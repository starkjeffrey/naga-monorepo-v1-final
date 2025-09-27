"""Main API configuration for Django Ninja.

This module imports and re-exports the unified v1 API instance and
adds support for the enhanced v2 API with GraphQL.

API Structure:
- v1.0.0: Current stable API with unified architecture
- v2.0.0: Enhanced API with advanced features and GraphQL support
- Future versions: v3, v4, etc. can be added independently

For backwards compatibility, this module continues to export
the v1 API instance at the same location as before, while
also supporting the new v2 API endpoints.

Migration Details:
- Eliminated circular dependencies between apps and versioned APIs
- Unified authentication system across all endpoints
- Consistent error handling and response schemas
- Proper separation between API layer and business logic
- Added GraphQL support with Strawberry
- Enhanced real-time capabilities with WebSocket support
"""

# Import the unified v1 API
from api.v1 import api as api_v1

# Import the enhanced v2 API
from api.v2 import api as api_v2

# Export both APIs
api = api_v1  # Maintain backwards compatibility
__all__ = ["api", "api_v1", "api_v2"]
