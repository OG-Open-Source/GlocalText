"""A reporter for generating dry-run execution summaries."""

import logging
from collections import defaultdict

from glocaltext import paths
from glocaltext.match_state import MatchLifecycle
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
        report_path = None
        try:
            report_dir = paths.get_report_dir(context.project_root)
            paths.ensure_dir_exists(report_dir)
            report_path = report_dir / f"{context.task.name}_dry_run.md"
            logger.info("Generating dry-run report at: %s", report_path)

            report_content = self._build_report_content(context)

            with report_path.open("w", encoding="utf-8") as f:
                f.write(report_content)
            logger.info("Successfully wrote dry-run report to %s", report_path)
        except FileNotFoundError:
            logger.exception("Could not generate dry-run report because the project root could not be determined.")
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
        """
        Build the text lifecycle tracking section.

        Phase 3: Uses the new state model (lifecycle and skip_reason)
        with backward compatibility for legacy provider strings.
        """
        # Replace rules modify processed_text, not original_text.
        # We identify replaced matches by checking if processed_text differs from original_text.
        replaced_matches = [m for m in context.all_matches if m.processed_text and m.processed_text != m.original_text]

        # Use lifecycle state to identify skipped matches
        skipped_matches = [m for m in context.terminated_matches if m.lifecycle == MatchLifecycle.SKIPPED]

        # Filter out SKIPPED matches from matches_to_translate for accurate reporting
        # (e.g., same language matches are marked SKIPPED but remain in matches_to_translate)
        actual_matches_to_translate = [m for m in context.matches_to_translate if m.lifecycle != MatchLifecycle.SKIPPED]

        # Collect skipped matches that are in matches_to_translate (e.g., same language)
        skipped_in_translation_list = [m for m in context.matches_to_translate if m.lifecycle == MatchLifecycle.SKIPPED]
        all_skipped_matches = skipped_matches + skipped_in_translation_list

        return (
            "## 🔄 Text Lifecycle Tracking\n\n"
            + self._format_match_section("Replaced by Rule", replaced_matches)
            + self._format_match_section("Skipped by Rule", all_skipped_matches)
            + self._format_match_section("Found in Cache", context.cached_matches)
            + self._format_match_section("Would be Translated", actual_matches_to_translate)
        )

    def _format_match_section(self, title: str, matches: list[TextMatch]) -> str:
        """Format a single section of the lifecycle tracking."""
        if not matches:
            return f"### {title} (0 items)\n\nNo matches in this category.\n\n"

        header = f"### {title} ({len(matches)} items)\n\n"
        matches_by_file = defaultdict(list)
        for match in matches:
            matches_by_file[match.source_file].append(match)

        content = ""
        for file, file_matches in matches_by_file.items():
            content += f"**File:** `{file}`\n\n"
            content += "| Original Text | Details |\n"
            content += "|---|---|\n"
            for match in file_matches:
                content += self._format_match_row(match)
            content += "\n"
        return header + content

    def _format_match_row(self, match: TextMatch) -> str:
        """Format a single match as a table row."""
        details = self._build_match_details(match)
        text_display = self._build_text_display(match)
        return f"| {text_display} | {details} |\n"

    def _build_match_details(self, match: TextMatch) -> str:
        """Build the details column for a match."""
        details = f"Lifecycle: `{match.lifecycle.value}`"
        if match.skip_reason:
            details += f"<br>Skip Reason: `{match.skip_reason.code}`"
        if match.translated_text:
            details += f"<br>Translation: `{match.translated_text}`"
        return details

    def _build_text_display(self, match: TextMatch) -> str:
        """Build the text display column for a match."""
        if match.processed_text and match.processed_text != match.original_text:
            return f"`{self._escape_markdown(match.original_text)}` → `{self._escape_markdown(match.processed_text)}`"
        display_text = match.processed_text if match.processed_text else match.original_text
        return f"`{self._escape_markdown(display_text)}`"

    def _build_batch_plan(self, context: ExecutionContext) -> str:
        """Build the simulated batch processing plan section."""
        # Filter out SKIPPED matches (e.g., same language) for accurate count
        actual_matches_to_translate = [m for m in context.matches_to_translate if m.lifecycle != MatchLifecycle.SKIPPED]
        to_translate_count = len(actual_matches_to_translate)

        if to_translate_count == 0:
            return "## 🚀 Batch Processing Plan (Simulated)\n\nNo new translations required.\n"

        # Use processed_text (after replace rules) if available, otherwise use original_text
        # This ensures the batch plan shows the actual text that will be sent to the translator
        unique_texts = {(m.processed_text if m.processed_text else m.original_text) for m in actual_matches_to_translate}
        unique_count = len(unique_texts)

        return (
            "## 🚀 Batch Processing Plan (Simulated)\n\n"
            f"A total of **{to_translate_count}** text occurrences corresponding to **{unique_count}** unique strings would be sent to the `{context.task.translator}` translator.\n\n"
            "**Unique strings to be translated:**\n" + "\n".join(f"- `{self._escape_markdown(text)}`" for text in sorted(unique_texts)) + "\n"
        )

    def _escape_markdown(self, text: str) -> str:
        """Escapes characters that have special meaning in Markdown."""
        return text.replace("|", "\\|").replace("\n", " ")
