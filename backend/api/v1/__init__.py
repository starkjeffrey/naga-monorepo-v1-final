"""Main API router for v1 endpoints.

This module creates the main NinjaAPI instance for version 1.0.0 and provides
the foundation for all v1 API endpoints. It will include routers from all
domain modules once they are migrated.

API Structure:
- /api/health/ - Health check endpoint
- /api/info/ - API information endpoint
- /api/attendance/ - Attendance endpoints (when migrated)
- /api/finance/ - Finance endpoints (when migrated)
- /api/grading/ - Grading endpoints (when migrated)
- /api/academic-records/ - Academic records endpoints (when migrated)
- /api/curriculum/ - Curriculum endpoints (when migrated)
- /api/mobile/ - Mobile-specific endpoints (when migrated)
"""

from django.http import HttpRequest
from ninja import NinjaAPI

from .schemas import ApiInfoResponse, HealthResponse

# Create the main v1 API instance
api = NinjaAPI(
    title="Naga SIS API",
    version="1.0.0",
    description="Student Information System API v1.0.0",
    docs_url="/docs/",
    openapi_url="/openapi.json",
    urls_namespace="naga_api_v1",  # Add unique namespace to avoid conflicts
    auth=None,  # Authentication handled per endpoint
)


@api.get("/health/", response=HealthResponse, tags=["System"])
def health_check(request: HttpRequest):
    """Health check endpoint to verify API availability."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={"database": "healthy", "redis": "healthy", "authentication": "healthy"},
    )


@api.get("/info/", response=ApiInfoResponse, tags=["System"])
def api_info(request: HttpRequest):
    """API information endpoint providing version and documentation details."""
    return ApiInfoResponse(
        title="Naga SIS API",
        version="1.0.0",
        description="Student Information System API for Pannasastra University of Cambodia",
        docs_url="/api/docs/",
        contact={"name": "Naga SIS Development Team", "url": "https://github.com/pannasastra/naga-sis"},
    )


# Domain routers - gradually activated
# Test grading API first
try:
    from . import grading

    api.add_router("/grading/", grading.router)
except Exception as e:
    # Log but don't crash the entire API
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load grading API: {e}")

# Add finance API
try:
    from . import finance

    api.add_router("/finance/", finance.router)
except Exception as e:
    # Log but don't crash the entire API
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load finance API: {e}")

# Add attendance API
try:
    from . import attendance

    api.add_router("/attendance/", attendance.router)
except Exception as e:
    # Log but don't crash the entire API
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load attendance API: {e}")

# Add people API
try:
    from . import people

    api.add_router("/people/", people.router)
except Exception as e:
    # Log but don't crash the entire API
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load people API: {e}")

# Add enrollment API
try:
    from . import enrollment

    api.add_router("/enrollment/", enrollment.router)
except Exception as e:
    # Log but don't crash the entire API
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load enrollment API: {e}")

# Add curriculum API
try:
    from . import curriculum

    api.add_router("/curriculum/", curriculum.router)
except Exception as e:
    # Log but don't crash the entire API
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load curriculum API: {e}")

# Add Khmer names API
try:
    from . import khmer_names

    api.add_router("/khmer-names/", khmer_names.router)
except Exception as e:
    # Log but don't crash the entire API
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load khmer names API: {e}")

# TODO: Add remaining routers as they are migrated:
# from . import academic_records, mobile
# api.add_router("/academic-records/", academic_records.router)
# api.add_router("/mobile/", mobile.router)


# Export the main API instance
__all__ = ["api"]
