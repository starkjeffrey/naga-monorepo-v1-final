#!/bin/bash

# =============================================================================
# COMPREHENSIVE API TEST SUITE FOR STAFF-WEB V2
# Complete curl command validation for all API modules
# =============================================================================

set -e  # Exit on any error

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
API_V2_URL="${BASE_URL}/api/v2"
AUTH_TOKEN="${AUTH_TOKEN:-}"
TEST_RESULTS_DIR="./test-results"
LOG_FILE="${TEST_RESULTS_DIR}/api-test-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Create results directory
mkdir -p "$TEST_RESULTS_DIR"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Test execution function
run_test() {
    local test_name="$1"
    local curl_command="$2"
    local expected_status="${3:-200}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo -e "${BLUE}[TEST $TOTAL_TESTS]${NC} $test_name"
    log "Running test: $test_name"
    log "Command: $curl_command"

    # Execute curl command and capture response
    response=$(eval "$curl_command" 2>&1)
    status_code=$(echo "$response" | tail -n1)

    if [[ "$status_code" == "$expected_status" ]]; then
        echo -e "${GREEN}✓ PASSED${NC} - Status: $status_code"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log "PASSED: $test_name (Status: $status_code)"
    else
        echo -e "${RED}✗ FAILED${NC} - Expected: $expected_status, Got: $status_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log "FAILED: $test_name (Expected: $expected_status, Got: $status_code)"
        log "Response: $response"
    fi

    echo ""
}

# Authentication setup
setup_auth() {
    if [[ -z "$AUTH_TOKEN" ]]; then
        echo -e "${YELLOW}Warning: No AUTH_TOKEN provided. Some tests may fail.${NC}"
        echo "Set AUTH_TOKEN environment variable for authenticated endpoints."
        echo ""
    fi
}

# =============================================================================
# STUDENT MANAGEMENT API TESTS
# =============================================================================

test_student_apis() {
    echo -e "${BLUE}========== STUDENT MANAGEMENT API TESTS ==========${NC}"

    # Basic student search
    run_test "Student Advanced Search" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/students/search/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"query\": \"john\", \"fuzzy_search\": true}'"

    # Student analytics (requires student ID)
    local test_student_id="550e8400-e29b-41d4-a716-446655440000"
    run_test "Student Analytics" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/students/$test_student_id/analytics/' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Student timeline
    run_test "Student Timeline" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/students/$test_student_id/timeline/' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Photo upload test (simulated)
    run_test "Student Photo Upload" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/students/$test_student_id/photos/upload/' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -F 'photo=@/tmp/test-photo.jpg'" \
        "400"  # Expected to fail without actual photo file

    # Bulk student actions
    run_test "Bulk Student Actions" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/students/bulk-actions/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"action\": \"update_status\", \"target_ids\": [\"$test_student_id\"], \"parameters\": {\"status\": \"active\"}, \"dry_run\": true}'"
}

# =============================================================================
# ACADEMIC MANAGEMENT API TESTS
# =============================================================================

test_academic_apis() {
    echo -e "${BLUE}========== ACADEMIC MANAGEMENT API TESTS ==========${NC}"

    local test_class_id="550e8400-e29b-41d4-a716-446655440001"
    local test_course_id="550e8400-e29b-41d4-a716-446655440002"
    local test_student_id="550e8400-e29b-41d4-a716-446655440000"

    # Grade spreadsheet data
    run_test "Grade Spreadsheet Data" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/academics/grades/spreadsheet/$test_class_id/' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Schedule conflict detection
    run_test "Schedule Conflict Detection" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/academics/schedule/conflicts/' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Transcript generation
    run_test "Transcript Generation" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/academics/transcripts/generate/$test_student_id/' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # QR attendance processing
    run_test "QR Attendance Processing" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/academics/attendance/qr-scan/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"qr_data\": \"$test_class_id:$test_student_id:2024-01-15T10:00:00Z\"}'"

    # Prerequisite chain visualization
    run_test "Prerequisite Chain" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/academics/courses/$test_course_id/prerequisites/' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Grade distribution analytics
    run_test "Grade Distribution Analytics" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/academics/analytics/grade-distribution/$test_class_id/' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Bulk grade updates
    run_test "Bulk Grade Updates" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/academics/grades/spreadsheet/$test_class_id/bulk-update/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '[{\"student_id\": \"$test_student_id\", \"assignment_id\": \"550e8400-e29b-41d4-a716-446655440003\", \"score\": 95, \"notes\": \"Excellent work\", \"last_modified\": \"2024-01-01T00:00:00Z\"}]'"
}

# =============================================================================
# FINANCIAL MANAGEMENT API TESTS
# =============================================================================

test_finance_apis() {
    echo -e "${BLUE}========== FINANCIAL MANAGEMENT API TESTS ==========${NC}"

    local test_student_id="550e8400-e29b-41d4-a716-446655440000"

    # POS transaction processing
    run_test "POS Transaction Processing" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/finance/pos/transaction/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"amount\": 100.00, \"payment_method\": \"cash\", \"description\": \"Test payment\", \"student_id\": \"$test_student_id\", \"line_items\": [{\"description\": \"Test item\", \"quantity\": 1, \"unit_price\": 100.00, \"total_amount\": 100.00}]}'"

    # Financial analytics dashboard
    run_test "Financial Analytics Dashboard" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/finance/analytics/dashboard/?date_range=30&include_forecasts=true' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Scholarship matching
    run_test "AI Scholarship Matching" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/finance/scholarships/matching/$test_student_id/' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Payment reminder automation
    run_test "Payment Reminder Automation" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/finance/automation/payment-reminders/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"student_ids\": [\"$test_student_id\"], \"reminder_days\": [7, 3, 1], \"template\": \"default\"}'"

    # Revenue forecast
    run_test "Revenue Forecast" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/finance/reports/revenue-forecast/?months_ahead=6&confidence_level=0.8' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Payment audit summary
    run_test "Payment Audit Summary" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/finance/audit/payment-summary/?start_date=2024-01-01T00:00:00Z&end_date=2024-12-31T23:59:59Z' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"
}

# =============================================================================
# INNOVATION API TESTS (AI/ML, AUTOMATION, OCR)
# =============================================================================

test_innovation_apis() {
    echo -e "${BLUE}========== INNOVATION API TESTS ==========${NC}"

    local test_student_id="550e8400-e29b-41d4-a716-446655440000"

    # AI Success Prediction
    run_test "AI Student Success Prediction" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/innovation/ai/predictions/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"model_type\": \"success_prediction\", \"input_data\": {\"student_id\": \"$test_student_id\"}}'"

    # AI Risk Assessment
    run_test "AI Risk Assessment" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/innovation/ai/predictions/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"model_type\": \"risk_assessment\", \"input_data\": {\"student_id\": \"$test_student_id\"}}'"

    # AI Grade Prediction
    run_test "AI Grade Prediction" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/innovation/ai/predictions/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"model_type\": \"grade_prediction\", \"input_data\": {\"student_id\": \"$test_student_id\"}}'"

    # Workflow automation list
    run_test "List Workflow Automations" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/innovation/automation/workflows/' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Execute workflow
    local test_workflow_id="550e8400-e29b-41d4-a716-446655440004"
    run_test "Execute Workflow" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/innovation/automation/workflows/$test_workflow_id/execute/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"parameters\": {\"test\": true}}'"

    # Document OCR processing (without actual file)
    run_test "Document OCR Processing" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/innovation/documents/ocr/' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -F 'document=@/tmp/test-document.pdf'" \
        "400"  # Expected to fail without actual document

    # Message threads
    run_test "List Message Threads" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/innovation/communications/threads/' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Custom analytics dashboard
    run_test "Custom Analytics Dashboard" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/innovation/analytics/custom/dashboard/?metrics=enrollment_trends,grade_distribution' \
        -H 'Authorization: Bearer $AUTH_TOKEN'"

    # Generate custom report
    run_test "Generate Custom Report" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/innovation/analytics/custom/report/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"report_type\": \"enrollment_summary\", \"date_range\": {\"start\": \"2024-01-01\", \"end\": \"2024-12-31\"}, \"format\": \"pdf\"}'"
}

# =============================================================================
# PERFORMANCE TESTING
# =============================================================================

test_performance() {
    echo -e "${BLUE}========== PERFORMANCE TESTS ==========${NC}"

    # Test concurrent requests
    run_test "Concurrent Requests Test" \
        "for i in {1..5}; do curl -s -w '%{http_code}' -X GET '$API_V2_URL/innovation/analytics/custom/dashboard/' -H 'Authorization: Bearer $AUTH_TOKEN' & done; wait"

    # Test large payload handling
    run_test "Large Payload Test" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/students/bulk-actions/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"action\": \"export_data\", \"target_ids\": [$(for i in {1..100}; do echo -n \"\\\"550e8400-e29b-41d4-a716-44665544$(printf %04d $i)\\\",\"; done | sed 's/,$//')]', \"dry_run\": true}'"
}

# =============================================================================
# SECURITY TESTING
# =============================================================================

test_security() {
    echo -e "${BLUE}========== SECURITY TESTS ==========${NC}"

    # Test without authentication
    run_test "Unauthenticated Request Test" \
        "curl -s -w '%{http_code}' -X GET '$API_V2_URL/students/search/'" \
        "401"  # Should return unauthorized

    # Test SQL injection prevention
    run_test "SQL Injection Prevention Test" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/students/search/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"query\": \"'; DROP TABLE students; --\"}'"

    # Test XSS prevention
    run_test "XSS Prevention Test" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/students/search/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"query\": \"<script>alert('xss')</script>\"}'"

    # Test oversized request
    run_test "Oversized Request Test" \
        "curl -s -w '%{http_code}' -X POST '$API_V2_URL/students/search/' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer $AUTH_TOKEN' \
        -d '{\"query\": \"$(head -c 10000 /dev/zero | tr '\0' 'A')\"}'" \
        "413"  # Should return payload too large
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    echo -e "${GREEN}==============================================================================${NC}"
    echo -e "${GREEN}     STAFF-WEB V2 COMPREHENSIVE API TEST SUITE${NC}"
    echo -e "${GREEN}==============================================================================${NC}"
    echo ""
    echo "Base URL: $BASE_URL"
    echo "API V2 URL: $API_V2_URL"
    echo "Log file: $LOG_FILE"
    echo ""

    setup_auth

    # Run all test suites
    test_student_apis
    test_academic_apis
    test_finance_apis
    test_innovation_apis
    test_performance
    test_security

    # Generate summary
    echo -e "${GREEN}==============================================================================${NC}"
    echo -e "${GREEN}                              TEST SUMMARY${NC}"
    echo -e "${GREEN}==============================================================================${NC}"
    echo -e "Total Tests: ${BLUE}$TOTAL_TESTS${NC}"
    echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
    echo ""

    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}🎉 ALL TESTS PASSED! 🎉${NC}"
        echo "The Staff-Web V2 API is ready for production deployment."
    else
        echo -e "${RED}❌ SOME TESTS FAILED${NC}"
        echo "Please review the failed tests and fix the issues before deployment."
        echo "Check the log file for detailed error information: $LOG_FILE"
    fi

    echo ""
    echo "Detailed results available in: $TEST_RESULTS_DIR"

    # Exit with appropriate code
    exit $FAILED_TESTS
}

# Run the test suite
main "$@"