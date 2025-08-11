import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from glocaltext.core.config import I18nConfig, I18nSource, ExtractionRule
from glocaltext.core.i18n import I18nProcessor
from glocaltext.utils.debug_logger import DebugLogger


class TestI18nProcessor(unittest.TestCase):

    def setUp(self):
        self.project_path = Path("/fake/project")
        # Create a dummy file in memory for the processor to read
        self.mock_file_content = """
        _("Translate this")
        _("$end_time - $start_time")
        _("Also translate this")
        """
        self.mock_file_path = self.project_path / "app.py"
        self.mock_debug_logger = MagicMock(spec=DebugLogger)

    def test_ignore_rules_correctly_filters_strings(self):
        """
        Verify that strings matching an ignore_rule are not extracted.
        """
        # Arrange
        config = I18nConfig(
            source=I18nSource(include=["**/*.py"], exclude=[]),
            capture_rules=[ExtractionRule(pattern=r'_\(["\'](.*?)["\']\)')],
            ignore_rules=[
                # This rule should exactly match and ignore the variable-like string
                ExtractionRule(pattern=r"\$end_time - \$start_time")
            ],
        )

        processor = I18nProcessor(config, self.project_path, self.mock_debug_logger)

        # Mock the file system operations
        with (
            patch("pathlib.Path.rglob", return_value=[self.mock_file_path]),
            patch.object(Path, "read_text", return_value=self.mock_file_content),
        ):

            # Act
            extracted_strings = processor.run()

        # Assert
        self.assertEqual(len(extracted_strings), 2)
        self.assertIn("Translate this", [s.text for s in extracted_strings.values()])
        self.assertIn(
            "Also translate this", [s.text for s in extracted_strings.values()]
        )
        self.assertNotIn(
            "$end_time - $start_time", [s.text for s in extracted_strings.values()]
        )


if __name__ == "__main__":
    unittest.main()
