#!/bin/bash
# Compare data counts across LOCAL, TEST, and MIGRATION environments
#
# This script provides a side-by-side comparison of data in all three environments
# to help identify inconsistencies or verify successful data migrations.
#
# Usage: ./scripts/compare-environment-data.sh

set -e

# Color output functions
red() { echo -e "\033[31m$1\033[0m"; }
green() { echo -e "\033[32m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }
blue() { echo -e "\033[34m$1\033[0m"; }
bold() { echo -e "\033[1m$1\033[0m"; }

# Ensure we're in the project root
cd "$(dirname "$0")/.."

echo "$(bold "📊 Environment Data Comparison")"
echo "⏰ $(date)"
echo

# Function to get detailed data counts
get_detailed_counts() {
    local compose_file=$1
    local env_name=$2
    
    if ! docker compose -f $compose_file ps django | grep -q "Up"; then
        echo "❌,$env_name,Service Down,,,,,,,,"
        return
    fi
    
    docker compose -f $compose_file exec django python manage.py shell -c "
from apps.people.models import Person, StudentProfile
from apps.curriculum.models import Course, Term, Division
from apps.enrollment.models import ClassHeaderEnrollment, ClassHeader
from apps.scheduling.models import ClassSession, ClassPart

try:
    # Core counts
    people = Person.objects.count()
    students = StudentProfile.objects.count()
    courses = Course.objects.count()
    terms = Term.objects.count()
    divisions = Division.objects.count()
    
    # Enrollment counts
    class_headers = ClassHeader.objects.count()
    enrollments = ClassHeaderEnrollment.objects.count()
    
    # Scheduling counts
    sessions = ClassSession.objects.count()
    parts = ClassPart.objects.count()
    
    # Status: OK if we have students, courses, and terms
    if students > 0 and courses > 0 and terms > 0:
        status = 'OK'
    elif students == 0 and courses == 0 and terms == 0:
        status = 'Empty'
    else:
        status = 'Partial'
    
    print(f'{status},$env_name,{people},{students},{courses},{terms},{divisions},{class_headers},{enrollments},{sessions},{parts}')
    
except Exception as e:
    print(f'Error,$env_name,Error: {str(e)[:50]}...,,,,,,,')
" 2>/dev/null
}

# Collect data from all environments
echo "🔍 Collecting data from all environments..."
echo

# Create temporary file for data
temp_file=$(mktemp)

# Headers
echo "Status,Environment,People,Students,Courses,Terms,Divisions,ClassHeaders,Enrollments,Sessions,Parts" > $temp_file

# Get data from each environment
get_detailed_counts "docker-compose.local.yml" "LOCAL" >> $temp_file
get_detailed_counts "docker-compose.migration.yml" "MIGRATION" >> $temp_file

# Note: Testing is now done locally with SQLite - no separate environment to check

# Display results in formatted table
echo "$(bold "📈 Data Comparison Table")"
echo

# Use column command to format the CSV nicely
if command -v column >/dev/null 2>&1; then
    column -t -s',' $temp_file
else
    cat $temp_file
fi

echo
echo

# Analysis
echo "$(bold "🔍 Analysis")"
echo

# Read the data and perform analysis
local_data=""
migration_data=""

while IFS=',' read -r status env people students courses terms divisions headers enrollments sessions parts; do
    if [ "$env" = "LOCAL" ]; then
        local_data="$status,$people,$students,$courses,$terms,$divisions,$headers,$enrollments,$sessions,$parts"
    elif [ "$env" = "MIGRATION" ]; then
        migration_data="$status,$people,$students,$courses,$terms,$divisions,$headers,$enrollments,$sessions,$parts"
    fi
done < <(tail -n +2 $temp_file)

# Parse the data for analysis
IFS=',' read -r local_status local_people local_students local_courses local_terms local_divisions local_headers local_enrollments local_sessions local_parts <<< "$local_data"
IFS=',' read -r migration_status migration_people migration_students migration_courses migration_terms migration_divisions migration_headers migration_enrollments migration_sessions migration_parts <<< "$migration_data"

# Environment status analysis
echo "🏥 Environment Health:"
case $local_status in
    "OK") echo "   • LOCAL: $(green "✅ Healthy") ($local_students students, $local_courses courses)" ;;
    "Empty") echo "   • LOCAL: $(yellow "⚠️  Empty") (no data)" ;;
    "Partial") echo "   • LOCAL: $(yellow "⚠️  Partial data") ($local_students students, $local_courses courses)" ;;
    "Error") echo "   • LOCAL: $(red "❌ Error") (service issues)" ;;
    *) echo "   • LOCAL: $(red "❌ Not running")" ;;
esac

# Check local testing capability
if command -v uv >/dev/null 2>&1; then
    echo "   • Testing: $(green "✅ Local SQLite available") (uv installed)"
else
    echo "   • Testing: $(yellow "⚠️  Install uv for optimal testing") (SQLite available but slower)"
fi

case $migration_status in
    "OK") echo "   • MIGRATION: $(green "✅ Healthy") ($migration_students students, $migration_courses courses)" ;;
    "Empty") echo "   • MIGRATION: $(yellow "⚠️  Empty") (needs legacy data import)" ;;
    "Partial") echo "   • MIGRATION: $(yellow "⚠️  Partial data") ($migration_students students, $migration_courses courses)" ;;
    "Error") echo "   • MIGRATION: $(red "❌ Error") (service issues)" ;;
    *) echo "   • MIGRATION: $(red "❌ Not running")" ;;
esac

echo

# Data consistency analysis
if [[ "$local_status" == "OK" && "$migration_status" == "OK" ]]; then
    echo "🔄 LOCAL vs MIGRATION Comparison:"
    
    # Compare key metrics
    if [ "$local_students" -eq "$migration_students" ] && [ "$local_courses" -eq "$migration_courses" ]; then
        echo "   • $(green "✅ Data in sync") (same student and course counts)"
    else
        echo "   • $(yellow "⚠️  Data differs:")"
        echo "     - Students: LOCAL=$local_students, MIGRATION=$migration_students"
        echo "     - Courses: LOCAL=$local_courses, MIGRATION=$migration_courses"
        
        if [ "$migration_students" -gt "$local_students" ]; then
            echo "     - $(blue "💡 Suggestion:") LOCAL may need refresh from MIGRATION"
        elif [ "$local_students" -gt "$migration_students" ]; then
            echo "     - $(blue "💡 Suggestion:") MIGRATION may need more legacy data import"
        fi
    fi
    echo
fi

# Enrollment analysis
if [[ "$local_status" == "OK" || "$migration_status" == "OK" ]]; then
    echo "🎓 Enrollment Analysis:"
    
    for env in "LOCAL" "MIGRATION"; do
        if [ "$env" = "LOCAL" ] && [ "$local_status" = "OK" ]; then
            students=$local_students
            enrollments=$local_enrollments
            headers=$local_headers
        elif [ "$env" = "MIGRATION" ] && [ "$migration_status" = "OK" ]; then
            students=$migration_students
            enrollments=$migration_enrollments
            headers=$migration_headers
        else
            continue
        fi
        
        if [ "$students" -gt 0 ] && [ "$enrollments" -gt 0 ]; then
            avg_enrollments=$(echo "scale=1; $enrollments / $students" | bc 2>/dev/null || echo "N/A")
            echo "   • $env: $enrollments total enrollments, avg $avg_enrollments per student"
        elif [ "$students" -gt 0 ]; then
            echo "   • $env: $students students but no enrollments ($(yellow "needs enrollment data"))"
        fi
    done
    echo
fi

# Recommendations
echo "$(bold "💡 Recommendations")"
echo

# Check if LOCAL needs refresh
if [[ "$local_status" == "OK" && "$migration_status" == "OK" && "$migration_students" -gt "$local_students" ]]; then
    echo "🔄 Data Refresh:"
    echo "   • MIGRATION has more data than LOCAL"
    echo "   • Run: $(blue "./scripts/refresh-local-from-migration.sh")"
    echo
fi

# Check if MIGRATION needs more data
if [[ "$migration_status" == "Empty" || ("$migration_status" == "OK" && "$migration_students" -lt 50) ]]; then
    echo "📥 MIGRATION Data Import:"
    echo "   • MIGRATION environment needs more legacy data"
    echo "   • Check available import scripts in scripts/migration_environment/"
    echo
fi

# Check Testing setup
echo "⚡ Testing Environment:"
if command -v uv >/dev/null 2>&1; then
    echo "   • Local SQLite testing ready with uv"
    echo "   • Run: DATABASE_URL=\"sqlite:///:memory:\" DJANGO_SETTINGS_MODULE=config.settings.test_sqlite uv run pytest"
else
    echo "   • Install uv for optimal testing: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi
echo "   • Use factory.create() in tests to generate data as needed"
echo

# Service status recommendations
all_running=true
if [[ "$local_status" == "Error" || "$local_status" == "" ]]; then
    echo "🚀 Start LOCAL: $(blue "docker compose -f docker-compose.local.yml up -d")"
    all_running=false
fi

# Testing is now local - no service to start

if [[ "$migration_status" == "Error" || "$migration_status" == "" ]]; then
    echo "🚀 Start MIGRATION: $(blue "docker compose -f docker-compose.migration.yml up -d")"
    all_running=false
fi

if $all_running; then
    echo "$(green "🎉 All environments are running!")"
    echo "📝 Run tests locally: DATABASE_URL=\"sqlite:///:memory:\" DJANGO_SETTINGS_MODULE=config.settings.test_sqlite uv run pytest"
fi

# Clean up
rm -f $temp_file

echo
echo "$(bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")"
echo "📝 For detailed status: ./scripts/check-environment-status.sh"
echo "🔄 To refresh LOCAL: ./scripts/refresh-local-from-migration.sh"