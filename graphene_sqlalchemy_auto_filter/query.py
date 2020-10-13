import logging
from collections import OrderedDict
from typing import List

import graphene
import inflection
import sqlalchemy
from graphene import Connection, Int, Node
from graphene.types.objecttype import ObjectType, ObjectTypeOptions
from graphene_sqlalchemy.types import (
    SQLAlchemyObjectType,
    sort_argument_for_object_type,
)
from graphene_sqlalchemy_filter import FilterableConnectionField, FilterSet
from graphene_sqlalchemy_filter.connection_field import FilterableFieldFactory
from sqlalchemy.ext.declarative import DeclarativeMeta


class CustomConnectionField(FilterableConnectionField):
    def __init__(self, connection, *args, **kwargs):
        """
        add default query
        limit
        offset
        """
        model = connection.Edge.node._type._meta.model
        if "limit" not in kwargs:
            kwargs.setdefault("limit", sort_argument_for_object_type(model))
        elif "limit" in kwargs and kwargs["limit"] is None:
            del kwargs["limit"]
        if "offset" not in kwargs:
            kwargs.setdefault("offset", sort_argument_for_object_type(model))
        elif "offset" in kwargs and kwargs["offset"] is None:
            del kwargs["offset"]
        super(CustomConnectionField, self).__init__(connection, *args, **kwargs)

    @classmethod
    def get_query(cls, model, info, **args):
        query = super(CustomConnectionField, cls).get_query(model, info, **args)
        if "limit" in args:
            query = query.limit(args["limit"])
        if "offset" in args:
            query = query.offset(args["offset"])
        return query


class CustomConnection(Connection):
    class Meta:
        abstract = True

    total_count = graphene.Int()

    @staticmethod
    def resolve_total_count(root, info):
        return root.iterable.limit(None).offset(None).count()


def init_custom_connection_field(
    custom_connection_field: FilterableConnectionField,
    declarative_base: DeclarativeMeta,
    custom_filters_path,
    exclude_models=None,
    base_filter_class=FilterSet,
):
    if exclude_models is None:
        exclude_models = []
    models = [
        m_cls
        for m_cls in declarative_base._decl_class_registry.values()
        if isinstance(m_cls, type) and issubclass(m_cls, declarative_base)
        if m_cls.__name__ not in exclude_models
    ]  # all models except exclude_models
    generated_filters = {
        sqla_model: filter_factory(base_filter_class, sqla_model, custom_filters_path)()
        for sqla_model in models
    }
    filters = {**custom_connection_field.filters, **generated_filters}
    custom_connection_field.filters = filters
    custom_connection_field.factory = FilterableFieldFactory(filters)


def filter_factory(
    base_filter_class: FilterSet,
    sqla_model: DeclarativeMeta,
    custom_filters_path: str = None,
) -> FilterSet:
    filter_class_name = sqla_model.__name__ + "Filter"
    try:
        # import our filters if exists
        filter_class = getattr(custom_filters_path, filter_class_name)
    except AttributeError:
        logging.debug(
            "Can't get {} from {} - auto generate".format(
                filter_class_name, custom_filters_path
            )
        )
        generated_fields = {
            column.key: [...] for column in sqlalchemy.inspect(sqla_model).attrs
        }
        filter_class = base_filter_class.create_type(
            filter_class_name, model=sqla_model, fields=generated_fields
        )
    return filter_class


def node_factory(
    custom_connection_field, model: DeclarativeMeta, custom_schemas_path: str = None
) -> SQLAlchemyObjectType:
    node_name = model.__name__ + "Node"
    model_description = _get_table_args_key(model, "comment")

    if hasattr(model, "id"):
        model.db_id = model.id

    try:
        # import our nodes if exists
        model_node_class = getattr(custom_schemas_path, node_name)
    except AttributeError:
        logging.debug(
            "Can't get {} from {} - auto generate".format(
                node_name, custom_schemas_path
            )
        )
        meta = type(
            "Meta",
            (object,),
            {
                "model": model,
                "interfaces": (Node,),
                "connection_field_factory": custom_connection_field.factory,
                "description": model_description,
            },
        )
        model_node_class = type(
            node_name,
            (SQLAlchemyObjectType,),
            {"db_id": Int(description="Real ID from DB"), "Meta": meta},
        )

    return model_node_class


def connections_factory(node: SQLAlchemyObjectType, custom_connection) -> Connection:
    connection_name = node.__name__.replace("Node", "Connection")
    return custom_connection.create_type(connection_name, node=node)


def _get_table_args_key(sqla_model: DeclarativeMeta, key: str, default=""):
    """
    Get key's value from __table_args__
    """
    value = default
    if isinstance(sqla_model.__table_args__, dict):
        value = sqla_model.__table_args__.get(key, default)
    elif isinstance(sqla_model.__table_args__, dict):
        value = next(
            (o.get(key) for o in sqla_model.__table_args__ if isinstance(o, dict)),
            default,
        )
    return value


class QueryObjectType(ObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        declarative_base: DeclarativeMeta,
        exclude_models: List[str],
        base_filter_class=FilterSet,
        custom_connection=CustomConnection,
        custom_connection_field=CustomConnectionField,
        custom_schemas_path: str = None,
        custom_filters_path: str = None,
        _meta=None,
        **options
    ):
        logging.info("Generate auto query...")
        if not _meta:
            _meta = ObjectTypeOptions(cls)
        fields = OrderedDict()
        fields["node"] = graphene.relay.Node.Field()
        for model in custom_connection_field.filters:
            logging.debug("Generate fields for {}".format(model.__name__))
            node = node_factory(custom_connection_field, model, custom_schemas_path)
            connection = connections_factory(node, custom_connection)
            query_name = "%s_list" % inflection.underscore(model.__name__)
            fields.update(
                {
                    inflection.underscore(model.__name__): graphene.relay.Node.Field(
                        node
                    ),
                    query_name: custom_connection_field(
                        connection,
                        limit=graphene.types.Int(),
                        offset=graphene.types.Int(),
                    ),
                }
            )

        if _meta.fields:
            _meta.fields.update(fields)
        else:
            _meta.fields = fields
        logging.info("Generate auto query done")
        return super(QueryObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, **options
        )
