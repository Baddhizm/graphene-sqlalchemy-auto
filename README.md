Generate default graphene schema from sqlalchemy model with filters base on:
* [graphene-sqlalchemy](https://github.com/graphql-python/graphene-sqlalchemy.git)
* [graphene-sqlalchemy-filter](https://github.com/art1415926535/graphene-sqlalchemy-filter)

# Features

- auto add queries (query name example: `NodeName`+`List`)
- auto add `filter`, `sort` fileds based on `graphene-sqlalchemy-filter`, it also support nested filters
- you can add your own custom filters, custom nodes, custom connection field, custom conenction
- auto add `dbId` for model's database id
- mutation auto return ok for success,message for more information and output for model data


# How To Use
example:
```python
from graphene_sqlalchemy_filter import FilterSet
from graphene_sqlalchemy_auto_filter import QueryObjectType, MutationObjectType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import inspect, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import create_engine
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType


engine = create_engine('sqlite://')
Base = declarative_base() 
Session = sessionmaker()


class User(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)


class UserFilter(FilterSet):  # pattern for custom filters name: ModelName + Filter
    class Meta:
        model = User
        fields = {
            column.key: [...] for column in inspect(model).attrs  # add all filters for all fields
        }


class UserNode(SQLAlchemyObjectType):  # pattern for custom node name: ModelName + Node
    custom_field = graphene.String()

    def resolve_custom_field(self, info):
        return 'foobar'


class Query(
    QueryObjectType,
    # And other queries...
):
    class Meta:
        declarative_base = Base
        exclude_models = ["Address"] # exclude models
        # custom_filters_path = 'your_package.filters'  # it scan for filters and compare filter name and model name 
        # custom_schemas_path = 'your_package.nodes'  # same as above
        # base_filter_class = MyFilterSet,  # type: graphene_sqlalchemy_filter.FilterSet
        # custom_connection = MyConnection,  # type: graphene.Connection
        # custom_connection_field = CustomConnectionField  # type: graphene_sqlalchemy.SQLAlchemyConnectionField

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
