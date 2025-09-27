#!/bin/bash
# Web Interface Migration - Comprehensive Testing Script
# Usage: ./web-interface-migration-test.sh [phase]

set -e

PHASE=${1:-"all"}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_RESULTS_DIR="test_results/web_interface_migration_$TIMESTAMP"
BASE_URL="http://localhost:8000"

echo "🧪 WEB INTERFACE MIGRATION - TESTING SUITE"
echo "========================================="
echo "Phase: $PHASE"
echo "Timestamp: $(date)"
echo "Results directory: $TEST_RESULTS_DIR"
echo ""

# Setup
mkdir -p "$TEST_RESULTS_DIR"

# Function to test HTTP endpoint
test_url() {
    local url="$1"
    local expected_code="$2"
    local description="$3"
    
    echo -n "  Testing $description... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
    
    if [ "$response" = "$expected_code" ]; then
        echo "✅ ($response)"
        echo "PASS: $url -> $response" >> "$TEST_RESULTS_DIR/url_tests.log"
        return 0
    else
        echo "❌ (expected $expected_code, got $response)"
        echo "FAIL: $url -> expected $expected_code, got $response" >> "$TEST_RESULTS_DIR/url_tests.log"
        return 1
    fi
}

# Function to test Django functionality
test_django() {
    echo "🔍 Django System Tests"
    echo "====================="
    
    echo "  Running Django check..."
    if python manage.py check --deploy > "$TEST_RESULTS_DIR/django_check.log" 2>&1; then
        echo "  ✅ Django configuration valid"
    else
        echo "  ❌ Django configuration issues found"
        cat "$TEST_RESULTS_DIR/django_check.log"
        return 1
    fi
    
    echo "  Testing URL reversing..."
    if python -c "
import os, sys
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
import django
django.setup()
from django.urls import reverse
print('Testing web_interface URLs...')
try:
    reverse('web_interface:login')
    reverse('web_interface:dashboard')
    reverse('web_interface:student-list')
    print('✅ URL reversing works correctly')
except Exception as e:
    print(f'❌ URL reversing failed: {e}')
    sys.exit(1)
" > "$TEST_RESULTS_DIR/url_reverse.log" 2>&1; then
        echo "  ✅ URL reversing successful"
    else
        echo "  ❌ URL reversing failed"
        cat "$TEST_RESULTS_DIR/url_reverse.log"
        return 1
    fi
}

# Phase 1: Pre-migration testing
test_phase1() {
    echo "🔹 Phase 1: Pre-Migration Testing"
    echo "================================"
    
    test_url "$BASE_URL/" "200" "Current root page"
    test_url "$BASE_URL/admin/" "302" "Admin redirect"
    test_url "$BASE_URL/web/" "200" "Web interface current location"
    test_url "$BASE_URL/api/" "200" "API endpoints"
    
    test_django
}

# Phase 2: Post-backup testing
test_phase2() {
    echo "🔹 Phase 2: Post-Backup Testing" 
    echo "==============================="
    
    test_url "$BASE_URL/legacy/" "200" "Legacy home page"
    test_url "$BASE_URL/legacy/about/" "200" "Legacy about page"
    test_url "$BASE_URL/legacy/admin-apps/users/" "200" "Legacy users"
    test_url "$BASE_URL/legacy/admin-apps/finance/" "200" "Legacy finance"
    
    # Verify original URLs still work
    test_url "$BASE_URL/" "200" "Original root still working"
    test_url "$BASE_URL/web/" "200" "Web interface still at /web/"
}

# Phase 3: Post-migration testing
test_phase3() {
    echo "🔹 Phase 3: Post-Migration Testing"
    echo "=================================="
    
    # Test new root functionality
    test_url "$BASE_URL/" "200" "Web interface at root"
    test_url "$BASE_URL/login/" "200" "Login page"
    test_url "$BASE_URL/dashboard/" "302" "Dashboard (requires auth)"
    test_url "$BASE_URL/students/" "302" "Student list (requires auth)"
    test_url "$BASE_URL/academic/" "302" "Academic section (requires auth)"
    test_url "$BASE_URL/finance/" "302" "Finance section (requires auth)"
    
    # Test legacy backup access
    test_url "$BASE_URL/legacy/" "200" "Legacy backup accessible"
    
    # Test admin still works
    test_url "$BASE_URL/admin/" "302" "Django admin still accessible"
    test_url "$BASE_URL/api/" "200" "API still accessible"
    
    test_django
}

# HTMX functionality testing
test_htmx() {
    echo "🔹 HTMX Functionality Testing"
    echo "============================="
    
    echo "  Testing HTMX endpoints..."
    
    # Test with HTMX headers
    test_url "$BASE_URL/search/students/" "302" "HTMX student search"
    test_url "$BASE_URL/modals/student/create/" "302" "HTMX student modal"
    
    echo "  ℹ️  Note: HTMX tests require authentication - manual testing recommended"
}

# Performance testing
test_performance() {
    echo "🔹 Performance Testing"
    echo "======================"
    
    echo "  Measuring page load times..."
    
    for url in "/" "/login/" "/legacy/"; do
        if curl -s "$BASE_URL$url" > /dev/null; then
            time_result=$(curl -o /dev/null -s -w "%{time_total}" "$BASE_URL$url")
            echo "  $url: ${time_result}s"
            echo "$url: ${time_result}s" >> "$TEST_RESULTS_DIR/performance.log"
            
            if (( $(echo "$time_result > 2.0" | bc -l) )); then
                echo "  ⚠️  Warning: Page load time > 2 seconds"
            fi
        fi
    done
}

# Static files testing
test_static_files() {
    echo "🔹 Static Files Testing"
    echo "======================="
    
    # Test critical static files
    test_url "$BASE_URL/static/favicon.ico" "200" "Favicon"
    test_url "$BASE_URL/static/web_interface/css/dashboard-optimized.css" "200" "Web interface CSS"
    test_url "$BASE_URL/static/web_interface/js/htmx.min.js" "200" "HTMX JavaScript"
}

# Comprehensive test runner
run_all_tests() {
    echo "🧪 Running Comprehensive Test Suite"
    echo "==================================="
    
    local failed_tests=0
    
    # Run all test phases
    test_phase1 || ((failed_tests++))
    test_phase2 || ((failed_tests++)) 
    test_phase3 || ((failed_tests++))
    test_htmx || ((failed_tests++))
    test_performance
    test_static_files || ((failed_tests++))
    
    echo ""
    echo "📊 TEST RESULTS SUMMARY"
    echo "======================"
    echo "Results stored in: $TEST_RESULTS_DIR"
    
    if [ $failed_tests -eq 0 ]; then
        echo "🎉 All tests passed!"
        echo "OVERALL RESULT: PASS" >> "$TEST_RESULTS_DIR/summary.log"
        return 0
    else
        echo "❌ $failed_tests test phase(s) failed"
        echo "OVERALL RESULT: FAIL ($failed_tests failures)" >> "$TEST_RESULTS_DIR/summary.log"
        return 1
    fi
}

# Main execution logic
case $PHASE in
    "1"|"phase1"|"pre")
        test_phase1
        ;;
    "2"|"phase2"|"backup")
        test_phase2
        ;;
    "3"|"phase3"|"post")
        test_phase3
        ;;
    "htmx")
        test_htmx
        ;;
    "performance"|"perf")
        test_performance
        ;;
    "static")
        test_static_files
        ;;
    "all"|*)
        run_all_tests
        ;;
esac

echo ""
echo "✅ Testing completed at $(date)"
echo "📁 Detailed results: $TEST_RESULTS_DIR"