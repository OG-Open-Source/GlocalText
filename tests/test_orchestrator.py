import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from glocaltext.orchestrator import Orchestrator
from glocaltext.core.i18n import ExtractedString


class TestOrchestrator(unittest.TestCase):

    def setUp(self):
        """Set up mock components for each test."""
        self.mock_project_path = Path("/fake/project")
        self.mock_i18n_processor = MagicMock()
        self.mock_l10n_processor = MagicMock()
        self.mock_compiler = MagicMock()
        self.mock_sync_processor = MagicMock()
        self.mock_cache = MagicMock()

        self.orchestrator = Orchestrator(
            project_path=self.mock_project_path,
            i18n_processor=self.mock_i18n_processor,
            l10n_processor=self.mock_l10n_processor,
            compiler=self.mock_compiler,
            sync_processor=self.mock_sync_processor,
            cache=self.mock_cache,
            debug=False,  # Disable debug logging for most tests
        )

    def test_run_localization_no_new_strings(self):
        """Test the localization run when no new strings are found."""
        # Arrange
        self.mock_i18n_processor.extracted_strings = {
            "hash1": ExtractedString(
                hash_id="hash1",
                text="Hello",
                text_to_translate="Hello",
                full_match="_('Hello')",
                source_file=Path("a.py"),
                line_number=1,
            )
        }
        self.mock_cache.get_all_cached_hashes.return_value = {"hash1"}

        # Act
        self.orchestrator.run_localization(force=False)

        # Assert
        self.mock_i18n_processor.run.assert_called_once()
        self.mock_l10n_processor.process_and_translate.assert_not_called()
        self.mock_compiler.run.assert_called_once_with(self.mock_project_path)
        self.mock_cache.save.assert_called_once()

    def test_run_localization_with_new_strings(self):
        """Test the localization run when new strings are detected."""
        # Arrange
        new_string = ExtractedString(
            hash_id="hash2",
            text="World",
            text_to_translate="World",
            full_match="_('World')",
            source_file=Path("b.py"),
            line_number=2,
        )
        self.mock_i18n_processor.extracted_strings = {"hash2": new_string}
        self.mock_cache.get_all_cached_hashes.return_value = set()

        # Act
        self.orchestrator.run_localization(force=False)

        # Assert
        self.mock_i18n_processor.run.assert_called_once()
        self.mock_l10n_processor.process_and_translate.assert_called_once_with(
            {"hash2": new_string}, force=False
        )
        self.mock_compiler.run.assert_called_once_with(self.mock_project_path)
        self.mock_cache.save.assert_called_once()

    def test_run_localization_with_force(self):
        """Test the localization run with the --force flag."""
        # Arrange
        all_strings = {
            "hash1": ExtractedString(
                hash_id="hash1",
                text="Hello",
                text_to_translate="Hello",
                full_match="_('Hello')",
                source_file=Path("a.py"),
                line_number=1,
            )
        }
        self.mock_i18n_processor.extracted_strings = all_strings
        self.mock_cache.get_all_cached_hashes.return_value = {"hash1"}

        # Act
        self.orchestrator.run_localization(force=True)

        # Assert
        self.mock_l10n_processor.process_and_translate.assert_called_once_with(
            all_strings, force=True
        )

    def test_run_sync(self):
        """Test the sync workflow."""
        # Act
        self.orchestrator.run_sync()

        # Assert
        self.mock_sync_processor.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
