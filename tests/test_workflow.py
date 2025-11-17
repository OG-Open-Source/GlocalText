"""End-to-end tests for the main workflow."""

import unittest
from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock, patch

from pyfakefs.fake_filesystem_unittest import TestCase  # type: ignore[import-not-found]

from glocaltext import _get_version
from glocaltext.config import GlocalConfig, ProviderSettings
from glocaltext.types import Output, Source, TranslationTask
from glocaltext.workflow import run_task


class TestWorkflow(TestCase):
    """
    Integration test suite for the main translation workflow.

    This uses pyfakefs to simulate a real filesystem.
    """

    def setUp(self) -> None:
        """Set up the fake filesystem and create mock files."""
        self.setUpPyfakefs()
        self.fs.create_file("/project/docs/file1.md", contents="Translate this: `Hello`\nDo not translate this: `internal_code`")
        self.fs.create_file("/project/docs/internal/file2.md", contents="`Secret`")
        self.fs.create_file("/project/other/script.sh", contents='echo "World"')

    @patch("glocaltext.workflow.SummaryReporter.generate")
    def test_end_to_end_workflow_run(self, mock_reporter_generate: MagicMock) -> None:
        """1. E2E: A full workflow run with file discovery, translation, and write-back."""
        mock_config = GlocalConfig(
            providers={"mock": ProviderSettings()},
        )
        mock_task = TranslationTask(
            name="test_markdown_translation",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(
                include=["docs/**/*.md"],
                exclude=["**/internal/**"],
            ),
            extraction_rules=[r"`([^`\n]+)`"],
            output=Output(in_place=False, path="/project/output/fr"),
        )
        run_task(mock_task, mock_config, dry_run=False, debug=False)
        mock_reporter_generate.assert_called_once()

    @patch("importlib.metadata.version")
    def test_version_import_success(self, mock_version: MagicMock) -> None:
        """2. Version: Ensures __version__ is loaded from metadata when package is installed."""
        mock_version.return_value = "1.2.3"
        version = _get_version()
        assert version == "1.2.3"
        mock_version.assert_called_once_with("GlocalText")

    @patch("importlib.metadata.version")
    def test_version_import_fails_gracefully(self, mock_version: MagicMock) -> None:
        """3. Version: Handles PackageNotFoundError gracefully by setting version to 'unknown'."""
        mock_version.side_effect = PackageNotFoundError
        version = _get_version()
        assert version == "0.0.0-dev"


if __name__ == "__main__":
    unittest.main()
