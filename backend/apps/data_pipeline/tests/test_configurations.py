"""
Test Configuration System

Tests for table configurations, column mappings, and registry functionality.
"""

import pytest
from django.test import TestCase

from data_pipeline.configs.base import ColumnMapping, ConfigurationError, TableConfig
from data_pipeline.core.registry import TableRegistry
from data_pipeline.validators.terms import TermValidator


class TestColumnMapping(TestCase):
    """Test ColumnMapping functionality"""

    def test_column_mapping_creation(self):
        """Test basic column mapping creation"""
        mapping = ColumnMapping(
            source_name="TestCol",
            target_name="test_col",
            data_type="nvarchar(50)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Test column",
        )

        self.assertEqual(mapping.source_name, "TestCol")
        self.assertEqual(mapping.target_name, "test_col")
        self.assertEqual(mapping.data_type, "nvarchar(50)")
        self.assertTrue(mapping.nullable)
        self.assertEqual(mapping.cleaning_rules, ["trim"])
        self.assertEqual(mapping.validation_priority, 3)  # default

    def test_column_mapping_validation(self):
        """Test column mapping validation"""
        # Valid mapping
        mapping = ColumnMapping(source_name="Valid", target_name="valid", data_type="int", nullable=False)
        errors = mapping.validate()
        self.assertEqual(len(errors), 0)

        # Invalid mapping - missing required fields
        with self.assertRaises(TypeError):
            ColumnMapping()

    def test_column_mapping_sql_generation(self):
        """Test SQL DDL generation from column mapping"""
        mapping = ColumnMapping(
            source_name="TestCol", target_name="test_col", data_type="nvarchar(100)", nullable=False
        )

        sql = mapping.to_sql_column()
        expected = "test_col nvarchar(100) NOT NULL"
        self.assertEqual(sql, expected)

        # Test nullable column
        mapping.nullable = True
        sql = mapping.to_sql_column()
        expected = "test_col nvarchar(100) NULL"
        self.assertEqual(sql, expected)


class TestTableConfig(TestCase):
    """Test TableConfig functionality"""

    def setUp(self):
        """Set up test configuration"""
        self.sample_columns = [
            ColumnMapping(
                source_name="ID", target_name="id", data_type="nvarchar(10)", nullable=False, validation_priority=1
            ),
            ColumnMapping(source_name="Name", target_name="name", data_type="nvarchar(100)", nullable=False),
        ]

    def test_table_config_creation(self):
        """Test basic table config creation"""
        config = TableConfig(
            table_name="test_table",
            source_file_pattern="test.csv",
            description="Test table",
            column_mappings=self.sample_columns,
        )

        self.assertEqual(config.table_name, "test_table")
        self.assertEqual(config.source_file_pattern, "test.csv")
        self.assertEqual(config.raw_table_name, "raw_test_table")  # auto-generated
        self.assertEqual(len(config.column_mappings), 2)

    def test_table_config_validation(self):
        """Test table configuration validation"""
        # Valid configuration
        config = TableConfig(
            table_name="valid_table",
            source_file_pattern="valid.csv",
            description="Valid test table",
            column_mappings=self.sample_columns,
        )
        errors = config.validate()
        self.assertEqual(len(errors), 0)

        # Invalid configuration - no columns
        config = TableConfig(
            table_name="invalid_table",
            source_file_pattern="invalid.csv",
            description="Invalid table",
            column_mappings=[],
        )
        errors = config.validate()
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("column_mappings" in error for error in errors))

    def test_table_config_sql_generation(self):
        """Test SQL DDL generation"""
        config = TableConfig(
            table_name="sql_test", source_file_pattern="test.csv", column_mappings=self.sample_columns
        )

        # Test raw table SQL
        raw_sql = config.generate_raw_table_sql()
        self.assertIn("CREATE TABLE raw_sql_test", raw_sql)
        self.assertIn("id TEXT", raw_sql)  # Raw tables use TEXT
        self.assertIn("name TEXT", raw_sql)

        # Test cleaned table SQL
        cleaned_sql = config.generate_cleaned_table_sql()
        self.assertIn("CREATE TABLE cleaned_sql_test", cleaned_sql)
        self.assertIn("id nvarchar(10) NOT NULL", cleaned_sql)
        self.assertIn("name nvarchar(100) NOT NULL", cleaned_sql)

    def test_table_config_dependencies(self):
        """Test dependency handling"""
        config = TableConfig(
            table_name="dependent_table",
            source_file_pattern="dep.csv",
            column_mappings=self.sample_columns,
            dependencies=["parent_table"],
        )

        self.assertEqual(config.dependencies, ["parent_table"])

        # Test circular dependency detection (would be handled by registry)
        config2 = TableConfig(
            table_name="circular_table",
            source_file_pattern="circular.csv",
            column_mappings=self.sample_columns,
            dependencies=["dependent_table"],
        )

        # The registry should detect this, not the individual config
        self.assertEqual(config2.dependencies, ["dependent_table"])


class TestTableRegistry(TestCase):
    """Test Table Registry functionality"""

    def setUp(self):
        """Set up test registry"""
        # Clear registry for clean tests
        TableRegistry.clear_registry()

        # Create sample configurations
        self.terms_config = TableConfig(
            table_name="terms",
            source_file_pattern="terms.csv",
            column_mappings=[
                ColumnMapping(source_name="TermID", target_name="term_id", data_type="nvarchar(200)", nullable=False)
            ],
            dependencies=[],
            validator_class=TermValidator,
        )

        self.students_config = TableConfig(
            table_name="students",
            source_file_pattern="students.csv",
            column_mappings=[
                ColumnMapping(source_name="ID", target_name="student_id", data_type="nvarchar(10)", nullable=False)
            ],
            dependencies=[],
        )

        self.enrollments_config = TableConfig(
            table_name="enrollments",
            source_file_pattern="enrollments.csv",
            column_mappings=[
                ColumnMapping(
                    source_name="StudentID", target_name="student_id", data_type="nvarchar(10)", nullable=False
                )
            ],
            dependencies=["students", "terms"],
        )

    def test_registry_registration(self):
        """Test table registration"""
        # Register a table
        TableRegistry.register_table(self.terms_config)

        # Verify registration
        self.assertIn("terms", TableRegistry.list_all_tables())

        # Retrieve configuration
        retrieved = TableRegistry.get_config("terms")
        self.assertEqual(retrieved.table_name, "terms")
        self.assertEqual(retrieved.source_file_pattern, "terms.csv")

    def test_registry_validation(self):
        """Test registry validation"""
        # Register valid configuration
        TableRegistry.register_table(self.terms_config)

        # Try to register invalid configuration
        invalid_config = TableConfig(
            table_name="invalid",
            source_file_pattern="invalid.csv",
            column_mappings=[],  # Empty columns - should fail
        )

        with self.assertRaises(ConfigurationError):
            TableRegistry.register_table(invalid_config)

    def test_registry_dependency_order(self):
        """Test dependency ordering"""
        # Register tables with dependencies
        TableRegistry.register_table(self.terms_config)
        TableRegistry.register_table(self.students_config)
        TableRegistry.register_table(self.enrollments_config)

        # Get dependency order
        order = TableRegistry.get_dependency_order()

        # Terms and students should come before enrollments
        terms_idx = order.index("terms")
        students_idx = order.index("students")
        enrollments_idx = order.index("enrollments")

        self.assertLess(terms_idx, enrollments_idx)
        self.assertLess(students_idx, enrollments_idx)

    def test_registry_complexity_order(self):
        """Test complexity-based ordering"""
        TableRegistry.register_table(self.terms_config)  # 1 column
        TableRegistry.register_table(self.students_config)  # 1 column

        # Add more complex config
        complex_config = TableConfig(
            table_name="complex",
            source_file_pattern="complex.csv",
            column_mappings=[
                ColumnMapping(f"Col{i}", f"col_{i}", "nvarchar(50)", True)
                for i in range(10)  # 10 columns
            ],
        )
        TableRegistry.register_table(complex_config)

        # Get by complexity
        by_complexity = TableRegistry.get_tables_by_complexity()

        # Simpler tables should come first
        complex_idx = by_complexity.index("complex")
        terms_idx = by_complexity.index("terms")

        self.assertLess(terms_idx, complex_idx)

    def test_registry_error_handling(self):
        """Test registry error handling"""
        # Try to get non-existent table
        with self.assertRaises(ValueError):
            TableRegistry.get_config("nonexistent")

        # Clear and verify
        TableRegistry.clear_registry()
        self.assertEqual(len(TableRegistry.list_all_tables()), 0)

    def tearDown(self):
        """Clean up after tests"""
        TableRegistry.clear_registry()


class TestConfigurationIntegration(TestCase):
    """Integration tests for configuration system"""

    def test_terms_configuration_complete(self):
        """Test that terms configuration is complete and valid"""
        # This will test the actual terms configuration
        from data_pipeline.configs.terms import TERMS_CONFIG

        # Validate configuration
        errors = TERMS_CONFIG.validate()
        self.assertEqual(len(errors), 0, f"Terms config has errors: {errors}")

        # Check required fields
        self.assertEqual(TERMS_CONFIG.table_name, "terms")
        self.assertGreater(len(TERMS_CONFIG.column_mappings), 0)
        self.assertEqual(TERMS_CONFIG.dependencies, [])

        # Check validator is present
        self.assertIsNotNone(TERMS_CONFIG.validator_class)
        self.assertEqual(TERMS_CONFIG.validator_class, TermValidator)

    def test_all_configurations_valid(self):
        """Test that all registered configurations are valid"""
        # Initialize registry (will load all configs)
        TableRegistry._ensure_initialized()

        # Validate all configurations
        all_errors = TableRegistry.validate_all_configs()

        if all_errors:
            error_details = []
            for table, errors in all_errors.items():
                error_details.append(f"{table}: {errors}")

            self.fail("Configuration errors found:\n" + "\n".join(error_details))

    def test_configuration_sql_generation(self):
        """Test SQL generation for all configurations"""
        from data_pipeline.configs.terms import TERMS_CONFIG

        # Test raw table generation
        raw_sql = TERMS_CONFIG.generate_raw_table_sql()
        self.assertIn("CREATE TABLE raw_terms", raw_sql)
        self.assertIn("term_id TEXT", raw_sql)

        # Test cleaned table generation
        cleaned_sql = TERMS_CONFIG.generate_cleaned_table_sql()
        self.assertIn("CREATE TABLE cleaned_terms", cleaned_sql)
        self.assertIn("term_id nvarchar(200) NOT NULL", cleaned_sql)

        # Test validated table generation
        validated_sql = TERMS_CONFIG.generate_validated_table_sql()
        self.assertIn("CREATE TABLE validated_terms", validated_sql)


if __name__ == "__main__":
    pytest.main([__file__])
