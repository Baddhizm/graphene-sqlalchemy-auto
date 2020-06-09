from collections import OrderedDict
from typing import List, Dict

import inflection

from graphene import Connection, Node, Int

from graphene.types.objecttype import ObjectTypeOptions, ObjectType
from graphene_sqlalchemy.types import SQLAlchemyObjectType
from sqlalchemy import inspect as sqla_inspect
from sqlalchemy.engine import reflection, create_engine, Engine
from sqlalchemy.ext.declarative import DeclarativeMeta

from graphene_filter import FilterSet, FilterableConnectionField
from graphene_filter.connection_field import FilterableFieldFactory


def create_model_filter(sqla_model: DeclarativeMeta, filter_class_name: str) -> FilterSet:
    meta = type('Meta', (object,), {'model': sqla_model, 'fields': {
        column.key: [...] for column in sqla_inspect(sqla_model).attrs
    }})
    filter_class = type(filter_class_name, (FilterSet,), {'Meta': meta})
    return filter_class


def create_node_class(sqla_model: DeclarativeMeta, node_name: str, filters: Dict[DeclarativeMeta, FilterSet],
                      get_table_description: bool = False, engine: Engine = None, table_description: str = None):
    meta = type(
        'Meta',
        (object,),
        {
            'model': sqla_model,
            'interfaces': (Node,),
            'connection_field_factory': FilterableFieldFactory(filters),
            'description': table_description if table_description else get_description_for_model(
                sqla_model, engine) if get_table_description else ''
        })
    model_node_class = type(
        node_name,
        (SQLAlchemyObjectType,),
        {'db_id': Int(description='Настоящий ИД из базы'), 'Meta': meta}
    )
    return model_node_class


def filter_factory(sqla_model: DeclarativeMeta, custom_filters_path: str = None) -> FilterSet:
    filter_class_name = inflection.camelize(sqla_model.__name__) + 'Filter'
    if custom_filters_path:
        try:
            # import custom filters
            exec('from %s import %s' % (custom_filters_path, filter_class_name))
            filter_class = eval(filter_class_name)
        except ImportError:
            filter_class = create_model_filter(sqla_model, filter_class_name)
    else:
        filter_class = create_model_filter(sqla_model, filter_class_name)
    return filter_class


def custom_field_factory(filters: Dict[DeclarativeMeta, FilterSet]) -> FilterableConnectionField:
    custom_field_class = type(
        'CustomField',
        (FilterableConnectionField,),
        {'filters': filters}
    )
    return custom_field_class


def node_factory(filters: Dict[DeclarativeMeta, FilterSet], sqla_model: DeclarativeMeta,
                 custom_schemas_path: str = None, get_table_description: bool = False, engine: Engine = None) -> SQLAlchemyObjectType:
    node_name = inflection.camelize(sqla_model.__name__) + 'Node'
    if hasattr(sqla_model, "id"):
        sqla_model.db_id = sqla_model.id
    if custom_schemas_path:
        try:
            # import custom nodes
            exec('from %s import %s' % (custom_schemas_path, node_name))
            model_node_class = eval(node_name)
            # replace to own meta with connection_field_factory
            interfaces = model_node_class._meta.interfaces if model_node_class._meta.interfaces else (Node,)
            description = model_node_class._meta.description if model_node_class._meta.description else ''
            meta = type(
                'Meta',
                (object,),
                {
                    'model': model_node_class._meta.model,
                    'interfaces': interfaces,
                    'connection_field_factory': FilterableFieldFactory(filters),
                    'description': description
                })
            model_node_class = type(
                node_name,
                (model_node_class,),
                {'Meta': meta}
            )
        except ImportError:
            model_node_class = create_node_class(sqla_model, node_name, filters, get_table_description, engine)
    else:
        model_node_class = create_node_class(sqla_model, node_name, filters, get_table_description, engine)

    return model_node_class


def connections_factory(node: SQLAlchemyObjectType) -> Connection:
    if 'Node' in node.__name__:
        connection_name = node.__name__.replace('Node', 'Connection')
    elif 'Schema' in node.__name__:
        connection_name = node.__name__.replace('Schema', 'Connection')
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


def get_description_for_model(sqla_model: DeclarativeMeta, engine: Engine) -> str:
    # TODO: too long get table description from database
    insp = reflection.Inspector.from_engine(engine)
    description = ''
    try:
        table_name = sqla_model.__tablename__
        schema = sqla_model.__table_args__.get('schema') \
            if isinstance(sqla_model.__table_args__, dict) else sqla_model.__table_args__[1].get('schema')
        description = insp.get_table_comment(
            table_name,
            schema=schema
        )['text']
    except Exception as e:
        print('Can\'t get table description for model: ', sqla_model.__name__, e)
    return description


class QueryObjectType(ObjectType):
    @classmethod
    def __init_subclass_with_meta__(
            cls,
            declarative_base: DeclarativeMeta,
            exclude_models: List[str],
            get_table_description: bool = False,
            engine: Engine = None,
            custom_schemas_path: str = None,
            custom_filters_path: str = None,
            _meta=None,
            **options
    ):
        if not _meta:
            _meta = ObjectTypeOptions(cls)
        fields = OrderedDict()
        models = [m_cls for m_cls in declarative_base._decl_class_registry.values()
                  if isinstance(m_cls, type) and issubclass(m_cls, declarative_base)
                  if m_cls.__name__ not in exclude_models]

        # https://github.com/art1415926535/graphene-sqlalchemy-filter#filter-registration-and-nested-fields-filters
        # Filters
        model_filters = {sqla_model: filter_factory(sqla_model, custom_filters_path)() for sqla_model in models}

        custom_field = custom_field_factory(model_filters)
        # Nodes
        nodes = [node_factory(model_filters, sqla_model, custom_schemas_path, get_table_description, engine)
                 for sqla_model in models]

        # Connections
        connections = [connections_factory(node) for node in nodes]

        for connection in connections:
            query_name = "all_%s" % inflection.underscore(connection.__name__).replace('_connection', '')
            query_description = connection.Edge.node.type._meta.description
            fields.update({query_name: custom_field(connection, description=query_description)})

        if _meta.fields:
            _meta.fields.update(fields)
        else:
            _meta.fields = fields
        return super(QueryObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, **options
        )
