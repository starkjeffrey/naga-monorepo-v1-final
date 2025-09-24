"""Main API configuration for Django Ninja.

This module imports and re-exports the unified v1 API instance.
The API architecture has been migrated to a versioned structure
to support proper API evolution and eliminate circular dependencies.

API Structure:
- v1.0.0: Current stable API with unified architecture
- Future versions: v2, v3, etc. can be added independently

For backwards compatibility, this module continues to export
the API instance at the same location as before.

Migration Details:
- Eliminated circular dependencies between apps and versioned APIs
- Unified authentication system across all endpoints
- Consistent error handling and response schemas
- Proper separation between API layer and business logic
"""

# Import the unified v1 API
from api.v1 import api

# Export the v1 API as the main API for backwards compatibility
__all__ = ["api"]
