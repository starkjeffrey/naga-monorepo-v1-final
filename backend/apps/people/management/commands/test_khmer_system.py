"""Simple test command for Khmer name approximation system."""

from django.core.management.base import BaseCommand
from apps.people.services.name_decomposer import NameDecomposer
from apps.people.services.khmer_approximator import KhmerNameApproximator
from apps.people.models import KhmerNamePattern, Person
from decimal import Decimal


class Command(BaseCommand):
    """Test command for Khmer name approximation system."""

    help = "Test the Khmer name approximation system functionality"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--create-sample-patterns',
            action='store_true',
            help='Create sample patterns for testing'
        )
        parser.add_argument(
            '--test-approximation',
            type=str,
            help='Test approximation for a specific name'
        )

    def handle(self, *args, **options):
        """Handle the command."""
        self.stdout.write("🧪 Testing Khmer Name Approximation System")

        if options['create_sample_patterns']:
            self.create_sample_patterns()

        if options['test_approximation']:
            self.test_approximation(options['test_approximation'])

        # Show system stats
        self.show_stats()

    def create_sample_patterns(self):
        """Create sample patterns for testing."""
        self.stdout.write("📚 Creating sample patterns...")

        patterns = [
            ("sovann", "សុវណ្ណ", 0.85, 17),
            ("dara", "ដារា", 0.92, 23),
            ("chan", "ចន្ទ", 0.78, 12),
            ("reach", "រាជ", 0.81, 15),
            ("sokha", "សុខា", 0.90, 19),
            ("phalla", "ផល្លា", 0.76, 11),
        ]

        for english, khmer, confidence, count in patterns:
            pattern, created = KhmerNamePattern.objects.get_or_create(
                english_component=english,
                defaults={
                    'normalized_component': english,
                    'limon_pattern': khmer,
                    'unicode_pattern': khmer,
                    'frequency': Decimal(str(confidence)),
                    'occurrence_count': count,
                    'confidence_score': Decimal(str(confidence)),
                    'is_verified': True
                }
            )

            if created:
                self.stdout.write(f"  ✅ Created pattern: {english} → {khmer}")
            else:
                self.stdout.write(f"  ℹ️  Pattern exists: {english} → {khmer}")

        self.stdout.write("📚 Sample patterns created!")

    def test_approximation(self, name):
        """Test approximation for a specific name."""
        self.stdout.write(f"🤖 Testing approximation for '{name}'...")

        # Test decomposition
        decomposer = NameDecomposer()
        components = decomposer.decompose(name)

        self.stdout.write("  📂 Name decomposition:")
        for i, comp in enumerate(components):
            self.stdout.write(f"    {i+1}. '{comp.text}' (confidence: {comp.confidence:.2f})")

        # Test approximation
        approximator = KhmerNameApproximator()
        result = approximator.approximate_name(name)

        self.stdout.write("  🎯 Approximation result:")
        self.stdout.write(f"    Original: {result.original_english}")
        self.stdout.write(f"    Approximated: {result.approximated_khmer}")
        self.stdout.write(f"    Display: {result.display_name}")
        self.stdout.write(f"    Confidence: {result.confidence_score:.2f}")
        self.stdout.write(f"    Method: {result.method_used}")

        if result.components_used:
            self.stdout.write("    Components used:")
            for comp in result.components_used:
                self.stdout.write(f"      - {comp['text']} → {comp['pattern']} (method: {comp['method']})")

        if result.warnings:
            self.stdout.write("    Warnings:")
            for warning in result.warnings:
                self.stdout.write(f"      ⚠️  {warning}")

    def show_stats(self):
        """Show system statistics."""
        self.stdout.write("\n📊 System Statistics:")

        pattern_count = KhmerNamePattern.objects.count()
        verified_patterns = KhmerNamePattern.objects.filter(is_verified=True).count()

        people_count = Person.objects.count()
        with_khmer = Person.objects.exclude(khmer_name__exact='').exclude(khmer_name__isnull=True).count()
        approximated = Person.objects.filter(khmer_name_source='approximated').count()

        self.stdout.write(f"  📚 Patterns: {pattern_count} total, {verified_patterns} verified")
        self.stdout.write(f"  👥 People: {people_count} total, {with_khmer} with Khmer names")
        self.stdout.write(f"  🤖 Approximated: {approximated} names")

        if people_count > 0:
            coverage = (with_khmer / people_count) * 100
            self.stdout.write(f"  📈 Coverage: {coverage:.1f}%")

        self.stdout.write("✅ Testing completed!")