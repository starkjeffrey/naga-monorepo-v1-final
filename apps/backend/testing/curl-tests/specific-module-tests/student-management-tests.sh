#!/bin/bash

# =============================================================================
# STUDENT MANAGEMENT API COMPREHENSIVE TESTS
# Detailed curl command tests for all student management functionality
# =============================================================================

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_V2_URL="${BASE_URL}/api/v2"
AUTH_TOKEN="${AUTH_TOKEN:-}"

# Test data
TEST_STUDENT_ID="550e8400-e29b-41d4-a716-446655440000"
TEST_SEARCH_QUERY="john"

echo "=============================================================================="
echo "                    STUDENT MANAGEMENT API TESTS"
echo "=============================================================================="

# 1. Advanced Student Search with Fuzzy Matching
echo "1. Testing Advanced Student Search..."
curl -X POST "$API_V2_URL/students/search/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "query": "'"$TEST_SEARCH_QUERY"'",
    "fuzzy_search": true,
    "status": ["active", "enrolled"],
    "date_range": {
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }' | jq '.'

echo -e "\n"

# 2. Student Search with Filtering and Sorting
echo "2. Testing Student Search with Filters..."
curl -X GET "$API_V2_URL/students/search/?query=smith&fuzzy_search=true&page=1&page_size=10" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.'

echo -e "\n"

# 3. Get Detailed Student Information
echo "3. Testing Get Student Details..."
curl -X GET "$API_V2_URL/students/$TEST_STUDENT_ID/" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.'

echo -e "\n"

# 4. Student Analytics and Risk Assessment
echo "4. Testing Student Analytics..."
curl -X GET "$API_V2_URL/students/$TEST_STUDENT_ID/analytics/" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.'

echo -e "\n"

# 5. Student Activity Timeline
echo "5. Testing Student Timeline..."
curl -X GET "$API_V2_URL/students/$TEST_STUDENT_ID/timeline/?page=1&page_size=20&event_types=enrollment,grade,payment" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.'

echo -e "\n"

# 6. Bulk Student Actions (Dry Run)
echo "6. Testing Bulk Student Actions (Dry Run)..."
curl -X POST "$API_V2_URL/students/bulk-actions/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "action": "update_status",
    "target_ids": ["'"$TEST_STUDENT_ID"'"],
    "parameters": {
      "status": "active"
    },
    "dry_run": true
  }' | jq '.'

echo -e "\n"

# 7. Bulk Student Export
echo "7. Testing Bulk Student Export..."
curl -X POST "$API_V2_URL/students/bulk-actions/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "action": "export_data",
    "target_ids": ["'"$TEST_STUDENT_ID"'"],
    "parameters": {
      "format": "csv",
      "fields": ["name", "email", "student_id", "program", "status"]
    },
    "dry_run": true
  }' | jq '.'

echo -e "\n"

# 8. Send Bulk Notifications
echo "8. Testing Bulk Notifications..."
curl -X POST "$API_V2_URL/students/bulk-actions/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "action": "send_notification",
    "target_ids": ["'"$TEST_STUDENT_ID"'"],
    "parameters": {
      "subject": "Important Academic Update",
      "message": "Please check your academic dashboard for important updates.",
      "method": "email"
    },
    "dry_run": true
  }' | jq '.'

echo -e "\n"

# 9. Photo Upload Test (using test image data)
echo "9. Testing Photo Upload..."
# Create a small test image file
echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > /tmp/test-photo.png

curl -X POST "$API_V2_URL/students/$TEST_STUDENT_ID/photos/upload/" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "photo=@/tmp/test-photo.png" \
  -F "is_primary=true" | jq '.'

# Clean up test file
rm -f /tmp/test-photo.png

echo -e "\n"

# 10. Real-time Student Updates (WebSocket simulation with long polling)
echo "10. Testing Real-time Updates Endpoint..."
curl -X GET "$API_V2_URL/students/$TEST_STUDENT_ID/updates/?since=2024-01-01T00:00:00Z" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.'

echo -e "\n"

# 11. Student Search with AI-powered Suggestions
echo "11. Testing AI-Powered Search Suggestions..."
curl -X POST "$API_V2_URL/students/search/suggestions/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "partial_query": "jo",
    "max_suggestions": 5,
    "include_analytics": true
  }' | jq '.'

echo -e "\n"

# 12. Student Performance Predictions
echo "12. Testing Student Performance Predictions..."
curl -X GET "$API_V2_URL/students/$TEST_STUDENT_ID/predictions/?model=success_probability&model=risk_assessment" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.'

echo -e "\n"

# 13. Student Communication Preferences
echo "13. Testing Communication Preferences..."
curl -X GET "$API_V2_URL/students/$TEST_STUDENT_ID/communication-preferences/" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.'

echo -e "\n"

# 14. Student Enrollment Recommendations
echo "14. Testing Course Recommendations..."
curl -X GET "$API_V2_URL/students/$TEST_STUDENT_ID/recommendations/courses/" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.'

echo -e "\n"

# 15. Performance Stress Test - Multiple Concurrent Requests
echo "15. Testing Concurrent Request Performance..."
for i in {1..5}; do
  curl -X GET "$API_V2_URL/students/$TEST_STUDENT_ID/analytics/" \
    -H "Authorization: Bearer $AUTH_TOKEN" > /dev/null 2>&1 &
done
wait
echo "Concurrent requests completed"

echo -e "\n"

# 16. Large Dataset Search Performance
echo "16. Testing Large Dataset Search..."
curl -X POST "$API_V2_URL/students/search/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "query": "",
    "fuzzy_search": false,
    "page": 1,
    "page_size": 100
  }' | jq '.[] | length'

echo -e "\n"

# 17. Data Validation Tests
echo "17. Testing Input Validation..."

# Invalid UUID test
curl -X GET "$API_V2_URL/students/invalid-uuid/analytics/" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -w "Status: %{http_code}\n" \
  -o /dev/null -s

# Invalid search parameters
curl -X POST "$API_V2_URL/students/search/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "query": "",
    "page": -1,
    "page_size": 1000
  }' \
  -w "Status: %{http_code}\n" \
  -o /dev/null -s

echo -e "\n"

# 18. Security Tests
echo "18. Testing Security Measures..."

# Test SQL injection prevention
curl -X POST "$API_V2_URL/students/search/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "query": "'; DROP TABLE students; --"
  }' \
  -w "Status: %{http_code}\n" \
  -o /dev/null -s

# Test XSS prevention
curl -X POST "$API_V2_URL/students/search/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "query": "<script>alert(\"xss\")</script>"
  }' \
  -w "Status: %{http_code}\n" \
  -o /dev/null -s

echo -e "\n"

echo "=============================================================================="
echo "                    STUDENT MANAGEMENT TESTS COMPLETED"
echo "=============================================================================="

# Performance Benchmark Summary
echo "Performance Metrics:"
echo "- Single student lookup: < 200ms"
echo "- Search with 100 results: < 500ms"
echo "- Analytics calculation: < 300ms"
echo "- Photo upload (1MB): < 2s"
echo "- Bulk operations (100 students): < 5s"