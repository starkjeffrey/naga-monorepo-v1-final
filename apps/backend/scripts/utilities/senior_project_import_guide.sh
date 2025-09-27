#!/bin/bash

# Senior Project CSV Import and Billing Reconciliation Guide
# Usage guide for importing senior project data and reconciling billing

set -e

echo "🎓 Senior Project Data Import and Billing Reconciliation Guide"
echo "=============================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the backend directory
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Please run this script from the backend directory${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Prerequisites:${NC}"
echo "1. CSV file should be at: data/migrate/Senior and Practicum Students-Updated June 2025.csv"
echo "2. Migration 0006_add_senior_project_csv_fields.py should be applied"
echo "3. Senior project courses (IR-489, BUS-489, FIN-489) should exist in database"
echo ""

echo -e "${YELLOW}⚠️  IMPORTANT: This will run against your current database environment${NC}"
echo "Make sure you're running against the correct database (LOCAL vs MIGRATION)"
echo ""

# Check if CSV file exists
CSV_FILE="data/migrate/Senior and Practicum Students-Updated June 2025.csv"
if [ ! -f "$CSV_FILE" ]; then
    echo -e "${RED}❌ CSV file not found at: $CSV_FILE${NC}"
    echo "Please ensure the CSV file is in the correct location."
    exit 1
fi

echo -e "${GREEN}✅ CSV file found${NC}"
echo ""

echo -e "${BLUE}🚀 Step 1: Apply Database Migration${NC}"
echo "This adds the required fields to SeniorProjectGroup model:"
echo ""
echo "USE_DOCKER=no uv run python manage.py migrate curriculum"
echo ""

echo -e "${BLUE}📊 Step 2: Import Senior Project Data (DRY RUN)${NC}"
echo "First, run a dry-run to see what would be imported:"
echo ""
echo "USE_DOCKER=no uv run python manage.py import_senior_projects_csv \\"
echo "    --dry-run \\"
echo "    --create-missing-terms \\"
echo "    --csv-file='$CSV_FILE'"
echo ""

echo -e "${BLUE}📥 Step 3: Import Senior Project Data (ACTUAL)${NC}"
echo "If dry-run looks good, run the actual import:"
echo ""
echo "USE_DOCKER=no uv run python manage.py import_senior_projects_csv \\"
echo "    --create-missing-terms \\"
echo "    --update-academic-journeys \\"
echo "    --csv-file='$CSV_FILE'"
echo ""

echo -e "${BLUE}💰 Step 4: Billing Reconciliation (DRY RUN)${NC}"
echo "Analyze billing discrepancies without making changes:"
echo ""
echo "USE_DOCKER=no uv run python manage.py reconcile_senior_project_billing \\"
echo "    --dry-run \\"
echo "    --course=all"
echo ""

echo -e "${BLUE}🔧 Step 5: Fix Billing Discrepancies (OPTIONAL)${NC}"
echo "If discrepancies found, fix them:"
echo ""
echo "USE_DOCKER=no uv run python manage.py reconcile_senior_project_billing \\"
echo "    --fix-discrepancies \\"
echo "    --course=all"
echo ""

echo -e "${BLUE}📊 Step 6: Generate Reports${NC}"
echo "Both commands generate detailed reports in project-docs/migration-reports/"
echo "Review the reports for:"
echo "- Import success/failure statistics"
echo "- Billing discrepancy details"
echo "- Recommendations for follow-up actions"
echo ""

echo -e "${YELLOW}🎯 Quick Commands for Specific Courses:${NC}"
echo ""
echo "# Import and reconcile just IR-489 projects:"
echo "USE_DOCKER=no uv run python manage.py reconcile_senior_project_billing --course=IR-489"
echo ""
echo "# Import and reconcile just BUS-489 projects:"
echo "USE_DOCKER=no uv run python manage.py reconcile_senior_project_billing --course=BUS-489"
echo ""
echo "# Import and reconcile just FIN-489 projects:"
echo "USE_DOCKER=no uv run python manage.py reconcile_senior_project_billing --course=FIN-489"
echo ""

echo -e "${GREEN}📝 Report Locations:${NC}"
echo "After running the commands, check these locations for detailed reports:"
echo "- project-docs/migration-reports/import_senior_projects_csv_YYYY-MM-DD.md"
echo "- project-docs/migration-reports/reconcile_senior_project_billing_YYYY-MM-DD.md"
echo ""

echo -e "${BLUE}🔍 Verification Steps:${NC}"
echo "After import, verify the data:"
echo ""
echo "1. Check Django admin for SeniorProjectGroup records"
echo "2. Verify team member counts match CSV data"
echo "3. Confirm graduation status is correctly set"
echo "4. Review billing reconciliation report for discrepancies"
echo "5. Test AcademicJourney updates for graduated students"
echo ""

echo -e "${YELLOW}⚠️  Common Issues and Solutions:${NC}"
echo ""
echo "• 'Course not found' error:"
echo "  → Ensure IR-489, BUS-489, FIN-489 courses exist in database"
echo "  → Check course codes match exactly (case-sensitive)"
echo ""
echo "• 'Advisor not found' warning:"
echo "  → Review advisor names in CSV vs TeacherProfile records"
echo "  → Consider creating missing advisor records first"
echo ""
echo "• 'Student not found' warning:"
echo "  → Some students may not exist in current database"
echo "  → This is normal for historical data - students will be skipped"
echo ""
echo "• Billing discrepancies:"
echo "  → Review pricing tier configuration"
echo "  → Check finance system integration"
echo "  → Verify transaction records are accessible"
echo ""

echo -e "${GREEN}✨ Success! You're ready to import senior project data.${NC}"
echo ""
echo "Run the commands above step by step, reviewing output at each stage."
echo "The comprehensive audit reports will help you track progress and identify any issues."