#!/bin/bash

# Test Data Integrity Checker
# This script checks what data exists in the current test database

set -e

echo "🔍 Test Database Data Inventory"
echo "==============================="

TEST_COMPOSE="docker-compose.test.yml"

# Ensure test environment is running
echo "🚀 Starting test environment (if not already running)..."
docker compose -f ${TEST_COMPOSE} up -d postgres
docker compose -f ${TEST_COMPOSE} exec -T postgres sh -c 'until pg_isready -U $POSTGRES_USER -d $POSTGRES_DB; do sleep 1; done'
echo "✅ Database is ready"

echo ""
echo "📊 Data Inventory:"
echo "-----------------"

# Function to check table data
check_table() {
    local table_name=$1
    local description=$2

    local count=$(docker compose -f ${TEST_COMPOSE} exec -T postgres psql -U debug -d naga_test_v1 -t -c "SELECT COUNT(*) FROM ${table_name};" 2>/dev/null || echo "0")
    count=$(echo $count | tr -d ' ')

    if [ "$count" = "0" ]; then
        echo "  ❌ ${description}: ${count} records"
    else
        echo "  ✅ ${description}: ${count} records"
    fi
}

# Core system tables
echo ""
echo "👥 Users & Authentication:"
check_table "auth_user" "Users"
check_table "auth_group" "Groups"
check_table "auth_permission" "Permissions"

echo ""
echo "👤 People & Profiles:"
check_table "people_person" "People"
check_table "people_studentprofile" "Student Profiles"
check_table "people_teacherprofile" "Teacher Profiles"
check_table "people_emergencycontact" "Emergency Contacts"

echo ""
echo "📚 Curriculum & Academic:"
check_table "curriculum_course" "Courses"
check_table "curriculum_term" "Terms"
check_table "curriculum_academicprogram" "Academic Programs"
check_table "curriculum_division" "Divisions"
check_table "academic_requirement" "Academic Requirements"

echo ""
echo "📝 Enrollment & Scheduling:"
check_table "enrollment_programenrollment" "Program Enrollments"
check_table "enrollment_classheaderenrollment" "Class Enrollments"
check_table "scheduling_classheader" "Class Headers"
check_table "scheduling_classsession" "Class Sessions"

echo ""
echo "💰 Finance:"
check_table "finance_invoice" "Invoices"
check_table "finance_payment" "Payments"
check_table "finance_coursepric1ing" "Course Pricing"
check_table "finance_studentfinancepackage" "Finance Packages"

echo ""
echo "🎯 Attendance & Grading:"
check_table "attendance_attendancerecord" "Attendance Records"
check_table "grading_classpartgrade" "Class Part Grades"
check_table "grading_gparecord" "GPA Records"

echo ""
echo "🏆 Scholarships & Testing:"
check_table "scholarships_sponsor" "Sponsors"
check_table "scholarships_sponsoredstudent" "Sponsored Students"
check_table "level_testing_placementtest" "Placement Tests"

echo ""
echo "🏢 Administrative:"
check_table "common_room" "Rooms"
check_table "common_holiday" "Holidays"
check_table "accounts_department" "Departments"
check_table "accounts_role" "Roles"

echo ""
echo "📋 Summary:"
echo "----------"
TOTAL_TABLES=$(docker compose -f ${TEST_COMPOSE} exec -T postgres psql -U debug -d naga_test_v1 -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
TOTAL_TABLES=$(echo $TOTAL_TABLES | tr -d ' ')
echo "  📊 Total tables in database: ${TOTAL_TABLES}"

TABLES_WITH_DATA=$(docker compose -f ${TEST_COMPOSE} exec -T postgres psql -U debug -d naga_test_v1 -t -c "
SELECT COUNT(*) FROM (
    SELECT schemaname,tablename
    FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename NOT LIKE 'django_%'
    AND tablename NOT LIKE 'auth_%'
) t
")
TABLES_WITH_DATA=$(echo $TABLES_WITH_DATA | tr -d ' ')

echo "  📈 App-specific tables: ${TABLES_WITH_DATA}"
echo ""
echo "💡 Ready for backup verification process!"
