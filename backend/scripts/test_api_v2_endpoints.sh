#!/bin/bash

# Test script for API v2 endpoints
# This script tests all the enhanced Django-Ninja v2 API endpoints

set -e

# Configuration
BASE_URL="http://localhost:8000"
API_V2_URL="$BASE_URL/api/v2"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test results
print_test_result() {
    local test_name="$1"
    local status="$2"
    local response="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓ PASS${NC} - $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC} - $test_name"
        echo -e "${YELLOW}Response:${NC} $response"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Function to make API request and test response
test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local test_name="$3"
    local expected_status="$4"
    local data="$5"

    echo -e "${BLUE}Testing:${NC} $test_name"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$API_V2_URL$endpoint")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_V2_URL$endpoint")
    else
        echo -e "${RED}Unsupported method: $method${NC}"
        return 1
    fi

    # Extract HTTP status code
    http_status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    response_body=$(echo "$response" | sed -e 's/HTTPSTATUS\:.*//g')

    if [ "$http_status" = "$expected_status" ]; then
        print_test_result "$test_name" "PASS" "$response_body"
    else
        print_test_result "$test_name" "FAIL" "Expected status $expected_status, got $http_status. Body: $response_body"
    fi
}

echo -e "${BLUE}=== Testing API v2 Endpoints ===${NC}"
echo ""

# Test health endpoints
echo -e "${YELLOW}--- Health Checks ---${NC}"
test_endpoint "GET" "/health/" "Health check endpoint" "200"
test_endpoint "GET" "/info/" "API info endpoint" "200"

# Test student endpoints
echo -e "${YELLOW}--- Student Endpoints ---${NC}"

# Note: These tests assume the server is running and may require authentication
# For a complete test, you would need valid authentication tokens

# Test student search (basic)
search_filters='{
    "query": "test",
    "fuzzy_search": false,
    "status": "enrolled"
}'
test_endpoint "POST" "/students/search/" "Student search endpoint" "401" "$search_filters"

# Test bulk actions (should fail without auth)
bulk_action='{
    "action": "update_status",
    "student_ids": ["550e8400-e29b-41d4-a716-446655440000"],
    "data": {"status": "active"}
}'
test_endpoint "POST" "/students/bulk-actions/" "Student bulk actions endpoint" "401" "$bulk_action"

# Test academics endpoints
echo -e "${YELLOW}--- Academic Endpoints ---${NC}"

# Test schedule conflict detection
test_endpoint "GET" "/academics/schedule/conflicts/" "Schedule conflict detection" "401"

# Test QR attendance processing
qr_data='{
    "qr_data": "{\"class_id\":\"550e8400-e29b-41d4-a716-446655440000\",\"student_id\":\"550e8400-e29b-41d4-a716-446655440001\",\"session_token\":\"test123\"}",
    "location": "Classroom A101"
}'
test_endpoint "POST" "/academics/attendance/qr-scan/" "QR attendance processing" "401" "$qr_data"

# Test finance endpoints
echo -e "${YELLOW}--- Finance Endpoints ---${NC}"

# These would typically require authentication and valid data
echo -e "${BLUE}Note: Finance endpoints require authentication${NC}"

# Test innovation endpoints
echo -e "${YELLOW}--- Innovation Endpoints ---${NC}"

# Test AI predictions
prediction_request='{
    "model_type": "success_prediction",
    "input_data": {"student_id": "550e8400-e29b-41d4-a716-446655440000"},
    "confidence_threshold": 0.5
}'
test_endpoint "POST" "/ai/predictions/" "AI predictions endpoint" "401" "$prediction_request"

# Test communications endpoints
echo -e "${YELLOW}--- Communication Endpoints ---${NC}"

# Test messaging (requires auth)
test_endpoint "GET" "/communications/" "Communications endpoint" "401"

# Test document OCR
echo -e "${YELLOW}--- Document Processing ---${NC}"
test_endpoint "POST" "/documents/ocr/" "Document OCR endpoint" "401" "{}"

# Test automation workflows
echo -e "${YELLOW}--- Automation Endpoints ---${NC}"
test_endpoint "GET" "/automation/workflows/" "Automation workflows endpoint" "401"

# Test analytics
echo -e "${YELLOW}--- Analytics Endpoints ---${NC}"
test_endpoint "GET" "/analytics/custom/" "Custom analytics endpoint" "401"

echo ""
echo -e "${BLUE}=== Test Summary ===${NC}"
echo -e "Tests run: $TESTS_RUN"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All accessible endpoints are responding correctly!${NC}"
    echo -e "${YELLOW}Note: Many endpoints require authentication and will return 401 status codes.${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Check the output above for details.${NC}"
    exit 1
fi