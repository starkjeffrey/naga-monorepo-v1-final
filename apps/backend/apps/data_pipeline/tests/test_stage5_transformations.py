# data_pipeline/tests/test_stage5_transformations.py
import unittest

import pandas as pd

from data_pipeline.core.transformations.text_encodings import KhmerTextTransformer

from ..configs.base import PipelineLogger
from ..core.stages import Stage5Transform
from ..core.transformations.base import TransformationContext


class TestKhmerTransformations(unittest.TestCase):
    """
    Test suite for Khmer text transformations.
    These tests ensure your Limon to Unicode conversion works correctly.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.transformer = KhmerTextTransformer()
        self.context = TransformationContext(
            source_table="test_table",
            source_column="test_column",
            target_column="test_target",
            row_number=1,
        )

    def test_limon_to_unicode_conversion(self):
        """Test that Limon text is correctly converted to Unicode."""
        # You'll need to provide actual Limon text examples
        limon_text = "example_limon_text"  # Replace with actual Limon
        expected_unicode = "អក្សរខ្មែរ"  # Replace with expected Unicode

        result = self.transformer.transform(limon_text, self.context)
        self.assertEqual(result, expected_unicode)

    def test_already_unicode_not_transformed(self):
        """Test that already-Unicode text is not transformed."""
        unicode_text = "អក្សរខ្មែរ"

        can_transform = self.transformer.can_transform(unicode_text)
        self.assertFalse(can_transform)

    def test_empty_string_handling(self):
        """Test that empty strings are handled gracefully."""
        result = self.transformer.transform("", self.context)
        self.assertEqual(result, "")

    def test_null_handling(self):
        """Test that None values are handled gracefully."""
        result = self.transformer.transform_with_fallback(None, self.context)
        self.assertIsNone(result)


class TestStage5Integration(unittest.TestCase):
    """
    Integration tests for the complete Stage 5 pipeline.
    These tests ensure Stage 5 works correctly with your data.
    """

    def test_stage5_with_sample_data(self):
        """Test Stage 5 with a sample dataset."""
        # Create sample data
        sample_data = pd.DataFrame(
            {
                "student_id": ["001", "002"],
                "name": ["John Doe", "Jane Smith"],
                "kname": ["limon_name_1", "limon_name_2"],  # Replace with actual Limon
                "phone": ["012345678", "098765432"],
            }
        )

        # Create config with transformation rules
        from ..configs.base import TableConfig, TransformationRule

        config = TableConfig(
            table_name="test_students",
            source_file_pattern="test_students.csv",
            transformed_table_name="transformed_test_students",
            transformation_rules=[
                TransformationRule(
                    source_column="kname",
                    target_column="kname_unicode",
                    transformer="khmer.limon_to_unicode",
                    preserve_original=True,
                )
            ],
        )

        # Create logger
        logger = PipelineLogger(config.table_name)

        # Run Stage 5
        stage5 = Stage5Transform(config, logger, run_id=1)
        result = stage5.execute(sample_data)

        # Verify results
        self.assertTrue(result["success"])
        self.assertEqual(result["records_transformed"], 2)
        self.assertEqual(result["transformations_applied"], 1)
