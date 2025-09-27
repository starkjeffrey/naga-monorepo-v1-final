"""GraphQL URL configuration.

This module configures the GraphQL endpoint using Strawberry GraphQL
with Django integration, providing both HTTP and WebSocket support
for queries, mutations, and subscriptions.
"""

from django.urls import path
from strawberry.django.views import GraphQLView

from graphql.schema import schema

# GraphQL view with subscription support
graphql_view = GraphQLView.as_view(
    schema=schema,
    graphiql=True,  # Enable GraphiQL playground in development
    subscription_path="/ws/graphql/"  # WebSocket path for subscriptions
)

urlpatterns = [
    # GraphQL HTTP endpoint for queries and mutations
    path("", graphql_view, name="graphql"),

    # GraphQL WebSocket endpoint for subscriptions will be handled by ASGI routing
    # See asgi.py for WebSocket configuration
]