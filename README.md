![](https://github.com/goodking-bq/graphene-sqlalchemy-auto/workflows/python-publish.yml/badge.svg)

Generate default graphene schema from sqlalchemy model with filters base on:
* [graphene-sqlalchemy](https://github.com/graphql-python/graphene-sqlalchemy.git)
* [graphene-sqlalchemy-filter](https://github.com/art1415926535/graphene-sqlalchemy-filter)

# Features

- auto add `before` `after` `first` `last` to pagination
- auto add `filter` filed based on `graphene-sqlalchemy-filter`, it also support nested filters
- you can add your own custom filters and custom nodes/schemas
- auto add `dbId` for model's database id
- mutation auto return ok for success,message for more information and output for model data


# How To Use
example:
```python
from graphene_sqlalchemy_filter import FilterSet
from graphene_sqlalchemy_auto import QueryObjectType,MutationObjectType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType

Base = declarative_base() 
Session = sessionmaker()

class ShipAddressFilter(FilterSet):  # pattern for custom filters name: ModelName + Filter
    class Meta:
        model = ShipAddress
        fields = {
            column.key: [...] for column in inspect(model).attrs
        }


class ShipAddressNode(SQLAlchemyObjectType):  # pattern for custom node name: ModelName + Node
    custom_field = graphene.String()

    def resolve_custom_field(self, info):
        return 'foobar'


class Query(
    QueryObjectType,
    # And other queries...
):
    class Meta:
        declarative_base = Base
        exclude_models = ["User"] # exclude models
        # custom_filters_path = 'your_package.filters'  # it scan for filters and compare filter name and model name 
        # custom_schemas_path = 'your_package.nodes'  # same as above
        # get_table_description = True  # if you need get table desc from existing DB, you also need set Engine 
        # engine = Engine  # necessary if get_table_description is True


class Mutation(MutationObjectType):
    class Meta:
        declarative_base = Base
        session=Session() # mutate used
        
        include_object = [] # you can use yourself mutation UserCreateMutation, UserUpdateMutation


schema = graphene.Schema(query=Query, mutation=Mutation)

```

about many-to-many mutation

>now you can use schema everywhere.some like flask,fastapi

>also more example you can find in [example](https://github.com/goodking-bq/graphene-sqlalchemy-auto/tree/master/example)
