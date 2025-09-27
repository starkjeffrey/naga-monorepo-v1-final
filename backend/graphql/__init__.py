"""GraphQL API implementation using Strawberry GraphQL.

This package provides a complete GraphQL API for the Naga SIS system with:
- Comprehensive type definitions for all domain objects
- Optimized queries with DataLoader for N+1 prevention
- Real-time subscriptions for live updates
- Mutations for data modification operations
- Advanced filtering and pagination support
"""

from .schema import schema

__all__ = ["schema"]