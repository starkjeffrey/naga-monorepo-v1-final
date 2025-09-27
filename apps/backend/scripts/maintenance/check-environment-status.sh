#!/bin/bash
# Quick status check for all three database environments
#
# This script shows the current status of LOCAL, TEST, and MIGRATION environments
# including service status and basic data counts.
#
# Usage: ./scripts/check-environment-status.sh

set -e

# Color output functions
red() { echo -e "\033[31m$1\033[0m"; }
green() { echo -e "\033[32m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }
blue() { echo -e "\033[34m$1\033[0m"; }
bold() { echo -e "\033[1m$1\033[0m"; }

# Ensure we're in the project root
cd "$(dirname "$0")/.."

echo "$(bold "🔍 Naga Backend v1.0 - Environment Status Check")"
echo "⏰ $(date)"
echo

# Function to check service status
check_service_status() {
    local compose_file=$1
    local env_name=$2
    local service=$3
    
    if docker compose -f $compose_file ps $service | grep -q "Up"; then
        echo "$(green "✅ $service")"
        return 0
    else
        echo "$(red "❌ $service")"
        return 1
    fi
}

# Function to get data counts
get_data_counts() {
    local compose_file=$1
    local env_name=$2
    
    echo "📊 Data Status:"
    
    if docker compose -f $compose_file ps django | grep -q "Up"; then
        docker compose -f $compose_file exec django python manage.py shell -c "
from apps.people.models import Person, StudentProfile
from apps.curriculum.models import Course, Term, Division
from apps.enrollment.models import ClassHeaderEnrollment

try:
    students = StudentProfile.objects.count()
    people = Person.objects.count()
    courses = Course.objects.count()
    terms = Term.objects.count()
    divisions = Division.objects.count()
    enrollments = ClassHeaderEnrollment.objects.count()
    
    print(f'   Students: {students:,}')
    print(f'   People: {people:,}')
    print(f'   Courses: {courses:,}')
    print(f'   Terms: {terms:,}')
    print(f'   Divisions: {divisions:,}')
    print(f'   Enrollments: {enrollments:,}')
    
    # Calculate some metrics
    if people > 0:
        student_ratio = (students / people) * 100
        print(f'   Student/People ratio: {student_ratio:.1f}%')
    
    if students > 0 and enrollments > 0:
        avg_enrollments = enrollments / students
        print(f'   Avg enrollments per student: {avg_enrollments:.1f}')
        
except Exception as e:
    print(f'   Error getting data: {e}')
" 2>/dev/null
    else
        echo "   $(yellow "⚠️  Django service not running - cannot get data counts")"
    fi
}

# Function to check environment
check_environment() {
    local compose_file=$1
    local env_name=$2
    local db_type=$3
    
    echo "$(bold "━━━ $env_name ENVIRONMENT ━━━")"
    echo "📁 Compose file: $compose_file"
    echo "🗄️  Database type: $db_type"
    echo
    
    echo "🔧 Service Status:"
    local django_status=0
    local db_status=0
    
    check_service_status $compose_file $env_name "django" || django_status=1
    
    if [ "$db_type" = "PostgreSQL" ]; then
        check_service_status $compose_file $env_name "postgres" || db_status=1
    else
        echo "$(blue "ℹ️  SQLite (in-memory, no separate service needed)")"
    fi
    
    # Check additional services
    if docker compose -f $compose_file ps redis 2>/dev/null | grep -q "Up"; then
        check_service_status $compose_file $env_name "redis"
    fi
    
    if docker compose -f $compose_file ps mailpit 2>/dev/null | grep -q "Up"; then
        check_service_status $compose_file $env_name "mailpit"
    fi
    
    echo
    
    # Get data counts if services are running
    if [ $django_status -eq 0 ]; then
        get_data_counts $compose_file $env_name
    else
        echo "📊 Data Status: $(yellow "Cannot check - Django not running")"
    fi
    
    echo
    
    # Show URLs if services are running
    if [ $django_status -eq 0 ]; then
        case $env_name in
            "LOCAL")
                echo "🌐 Access URLs:"
                echo "   • Django: $(green "http://localhost:8000")"
                if docker compose -f $compose_file ps mailpit 2>/dev/null | grep -q "Up"; then
                    echo "   • Mailpit: $(green "http://localhost:8025")"
                fi
                ;;
            "TEST")
                echo "🌐 Access URLs:"
                echo "   • Django: $(green "http://localhost:8001")"
                ;;
            "MIGRATION")
                echo "🌐 Access URLs:"
                echo "   • Django: $(green "http://localhost:8002")"
                ;;
        esac
        echo
    fi
}

# Main status check
main() {
    # Check LOCAL environment
    check_environment "docker-compose.local.yml" "LOCAL" "PostgreSQL"
    
    # Note: Testing now done locally with SQLite - no separate environment needed
    
    # Check MIGRATION environment
    check_environment "docker-compose.migration.yml" "MIGRATION" "PostgreSQL"
    
    echo "$(bold "━━━ SUMMARY ━━━")"
    
    # Quick service overview
    echo "🏃 Running Services:"
    local total_services=0
    local running_services=0
    
    for env in "docker-compose.local.yml:LOCAL" "docker-compose.migration.yml:MIGRATION"; do
        IFS=':' read -r compose_file env_name <<< "$env"
        
        if docker compose -f $compose_file ps django 2>/dev/null | grep -q "Up"; then
            echo "   • $(green "$env_name Django ✅")"
            running_services=$((running_services + 1))
        else
            echo "   • $(red "$env_name Django ❌")"
        fi
        total_services=$((total_services + 1))
    done
    
    # Check local testing capability
    if command -v uv >/dev/null 2>&1; then
        echo "   • $(green "Local Testing (uv) ✅")"
    else
        echo "   • $(yellow "Local Testing (uv) ⚠️  - install uv for fastest testing")"
    fi
    
    echo
    echo "📈 Service Health: $running_services/$total_services environments running"
    
    if [ $running_services -eq $total_services ]; then
        echo "$(green "🎉 All environments are healthy!")"
    elif [ $running_services -gt 0 ]; then
        echo "$(yellow "⚠️  Some environments need attention")"
    else
        echo "$(red "🚨 No environments are running")"
    fi
    
    echo
    echo "🛠️  Quick Actions:"
    echo "   • Start LOCAL: docker compose -f docker-compose.local.yml up -d"
    echo "   • Start MIGRATION: docker compose -f docker-compose.migration.yml up -d"
    echo "   • Run Tests: DATABASE_URL=\"sqlite:///:memory:\" DJANGO_SETTINGS_MODULE=config.settings.test_sqlite uv run pytest"
    echo "   • Refresh LOCAL from MIGRATION: ./scripts/refresh-local-from-migration.sh"
    echo
}

# Run main function
main "$@"