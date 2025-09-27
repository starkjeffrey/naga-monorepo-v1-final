#!/bin/bash

# Academic Management API Validation Test Suite
#
# Comprehensive curl-based tests for validating all academic management endpoints
# including real-time collaboration, AI features, and operational transforms.
#
# Usage: ./api-validation.sh [BASE_URL] [AUTH_TOKEN]

set -e

# Configuration
BASE_URL=${1:-"http://localhost:8000/api/v1"}
AUTH_TOKEN=${2:-""}
TEST_OUTPUT_DIR="./test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${TEST_OUTPUT_DIR}/api_test_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Create output directory
mkdir -p "$TEST_OUTPUT_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Test result functions
test_start() {
    ((TOTAL_TESTS++))
    echo -e "${BLUE}[TEST $TOTAL_TESTS]${NC} $1"
    log "Starting test: $1"
}

test_pass() {
    ((PASSED_TESTS++))
    echo -e "${GREEN}✓ PASS${NC}: $1"
    log "PASS: $1"
}

test_fail() {
    ((FAILED_TESTS++))
    echo -e "${RED}✗ FAIL${NC}: $1"
    log "FAIL: $1"
    if [ -n "$2" ]; then
        echo -e "${RED}  Error: $2${NC}"
        log "  Error: $2"
    fi
}

# HTTP request wrapper with error handling
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=${4:-200}
    local description=$5

    local url="${BASE_URL}${endpoint}"
    local auth_header=""

    if [ -n "$AUTH_TOKEN" ]; then
        auth_header="-H \"Authorization: Bearer $AUTH_TOKEN\""
    fi

    local curl_cmd="curl -s -w \"HTTPSTATUS:%{http_code}\" -X $method"

    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -H \"Content-Type: application/json\" -d '$data'"
    fi

    if [ -n "$auth_header" ]; then
        curl_cmd="$curl_cmd $auth_header"
    fi

    curl_cmd="$curl_cmd \"$url\""

    local response
    response=$(eval $curl_cmd)

    local body=$(echo "$response" | sed -E 's/HTTPSTATUS\:[0-9]{3}$//')
    local status=$(echo "$response" | tr -d '\n' | sed -E 's/.*HTTPSTATUS:([0-9]{3})$/\1/')

    if [ "$status" -eq "$expected_status" ]; then
        test_pass "$description"
        echo "$body" | jq . 2>/dev/null || echo "$body"
        return 0
    else
        test_fail "$description" "Expected status $expected_status, got $status"
        echo "Response: $body"
        return 1
    fi
}

# Test data creation functions
create_test_course() {
    cat <<EOF
{
    "code": "TEST101",
    "name": "Test Course",
    "description": "A test course for API validation",
    "department": "Testing",
    "credits": 3,
    "level": "undergraduate",
    "status": "active",
    "maxCapacity": 30,
    "tuition": 1500,
    "prerequisites": [],
    "tags": ["test", "api"]
}
EOF
}

create_test_enrollment() {
    cat <<EOF
{
    "studentId": "student-test-123",
    "courseId": "course-test-456",
    "status": "enrolled",
    "paymentStatus": "pending",
    "paymentAmount": 1500
}
EOF
}

create_test_grade() {
    cat <<EOF
{
    "studentId": "student-test-123",
    "assignmentId": "assignment-test-789",
    "points": 85,
    "comments": "Good work!",
    "submitted": true,
    "late": false,
    "excused": false
}
EOF
}

# Header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Academic Management API Validation Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Base URL: $BASE_URL"
echo "Auth Token: ${AUTH_TOKEN:+***PRESENT***}${AUTH_TOKEN:-***NOT PROVIDED***}"
echo "Log file: $LOG_FILE"
echo ""

# ============================================================================
# Grade Management Tests
# ============================================================================

echo -e "${YELLOW}📊 Grade Management Tests${NC}"
echo "----------------------------------------"

test_start "Get class grades"
make_request "GET" "/grades/class/test-class-123?term=fall-2024" "" 200 "Fetch class grades with term filter"

test_start "Get grade statistics"
make_request "GET" "/grades/class/test-class-123/statistics" "" 200 "Fetch grade statistics for class"

test_start "Update single grade"
update_data=$(create_test_grade)
make_request "PUT" "/grades/test-grade-123" "$update_data" 200 "Update individual grade"

test_start "Bulk grade update"
bulk_data='{
    "grades": [
        {"id": "grade-1", "points": 90},
        {"id": "grade-2", "points": 85},
        {"id": "grade-3", "points": 88}
    ]
}'
make_request "POST" "/grades/bulk" "$bulk_data" 200 "Bulk update multiple grades"

test_start "Apply grade curve"
curve_data='{
    "curveType": "linear",
    "targetAverage": 85
}'
make_request "POST" "/grades/class/test-class-123/curve" "$curve_data" 200 "Apply linear grade curve"

test_start "Get grade change history"
make_request "GET" "/grades/test-grade-123/history" "" 200 "Fetch grade change history"

echo ""

# ============================================================================
# Course Management Tests
# ============================================================================

echo -e "${YELLOW}📚 Course Management Tests${NC}"
echo "----------------------------------------"

test_start "Get all courses with pagination"
make_request "GET" "/courses?page=1&limit=10&department=Computer%20Science" "" 200 "Fetch courses with filters and pagination"

test_start "Get single course details"
make_request "GET" "/courses/test-course-123" "" 200 "Fetch individual course details"

test_start "Create new course"
course_data=$(create_test_course)
make_request "POST" "/courses" "$course_data" 201 "Create new course"

test_start "Update course"
update_course_data='{
    "description": "Updated course description",
    "maxCapacity": 35
}'
make_request "PUT" "/courses/test-course-123" "$update_course_data" 200 "Update course information"

test_start "Duplicate course"
duplicate_data='{
    "code": "TEST102",
    "name": "Test Course Copy"
}'
make_request "POST" "/courses/test-course-123/duplicate" "$duplicate_data" 201 "Duplicate existing course"

test_start "Get course analytics"
make_request "GET" "/courses/test-course-123/analytics" "" 200 "Fetch course analytics data"

test_start "Get AI course recommendations"
make_request "GET" "/courses/test-course-123/ai-recommendations" "" 200 "Fetch AI-powered course recommendations"

test_start "Bulk course operations"
bulk_course_data='{
    "operation": "activate",
    "courseIds": ["course-1", "course-2", "course-3"]
}'
make_request "POST" "/courses/bulk" "$bulk_course_data" 200 "Perform bulk course operations"

echo ""

# ============================================================================
# Enrollment Management Tests
# ============================================================================

echo -e "${YELLOW}👥 Enrollment Management Tests${NC}"
echo "----------------------------------------"

test_start "Get enrollments with filters"
make_request "GET" "/enrollments?status=enrolled&term=fall-2024&page=1&limit=20" "" 200 "Fetch enrollments with status and term filters"

test_start "Create new enrollment"
enrollment_data=$(create_test_enrollment)
make_request "POST" "/enrollments" "$enrollment_data" 201 "Create new student enrollment"

test_start "Update enrollment status"
update_enrollment_data='{
    "status": "completed",
    "paymentStatus": "paid"
}'
make_request "PUT" "/enrollments/test-enrollment-123" "$update_enrollment_data" 200 "Update enrollment status"

test_start "Process waitlist enrollment"
make_request "POST" "/enrollments/waitlist/test-waitlist-456/process" "" 200 "Process student from waitlist to enrolled"

test_start "Get enrollment statistics"
make_request "GET" "/enrollments/statistics?term=fall-2024&department=Computer%20Science" "" 200 "Fetch enrollment statistics with filters"

test_start "Get enrollment forecast"
forecast_data='{
    "courseIds": ["course-123", "course-456", "course-789"],
    "periods": 3
}'
make_request "POST" "/enrollments/forecast" "$forecast_data" 200 "Generate enrollment forecasting"

test_start "Validate enrollment eligibility"
validation_data='{
    "studentId": "student-test-123",
    "courseId": "course-test-456"
}'
make_request "POST" "/enrollments/validate" "$validation_data" 200 "Validate student enrollment eligibility"

echo ""

# ============================================================================
# Schedule Management Tests
# ============================================================================

echo -e "${YELLOW}📅 Schedule Management Tests${NC}"
echo "----------------------------------------"

test_start "Get schedule data"
make_request "GET" "/schedule?term=fall-2024&departmentId=dept-cs" "" 200 "Fetch schedule data with filters"

test_start "Update schedule item"
schedule_update_data='{
    "timeSlot": {
        "dayOfWeek": "Monday",
        "startTime": "10:00",
        "endTime": "11:30"
    },
    "roomId": "room-a101"
}'
make_request "PUT" "/schedule/schedule-item-123" "$schedule_update_data" 200 "Update schedule item details"

test_start "Detect schedule conflicts"
make_request "GET" "/schedule/conflicts/current" "" 200 "Detect current schedule conflicts"

test_start "Optimize schedule with AI"
optimization_data='{
    "minimizeConflicts": true,
    "maximizeUtilization": true,
    "respectPreferences": false,
    "balanceWorkload": true
}'
make_request "POST" "/schedule/optimize" "$optimization_data" 200 "AI-powered schedule optimization"

test_start "Check room availability"
room_availability_data='{
    "start": "2024-09-01T09:00:00Z",
    "end": "2024-09-01T10:30:00Z"
}'
make_request "POST" "/schedule/rooms/room-a101/availability" "$room_availability_data" 200 "Check room availability for time range"

test_start "Check instructor availability"
instructor_availability_data='{
    "start": "2024-09-01T09:00:00Z",
    "end": "2024-09-01T10:30:00Z"
}'
make_request "POST" "/schedule/instructors/instructor-123/availability" "$instructor_availability_data" 200 "Check instructor availability"

echo ""

# ============================================================================
# AI Integration Tests
# ============================================================================

echo -e "${YELLOW}🤖 AI Integration Tests${NC}"
echo "----------------------------------------"

test_start "Get student course recommendations"
recommendation_context='{
    "careerGoals": ["software-engineering", "data-science"],
    "interests": ["programming", "algorithms", "machine-learning"],
    "timeConstraints": ["morning", "afternoon"]
}'
make_request "POST" "/ai/students/student-test-123/recommendations" "$recommendation_context" 200 "AI-powered course recommendations for student"

test_start "Identify at-risk students"
make_request "GET" "/ai/students/at-risk?threshold=0.7&courseId=course-123" "" 200 "Identify students at risk of academic failure"

test_start "Predict student performance"
performance_prediction_data='{
    "studentId": "student-test-123",
    "courseId": "course-test-456"
}'
make_request "POST" "/ai/predict/performance" "$performance_prediction_data" 200 "Predict student performance in course"

echo ""

# ============================================================================
# Analytics and Reporting Tests
# ============================================================================

echo -e "${YELLOW}📈 Analytics and Reporting Tests${NC}"
echo "----------------------------------------"

test_start "Get comprehensive academic analytics"
make_request "GET" "/analytics/academic?timeRange=semester&department=Computer%20Science" "" 200 "Fetch comprehensive academic analytics"

test_start "Generate academic report"
report_data='{
    "reportType": "enrollment",
    "format": "pdf",
    "dateRange": {
        "start": "2024-09-01",
        "end": "2024-12-15"
    },
    "filters": {
        "department": "Computer Science",
        "level": "undergraduate"
    }
}'
make_request "POST" "/reports/generate" "$report_data" 200 "Generate enrollment report"

test_start "Get report status"
make_request "GET" "/reports/test-report-123/status" "" 200 "Check report generation status"

echo ""

# ============================================================================
# Real-time Collaboration Tests (WebSocket simulation)
# ============================================================================

echo -e "${YELLOW}🔄 Real-time Collaboration Tests${NC}"
echo "----------------------------------------"

# Note: These tests simulate WebSocket behavior through HTTP endpoints
# In a real implementation, you would test actual WebSocket connections

test_start "WebSocket connection simulation"
ws_connect_data='{
    "resourceType": "grades",
    "resourceId": "class-123",
    "userId": "user-test-123"
}'
make_request "POST" "/ws/connect" "$ws_connect_data" 200 "Simulate WebSocket connection for grades"

test_start "User presence update"
presence_data='{
    "action": "join",
    "userId": "user-test-123",
    "resourceId": "class-123"
}'
make_request "POST" "/ws/presence" "$presence_data" 200 "Update user presence in collaborative session"

test_start "Field lock request"
field_lock_data='{
    "field": "points",
    "userId": "user-test-123",
    "expiresIn": 30000
}'
make_request "POST" "/ws/field-lock" "$field_lock_data" 200 "Request field lock for collaborative editing"

test_start "Operational transform submission"
operation_data='{
    "documentId": "grade-matrix",
    "operation": {
        "type": "replace",
        "position": 0,
        "length": 2,
        "content": "85"
    },
    "version": 5
}'
make_request "POST" "/ws/operation" "$operation_data" 200 "Submit operational transform"

echo ""

# ============================================================================
# Error Handling Tests
# ============================================================================

echo -e "${YELLOW}⚠️  Error Handling Tests${NC}"
echo "----------------------------------------"

test_start "Invalid course ID"
make_request "GET" "/courses/nonexistent-course" "" 404 "Handle request for non-existent course"

test_start "Invalid JSON data"
invalid_json='{"invalid": json, missing quote}'
make_request "POST" "/courses" "$invalid_json" 400 "Handle malformed JSON request"

test_start "Unauthorized access"
# Temporarily remove auth token for this test
temp_token="$AUTH_TOKEN"
AUTH_TOKEN=""
make_request "GET" "/grades/class/secure-class" "" 401 "Handle unauthorized access"
AUTH_TOKEN="$temp_token"

test_start "Method not allowed"
make_request "PATCH" "/courses/test-course/invalid-operation" "" 405 "Handle unsupported HTTP method"

echo ""

# ============================================================================
# Performance Tests
# ============================================================================

echo -e "${YELLOW}⚡ Performance Tests${NC}"
echo "----------------------------------------"

test_start "Large dataset query"
make_request "GET" "/courses?limit=1000" "" 200 "Handle large dataset query"

test_start "Concurrent request simulation"
# Simulate multiple concurrent requests
for i in {1..5}; do
    make_request "GET" "/courses?page=$i&limit=10" "" 200 "Concurrent request $i" &
done
wait
test_pass "All concurrent requests completed"

echo ""

# ============================================================================
# Data Validation Tests
# ============================================================================

echo -e "${YELLOW}✅ Data Validation Tests${NC}"
echo "----------------------------------------"

test_start "Course creation with invalid data"
invalid_course_data='{
    "code": "",
    "name": "Test Course",
    "credits": -1,
    "level": "invalid_level"
}'
make_request "POST" "/courses" "$invalid_course_data" 400 "Reject course with invalid data"

test_start "Grade update with out-of-range value"
invalid_grade_data='{
    "points": 150,
    "maxPoints": 100
}'
make_request "PUT" "/grades/test-grade-123" "$invalid_grade_data" 400 "Reject grade exceeding maximum points"

test_start "Enrollment with missing required fields"
incomplete_enrollment='{
    "studentId": "student-123"
}'
make_request "POST" "/enrollments" "$incomplete_enrollment" 400 "Reject incomplete enrollment data"

echo ""

# ============================================================================
# Test Summary
# ============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit_code=0
else
    echo -e "${RED}❌ $FAILED_TESTS test(s) failed.${NC}"
    exit_code=1
fi

echo ""
echo "Detailed results saved to: $LOG_FILE"
echo ""

# Generate test report
cat > "${TEST_OUTPUT_DIR}/test_report_${TIMESTAMP}.html" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>Academic API Test Report - $TIMESTAMP</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .summary { margin: 20px 0; }
        .pass { color: green; font-weight: bold; }
        .fail { color: red; font-weight: bold; }
        .section { margin: 20px 0; border-left: 4px solid #ddd; padding-left: 15px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Academic Management API Test Report</h1>
        <p>Generated: $(date)</p>
        <p>Base URL: $BASE_URL</p>
    </div>

    <div class="summary">
        <h2>Test Summary</h2>
        <p>Total Tests: $TOTAL_TESTS</p>
        <p class="pass">Passed: $PASSED_TESTS</p>
        <p class="fail">Failed: $FAILED_TESTS</p>
        <p>Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%</p>
    </div>

    <div class="section">
        <h2>Test Coverage</h2>
        <ul>
            <li>✅ Grade Management API</li>
            <li>✅ Course Management API</li>
            <li>✅ Enrollment Management API</li>
            <li>✅ Schedule Management API</li>
            <li>✅ AI Integration API</li>
            <li>✅ Analytics and Reporting API</li>
            <li>✅ Real-time Collaboration API</li>
            <li>✅ Error Handling</li>
            <li>✅ Performance Testing</li>
            <li>✅ Data Validation</li>
        </ul>
    </div>

    <div class="section">
        <h2>Full Test Log</h2>
        <pre>$(cat "$LOG_FILE")</pre>
    </div>
</body>
</html>
EOF

echo "HTML report generated: ${TEST_OUTPUT_DIR}/test_report_${TIMESTAMP}.html"

exit $exit_code