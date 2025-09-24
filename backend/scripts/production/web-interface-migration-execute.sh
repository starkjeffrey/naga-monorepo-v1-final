#!/bin/bash
# Web Interface Migration - Execution Script
# Usage: ./web-interface-migration-execute.sh [phase] [--confirm]

set -e

PHASE=${1:-"help"}
CONFIRM=${2:-""}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MIGRATION_LOG="logs/web_interface_migration_$TIMESTAMP.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MIGRATION_LOG"
}

# Confirmation function
confirm() {
    if [ "$CONFIRM" != "--confirm" ]; then
        echo -e "${RED}❌ Migration phase requires --confirm flag${NC}"
        echo "Usage: $0 $PHASE --confirm"
        exit 1
    fi
}

# Create migration log directory
mkdir -p logs

echo -e "${BLUE}🚀 WEB INTERFACE MIGRATION EXECUTOR${NC}"
echo "===================================="
log "Migration started - Phase: $PHASE"

# Phase 1: Create backup infrastructure
execute_phase1() {
    echo -e "${BLUE}🔹 Phase 1: Creating Backup Infrastructure${NC}"
    confirm
    
    log "Starting Phase 1: Backup Infrastructure"
    
    # Backup current configuration
    log "Backing up current config/urls.py"
    cp config/urls.py "config/urls_backup_$TIMESTAMP.py"
    
    # Create legacy URL patterns
    log "Creating legacy URL patterns"
    cat > "config/legacy_urls.py" << 'EOF'
"""Legacy URL patterns for backward compatibility."""
from django.urls import include, path
from django.views.generic import TemplateView

legacy_urlpatterns = [
    # Legacy pages
    path("", TemplateView.as_view(template_name="pages/home.html"), name="legacy-home"),
    path("about/", TemplateView.as_view(template_name="pages/about.html"), name="legacy-about"),
    
    # Legacy test pages
    path("test-topnav/", TemplateView.as_view(template_name="pages/test_topnav.html"), name="legacy-test-topnav"),
    path("test-simple-topnav/", TemplateView.as_view(template_name="pages/test_simple_topnav.html"), name="legacy-test-simple-topnav"),
    path("test-fixed-topnav/", TemplateView.as_view(template_name="pages/test_fixed_topnav.html"), name="legacy-test-fixed-topnav"),
    path("test-svg-topnav/", TemplateView.as_view(template_name="pages/test_svg_topnav.html"), name="legacy-test-svg-topnav"),
    path("test-base2/", TemplateView.as_view(template_name="pages/test_base2.html"), name="legacy-test-base2"),
    path("test-new-base/", TemplateView.as_view(template_name="pages/test_new_base.html"), name="legacy-test-new-base"),
    
    # Legacy admin apps
    path("admin-apps/", include([
        path("users/", include("users.urls", namespace="legacy-users")),
        path("level-testing/", include("apps.level_testing.urls", namespace="legacy-level-testing")),
        path("people/", include("apps.people.urls", namespace="legacy-people")),
        path("scheduling/", include("apps.scheduling.urls", namespace="legacy-scheduling")),
        path("finance/", include("apps.finance.urls", namespace="legacy-finance")),
    ])),
]
EOF

    # Update main urls.py to include legacy patterns
    log "Adding legacy patterns to main URL configuration"
    python << 'EOF'
import re

with open('config/urls.py', 'r') as f:
    content = f.read()

# Add legacy import
if 'from .legacy_urls import legacy_urlpatterns' not in content:
    import_line = 'from .legacy_urls import legacy_urlpatterns\n'
    content = re.sub(r'(from config.api import api\n)', r'\1' + import_line, content)

# Add legacy path to urlpatterns
if 'path("legacy/", include(legacy_urlpatterns)),' not in content:
    legacy_path = '    path("legacy/", include(legacy_urlpatterns)),\n'
    content = re.sub(r'(    # Internationalization\n)', legacy_path + r'\1', content)

with open('config/urls.py', 'w') as f:
    f.write(content)
EOF

    log "Testing backup configuration"
    python manage.py check --deploy
    
    log "Phase 1 completed: Backup infrastructure created"
    echo -e "${GREEN}✅ Phase 1 completed successfully${NC}"
    echo -e "${YELLOW}ℹ️  Legacy system now accessible at /legacy/${NC}"
}

# Phase 2: Prepare web interface for root
execute_phase2() {
    echo -e "${BLUE}🔹 Phase 2: Preparing Web Interface for Root${NC}"
    confirm
    
    log "Starting Phase 2: Web Interface Root Preparation"
    
    # Test web interface functionality
    log "Testing web interface at current location (/web/)"
    curl -s -f http://localhost:8000/web/ > /dev/null || {
        log "ERROR: Web interface not accessible at /web/"
        exit 1
    }
    
    # Verify URL reversing works
    log "Checking URL reversing for web_interface"
    python << 'EOF'
import os, sys
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
import django
django.setup()

from django.urls import reverse
try:
    reverse('web_interface:login')
    reverse('web_interface:dashboard') 
    reverse('web_interface:student-list')
    print("✅ URL reversing successful")
except Exception as e:
    print(f"❌ URL reversing failed: {e}")
    sys.exit(1)
EOF

    # Check static files
    log "Verifying web interface static files"
    test -f "apps/web_interface/static/web_interface/css/dashboard-optimized.css" || {
        log "WARNING: Web interface CSS not found"
    }
    
    test -f "apps/web_interface/static/web_interface/js/htmx.min.js" || {
        log "WARNING: Web interface HTMX not found"
    }
    
    log "Phase 2 completed: Web interface ready for root deployment"
    echo -e "${GREEN}✅ Phase 2 completed successfully${NC}"
}

# Phase 3: Execute migration
execute_phase3() {
    echo -e "${BLUE}🔹 Phase 3: Executing Migration${NC}"
    confirm
    
    log "Starting Phase 3: URL Pattern Switchover"
    
    # Create new URL configuration
    log "Creating new root URL configuration"
    cat > "config/urls_new.py" << 'EOF'
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views import defaults as default_views

from config.api import api
from .legacy_urls import legacy_urlpatterns

urlpatterns = [
    # Web Interface at root (NEW)
    path("", include("apps.web_interface.urls", namespace="web_interface")),
    
    # Django Admin - preserve access
    path(settings.ADMIN_URL, admin.site.urls),
    
    # API endpoints - preserve access
    path("api/", api.urls),
    
    # Legacy system backup
    path("legacy/", include(legacy_urlpatterns)),
    
    # Authentication - preserve allauth
    path("accounts/", include("allauth.urls")),
    
    # Internationalization
    path("i18n/", include("django.conf.urls.i18n")),
    
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

if settings.DEBUG:
    # Static file serving when using Gunicorn + Uvicorn for local web socket development
    urlpatterns += staticfiles_urlpatterns()

    # Custom error handlers
    urlpatterns += [
        path("400/", default_views.bad_request, kwargs={"exception": Exception("Bad Request!")}),
        path("403/", default_views.permission_denied, kwargs={"exception": Exception("Permission Denied")}),
        path("404/", default_views.page_not_found, kwargs={"exception": Exception("Page not Found")}),
        path("500/", default_views.server_error),
    ]
    
    # Transaction browser for AR reconstruction batches
    from scratchpad.transaction_django_view import urlpatterns as transaction_urls
    urlpatterns += [path("transaction-browser/", include(transaction_urls))]
    
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls)), *urlpatterns]

# Custom error handlers
handler400 = default_views.bad_request
handler403 = default_views.permission_denied
handler404 = default_views.page_not_found
handler500 = default_views.server_error
EOF

    # Backup current and deploy new
    log "Deploying new URL configuration"
    mv config/urls.py "config/urls_old_$TIMESTAMP.py"
    mv config/urls_new.py config/urls.py
    
    # Test new configuration
    log "Testing new configuration"
    python manage.py check --deploy || {
        log "ERROR: New configuration failed validation"
        log "Rolling back to previous configuration"
        mv config/urls.py "config/urls_failed_$TIMESTAMP.py"
        mv "config/urls_old_$TIMESTAMP.py" config/urls.py
        exit 1
    }
    
    # Restart Django
    log "Restarting Django services"
    if command -v docker-compose >/dev/null; then
        docker-compose -f docker-compose.local.yml restart django
        sleep 5
    fi
    
    # Test new root
    log "Testing new root functionality"
    curl -s -f http://localhost:8000/ > /dev/null || {
        log "ERROR: New root not accessible"
        log "Rolling back configuration"
        mv config/urls.py "config/urls_failed_$TIMESTAMP.py"
        mv "config/urls_old_$TIMESTAMP.py" config/urls.py
        exit 1
    }
    
    log "Phase 3 completed: Web interface now serving at root"
    echo -e "${GREEN}✅ Phase 3 completed successfully${NC}"
    echo -e "${YELLOW}ℹ️  Web interface now accessible at /${NC}"
    echo -e "${YELLOW}ℹ️  Legacy system accessible at /legacy/${NC}"
}

# Phase 4: Verification and optimization
execute_phase4() {
    echo -e "${BLUE}🔹 Phase 4: Verification and Optimization${NC}"
    confirm
    
    log "Starting Phase 4: Post-migration verification"
    
    # Run comprehensive tests
    log "Running migration test suite"
    ./scripts/production/web-interface-migration-test.sh post
    
    # Performance check
    log "Checking performance"
    ./scripts/production/web-interface-migration-test.sh performance
    
    log "Phase 4 completed: Migration verified and optimized"
    echo -e "${GREEN}✅ Phase 4 completed successfully${NC}"
}

# Help function
show_help() {
    echo "Web Interface Migration Executor"
    echo ""
    echo "Usage: $0 [phase] --confirm"
    echo ""
    echo "Phases:"
    echo "  1, phase1, backup    - Create backup infrastructure"
    echo "  2, phase2, prepare   - Prepare web interface for root"
    echo "  3, phase3, migrate   - Execute the migration"
    echo "  4, phase4, verify    - Verify and optimize"
    echo "  all                  - Execute all phases"
    echo ""
    echo "Options:"
    echo "  --confirm            - Required to execute migration phases"
    echo ""
    echo "Examples:"
    echo "  $0 1 --confirm       - Execute phase 1"
    echo "  $0 all --confirm     - Execute complete migration"
    echo ""
    echo "⚠️  Important: Always test in development environment first!"
}

# Execute all phases
execute_all() {
    echo -e "${BLUE}🚀 Executing Complete Migration${NC}"
    confirm
    
    log "Starting complete migration process"
    
    execute_phase1
    execute_phase2  
    execute_phase3
    execute_phase4
    
    log "Complete migration finished successfully"
    echo -e "${GREEN}🎉 Migration completed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Summary:${NC}"
    echo "• Web interface now serving at root URL (/)"
    echo "• Legacy system preserved at /legacy/"
    echo "• Django admin still accessible at /admin/"
    echo "• API endpoints preserved at /api/"
    echo ""
    echo -e "${YELLOW}Log file: $MIGRATION_LOG${NC}"
}

# Main execution
case $PHASE in
    "1"|"phase1"|"backup")
        execute_phase1
        ;;
    "2"|"phase2"|"prepare")
        execute_phase2
        ;;
    "3"|"phase3"|"migrate")
        execute_phase3
        ;;
    "4"|"phase4"|"verify")
        execute_phase4
        ;;
    "all")
        execute_all
        ;;
    "help"|*)
        show_help
        ;;
esac

log "Migration phase '$PHASE' completed at $(date)"