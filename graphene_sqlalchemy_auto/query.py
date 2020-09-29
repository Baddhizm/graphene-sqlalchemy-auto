import logging
from collections import OrderedDict
from importlib import import_module
from typing import List, Dict

import inflection
from graphene import Connection, Node, Int
from graphene.types.objecttype import ObjectTypeOptions, ObjectType
from graphene_sqlalchemy.types import SQLAlchemyObjectType, SQLAlchemyObjectTypeOptions
from graphene_sqlalchemy_filter import FilterSet
from graphene_sqlalchemy_filter.connection_field import FilterableFieldFactory, FilterableConnectionField
from sqlalchemy import inspect as sqla_inspect
from sqlalchemy.ext.declarative import DeclarativeMeta

logger = logging.getLogger()


def filter_factory(sqla_model: DeclarativeMeta, custom_filters_path: str = None):
    filter_class_name = inflection.camelize(sqla_model.__name__) + 'Filter'
    try:
        # import our filters if exists
        filter_class = getattr(import_module(custom_filters_path), filter_class_name)
    except AttributeError:
        logger.debug("Can't get {} from {} - auto generate".format(filter_class_name, custom_filters_path))
        meta = type('Meta', (object,), {'model': sqla_model, 'fields': {
            column.key: [...] for column in sqla_inspect(sqla_model).attrs
        }})
        filter_class = type(filter_class_name, (FilterSet,), {'Meta': meta})
    return filter_class


def custom_field_factory(filters: Dict[DeclarativeMeta, FilterSet]):
    custom_field_class = type(
        'CustomField',
        (FilterableConnectionField,),
        {'filters': {model: filter_() for model, filter_ in filters.items()}}
    )
    return custom_field_class


def node_factory(filters: Dict[DeclarativeMeta, FilterSet],
                 sqla_model: DeclarativeMeta,
                 custom_schemas_path: str = None):
    node_name = inflection.camelize(sqla_model.__name__) + 'Node'
    sqla_model_description = _get_table_args_key(sqla_model, 'comment')

    if hasattr(sqla_model, "id"):
        sqla_model.db_id = sqla_model.id

    our_node = False
    try:
        # import our nodes if exists
        if custom_schemas_path:
            model_node_class = getattr(import_module(custom_schemas_path), node_name)
            our_node = True
    except AttributeError:
        logger.debug("Can't get {} from {} - auto generate".format(node_name, custom_schemas_path))
        meta = type(
            'Meta',
            (object,),
            {
                'model': sqla_model,
                'interfaces': (Node,),
                'connection_field_factory': FilterableFieldFactory(filters),
                'description': sqla_model_description
            })
        model_node_class = type(
            node_name,
            (SQLAlchemyObjectType,),
            {'db_id': Int(description='Real ID from DB'), 'Meta': meta}
        )

    if our_node:
        # get some options just in case you forgot to specify in the node
        interfaces = model_node_class._meta.interfaces if model_node_class._meta.interfaces else (Node,)
        description_from_node = model_node_class._meta.description
        if description_from_node:
            description = description_from_node
        elif sqla_model_description:
            description = sqla_model_description
        else:
            description = ''
        # create new options dict with our and existing options
        options_dict = {
            **{key: value for key, value in model_node_class._meta.__dict__.items()},
            'connection_field_factory': FilterableFieldFactory(filters),
            'description': description,
            'interfaces': interfaces
        }
        # create class with our settings
        options = type(
            node_name + 'Options',
            (SQLAlchemyObjectTypeOptions,),
            options_dict
        )
        # override in imported node
        model_node_class._meta = options

    return model_node_class


def connections_factory(node: SQLAlchemyObjectType) -> Connection:
    connection_name = node.__name__.replace('Node', 'Connection')
    meta = type(
        'Meta',
        (object,),
        {'node': node})
    connection_class = type(
        connection_name,
        (Connection,),
        {'Meta': meta}
    )
    return connection_class


def _get_table_args_key(sqla_model: DeclarativeMeta, key: str):
    """
    Get key's value from __table_args__
    """
    value = None
    if isinstance(sqla_model.__table_args__, dict):
        value = sqla_model.__table_args__.get(key)
    elif isinstance(sqla_model.__table_args__, tuple):
        # search dict in tuple
        value = next((o.get(key) for o in sqla_model.__table_args__ if isinstance(o, dict)), None)
    return value


class QueryObjectType(ObjectType):
    @classmethod
    def __init_subclass_with_meta__(
            cls,
            declarative_base: DeclarativeMeta,
            exclude_models: List[str],
            custom_schemas_path: str = None,
            custom_filters_path: str = None,
            _meta=None,
            **options
    ):
        logger.info('Generate auto query...')
        inspector = None
        if not _meta:
            _meta = ObjectTypeOptions(cls)

        fields = OrderedDict()
        models = [m_cls for m_cls in declarative_base._decl_class_registry.values()
                  if isinstance(m_cls, type) and issubclass(m_cls, declarative_base)
                  if m_cls.__name__ not in exclude_models]

        # https://github.com/art1415926535/graphene-sqlalchemy-filter#filter-registration-and-nested-fields-filters
        # Filters
        model_filters = {sqla_model: filter_factory(sqla_model, custom_filters_path) for sqla_model in models}

        custom_field = custom_field_factory(model_filters)
        # Nodes
        nodes = [node_factory(model_filters, sqla_model, custom_schemas_path) for sqla_model in models]

        # Connections
        connections = [connections_factory(node) for node in nodes]

        for connection in connections:
            query_name = "all_%ss" % inflection.underscore(connection.__name__).replace('_connection', '')
            query_description = connection.Edge.node.type._meta.description
            fields.update({query_name: custom_field(connection, description=query_description)})

        if _meta.fields:
            _meta.fields.update(fields)
        else:
            _meta.fields = fields
        logger.info('Generate auto query done')
        return super(QueryObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, **options
        )
