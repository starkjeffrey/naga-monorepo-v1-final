#!/bin/bash
# Verify migration completion status
#
# This script checks work status and prevents rework by showing what's already been completed

set -e

# Color output functions
red() { echo -e "\033[31m$1\033[0m"; }
green() { echo -e "\033[32m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }
blue() { echo -e "\033[34m$1\033[0m"; }
bold() { echo -e "\033[1m$1\033[0m"; }

# Ensure we're in the project root
cd "$(dirname "$0")/.."

echo "$(bold "🔍 Migration Completion Verification")"
echo "⏰ $(date)"
echo

# Check work status files
echo "$(bold "📋 Work Status Files:")"
if ls project-docs/work-status/*COMPLETED* 2>/dev/null; then
    for file in project-docs/work-status/*COMPLETED*; do
        basename_file=$(basename "$file")
        echo "  $(green "✅") $basename_file"
    done
else
    echo "  $(yellow "⚠️  No completion status files found")"
fi
echo

# Check session logs
echo "$(bold "📝 Session Logs:")"
if ls project-docs/session-logs/session-*.md 2>/dev/null; then
    for file in project-docs/session-logs/session-*.md; do
        basename_file=$(basename "$file")
        echo "  $(blue "📄") $basename_file"
    done
else
    echo "  $(yellow "⚠️  No session logs found")"
fi
echo

# Check migration scripts with dates
echo "$(bold "🔧 Migration Scripts:")"
find scripts/ -name "*250626*" -o -name "*COMPLETED*" | while read -r file; do
    echo "  $(green "📜") $file"
done
echo

# Check database state in LOCAL environment
echo "$(bold "🗄️  LOCAL Database State:")"
if docker compose -f docker-compose.local.yml ps django | grep -q "Up"; then
    docker compose -f docker-compose.local.yml exec django python manage.py shell -c "
from apps.people.models import Person, StudentProfile
from apps.scholarships.models import SponsoredStudent, Sponsor

print(f'  People: {Person.objects.count():,}')
print(f'  Students: {StudentProfile.objects.count():,}')
print(f'  Sponsors: {Sponsor.objects.count():,}')  
print(f'  Sponsored Students: {SponsoredStudent.objects.count():,}')

if SponsoredStudent.objects.count() > 0:
    print(f'  $(green \"✅ Sponsorships are linked\")')
    for sponsor in Sponsor.objects.all():
        count = SponsoredStudent.objects.filter(sponsor=sponsor).count()
        if count > 0:
            print(f'    {sponsor.code}: {count} students')
else:
    print(f'  $(yellow \"⚠️  No sponsorships found - may need linking\")')
" 2>/dev/null | sed 's/^/  /'
else
    echo "  $(red "❌ LOCAL environment not running")"
fi
echo

# Recommendations
echo "$(bold "💡 Recommendations:")"
echo "  • Check session logs before starting new work"
echo "  • Verify database state matches expected completion"
echo "  • Create status files when completing work"
echo "  • Use date-based naming for scripts and artifacts"
echo

echo "$(bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")"
echo "📝 Always run this script before starting migration work!"
echo "🔄 Use: ./scripts/verify-migration-completion.sh"