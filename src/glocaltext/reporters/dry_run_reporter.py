"""A reporter for generating dry-run execution summaries."""

import logging
from collections import defaultdict
from pathlib import Path

from glocaltext.models import ExecutionContext, TextMatch

logger = logging.getLogger(__name__)


class DryRunReporter:
    """Generates a detailed Markdown report for a dry-run execution."""

    def generate(self, context: ExecutionContext) -> None:
        """
        Create a Markdown file with a summary of the dry run.

        Args:
            context: The execution context containing all run information.

        """
        report_path = Path.cwd() / f"{context.task.name}_dry_run_report.md"
        logger.info("Generating dry-run report at: %s", report_path)

        report_content = self._build_report_content(context)

        try:
            with report_path.open("w", encoding="utf-8") as f:
                f.write(report_content)
            logger.info("Successfully wrote dry-run report to %s", report_path)
        except OSError:
            logger.exception("Failed to write dry-run report to %s", report_path)

    def _build_report_content(self, context: ExecutionContext) -> str:
        """Construct the full Markdown content for the report."""
        parts = [
            self._build_header(context),
            self._build_file_summary(context),
            self._build_lifecycle_tracking(context),
            self._build_batch_plan(context),
        ]
        return "\n".join(parts)

    def _build_header(self, context: ExecutionContext) -> str:
        """Build the main header and overview section of the report."""
        return (
            f"# Dry Run Report for Task: `{context.task.name}`\n\n"
            "This report simulates the execution of the task without making any actual API calls or file modifications.\n\n"
            "## 📝 Task Overview\n\n"
            f"- **Source Language:** `{context.task.source_lang}`\n"
            f"- **Target Language:** `{context.task.target_lang}`\n"
            f"- **Translator:** `{context.task.translator}`\n"
            f"- **Incremental Mode:** `{'Yes' if context.is_incremental else 'No'}`\n"
            f"- **Files to Process:** {len(context.files_to_process)}\n"
            f"- **Total Matches Found:** {len(context.all_matches)}\n"
        )

    def _build_file_summary(self, context: ExecutionContext) -> str:
        """Build the file details section."""
        if not context.files_to_process:
            return "## 📂 File Details\n\nNo files found to process.\n"

        file_list_items = "\n".join(f"- `{file}`" for file in context.files_to_process)
        return f"## 📂 File Details\n\n**Files Scanned:**\n{file_list_items}\n"

    def _build_lifecycle_tracking(self, context: ExecutionContext) -> str:
        """Build the text lifecycle tracking section."""
        return (
            "## 🔄 Text Lifecycle Tracking\n\n"
            + self._format_match_section("Replaced by Rule", [m for m in context.terminated_matches if m.provider == "rule"])
            + self._format_match_section("Skipped by Rule", [m for m in context.terminated_matches if m.provider == "skipped"])
            + self._format_match_section("Found in Cache", context.cached_matches)
            + self._format_match_section("Would be Translated", context.matches_to_translate)
        )

    def _format_match_section(self, title: str, matches: list[TextMatch]) -> str:
        """Format a single section of the lifecycle tracking."""
        if not matches:
            return f"### {title} (0 items)\n\nNo matches in this category.\n\n"

        header = f"### {title} ({len(matches)} items)\n\n"
        # Group by file for better readability
        matches_by_file = defaultdict(list)
        for match in matches:
            matches_by_file[match.source_file].append(match)

        content = ""
        for file, file_matches in matches_by_file.items():
            content += f"**File:** `{file}`\n\n"
            content += "| Original Text | Details |\n"
            content += "|---|---|\n"
            for match in file_matches:
                details = f"Provider: `{match.provider}`"
                if match.translated_text:
                    details += f"<br>Translation: `{match.translated_text}`"
                content += f"| `{self._escape_markdown(match.original_text)}` | {details} |\n"
            content += "\n"
        return header + content

    def _build_batch_plan(self, context: ExecutionContext) -> str:
        """Build the simulated batch processing plan section."""
        to_translate_count = len(context.matches_to_translate)
        if to_translate_count == 0:
            return "## 🚀 Batch Processing Plan (Simulated)\n\nNo new translations required.\n"

        unique_texts = {m.original_text for m in context.matches_to_translate}
        unique_count = len(unique_texts)

        return (
            "## 🚀 Batch Processing Plan (Simulated)\n\n"
            f"A total of **{to_translate_count}** text occurrences corresponding to **{unique_count}** unique strings would be sent to the `{context.task.translator}` translator.\n\n"
            "**Unique strings to be translated:**\n" + "\n".join(f"- `{self._escape_markdown(text)}`" for text in sorted(unique_texts)) + "\n"
        )

    def _escape_markdown(self, text: str) -> str:
        """Escapes characters that have special meaning in Markdown."""
        return text.replace("|", "\\|").replace("\n", " ")
