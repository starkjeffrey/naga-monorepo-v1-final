#!/bin/bash
# Dump fixtures for all apps in the Naga SIS

echo "🚀 Starting comprehensive fixture dump..."
echo "📅 Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

# Common app fixtures
echo -e "\n📦 Dumping common app fixtures..."
docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    common.Holiday \
    common.Room \
    --format=json --indent=2 > apps/common/fixtures/common_foundation.json
echo "✅ Created common_foundation.json"

# Geography app fixtures
echo -e "\n🌍 Dumping geography app fixtures..."
docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    geography.Country \
    geography.Province \
    geography.District \
    geography.Commune \
    geography.Village \
    --format=json --indent=2 > apps/geography/fixtures/geography_data.json
echo "✅ Created geography_data.json"

# Facilities app fixtures
echo -e "\n🏢 Dumping facilities app fixtures..."
docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    facilities.Building \
    facilities.Floor \
    facilities.RoomType \
    --format=json --indent=2 > apps/facilities/fixtures/facilities_config.json
echo "✅ Created facilities_config.json"

# Curriculum app fixtures (already done but let's be comprehensive)
echo -e "\n📚 Dumping curriculum app fixtures..."
docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    curriculum.Division \
    --format=json --indent=2 > apps/curriculum/fixtures/divisions.json
echo "✅ Created divisions.json"

docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    curriculum.Major \
    --format=json --indent=2 > apps/curriculum/fixtures/majors.json
echo "✅ Created majors.json"

docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    curriculum.Cycle \
    --format=json --indent=2 > apps/curriculum/fixtures/cycles.json
echo "✅ Created cycles.json"

docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    curriculum.Term \
    --format=json --indent=2 > apps/curriculum/fixtures/terms.json
echo "✅ Created terms.json"

docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    curriculum.Course \
    curriculum.CoursePrerequisite \
    --format=json --indent=2 > apps/curriculum/fixtures/courses.json
echo "✅ Created courses.json"

# Academic app fixtures
echo -e "\n🎓 Dumping academic app fixtures..."
docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    academic.CanonicalRequirement \
    --format=json --indent=2 > apps/academic/fixtures/canonical_requirements.json
echo "✅ Created canonical_requirements.json"

# Finance app fixtures (comprehensive)
echo -e "\n💰 Dumping finance app fixtures..."
docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    finance.DefaultPricing \
    finance.CourseFixedPricing \
    finance.SeniorProjectPricing \
    finance.ReadingClassPricing \
    finance.FeePricing \
    --format=json --indent=2 > apps/finance/fixtures/pricing_config.json
echo "✅ Created pricing_config.json"

docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    finance.GLAccount \
    finance.FeeGLMapping \
    --format=json --indent=2 > apps/finance/fixtures/gl_accounts.json
echo "✅ Created gl_accounts.json"

docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    finance.DiscountRule \
    --format=json --indent=2 > apps/finance/fixtures/discount_rules.json
echo "✅ Created discount_rules.json"

# Scholarships app fixtures
echo -e "\n🎁 Dumping scholarships app fixtures..."
docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    scholarships.Sponsor \
    --format=json --indent=2 > apps/scholarships/fixtures/sponsors.json
echo "✅ Created sponsors.json"

# Scheduling app fixtures (if models exist)
echo -e "\n📅 Checking scheduling app fixtures..."
docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    scheduling \
    --format=json --indent=2 > apps/scheduling/fixtures/scheduling_config.json 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Created scheduling_config.json"
else
    echo "⚠️  No scheduling models found to dump"
fi

# Grading app fixtures (if models exist)
echo -e "\n📊 Checking grading app fixtures..."
docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    grading \
    --format=json --indent=2 > apps/grading/fixtures/grading_config.json 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Created grading_config.json"
else
    echo "⚠️  No grading models found to dump"
fi

# Level Testing app fixtures
echo -e "\n📝 Checking level testing app fixtures..."
docker compose -f docker-compose.local.yml run --rm django python manage.py dumpdata \
    level_testing.TestType \
    level_testing.TestLevel \
    --format=json --indent=2 > apps/level_testing/fixtures/test_config.json 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Created test_config.json"
else
    echo "⚠️  No level testing configuration found to dump"
fi

echo -e "\n✨ Fixture dump complete!"
echo -e "\n📋 Summary of created fixtures:"
find apps/*/fixtures -name "*.json" -type f -newer /tmp -exec ls -lh {} \; 2>/dev/null | awk '{print $9, "-", $5}'

echo -e "\n💡 To load fixtures, use:"
echo "  docker compose -f docker-compose.local.yml run --rm django python manage.py loaddata <fixture_file>"
echo -e "\nOr load all fixtures for an app:"
echo "  docker compose -f docker-compose.local.yml run --rm django python manage.py loaddata 'apps/*/fixtures/*.json'"