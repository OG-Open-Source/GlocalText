import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Data Models for Structured Logging ---


class LogAction(BaseModel):
    """Represents a single logged action within a processing unit."""

    action_type: str = Field(
        ..., description="Type of action, e.g., 'Extract', 'Ignore', 'Protect'."
    )
    details: str = Field(..., description="Details of the action.")
    status: str = Field(
        "INFO",
        description="Status of the action, e.g., 'INFO', 'WARN', 'SUCCESS', 'FAIL'.",
    )


class StringProcessingUnit(BaseModel):
    """Represents the entire lifecycle of a single extracted string."""

    source_text: str
    location: str
    hash_id: str
    final_status: str = "PENDING"
    actions: List[LogAction] = Field(default_factory=list)
    translation_details: Dict[str, Any] = Field(default_factory=dict)
    compilation_details: Dict[str, Any] = Field(default_factory=dict)


class FileProcessingUnit(BaseModel):
    """Represents all strings processed within a single file."""

    file_path: str
    strings: List[StringProcessingUnit] = Field(default_factory=list)


class LogPhase(BaseModel):
    """Represents a major phase of the execution, e.g., 'SCANNING', 'TRANSLATION'."""

    name: str
    summary: List[str] = Field(default_factory=list)
    content: List[Any] = Field(default_factory=list)  # Can hold strings or other units


class DebugReport(BaseModel):
    """The root model for the entire debug log."""

    run_started: datetime
    run_finished: Optional[datetime] = None
    project_path: str
    phases: Dict[str, LogPhase] = Field(default_factory=dict)


# --- The New DebugLogger ---


class DebugLogger:
    """
    A logger that captures structured data about the run and renders it
    into a human-readable format at the end of the process.
    It no longer handles file I/O directly.
    """

    def __init__(self, project_path: Path, enabled: bool = False):
        self.enabled = enabled
        if not self.enabled:
            return

        self.report = DebugReport(
            run_started=datetime.now(), project_path=str(project_path)
        )
        self._current_phase: Optional[LogPhase] = None
        self._current_file_unit: Optional[FileProcessingUnit] = None
        self._string_map: Dict[str, StringProcessingUnit] = {}  # hash_id -> unit
        logger.debug("Structured debug logger enabled.")

    def start_phase(self, name: str):
        if not self.enabled:
            return
        phase = LogPhase(name=name)
        self.report.phases[name] = phase
        self._current_phase = phase

    def add_phase_summary(self, summary_line: str):
        if not self.enabled or not self._current_phase:
            return
        self._current_phase.summary.append(summary_line)

    def start_file_unit(self, file_path: Path):
        if not self.enabled:
            return
        relative_path = str(file_path.relative_to(Path(self.report.project_path)))
        self._current_file_unit = FileProcessingUnit(file_path=relative_path)

    def end_file_unit(self):
        if not self.enabled or not self._current_file_unit:
            return
        if self._current_phase:
            self._current_phase.content.append(self._current_file_unit)
        self._current_file_unit = None

    def log_string_action(
        self,
        hash_id: str,
        action_type: str,
        details: str,
        source_info: Optional[Dict] = None,
    ):
        if not self.enabled:
            return

        unit = self._string_map.get(hash_id)
        if not unit and source_info:
            unit = StringProcessingUnit(
                source_text=source_info["source_text"],
                location=source_info["location"],
                hash_id=hash_id,
            )
            self._string_map[hash_id] = unit
            if self._current_file_unit:
                self._current_file_unit.strings.append(unit)

        if unit:
            unit.actions.append(LogAction(action_type=action_type, details=details))

    def set_string_status(self, hash_id: str, status: str):
        if not self.enabled:
            return
        unit = self._string_map.get(hash_id)
        if unit:
            unit.final_status = status

    def log_translation_details(
        self, hash_id: str, lang: str, translated_template: str, final_text: str
    ):
        if not self.enabled:
            return
        unit = self._string_map.get(hash_id)
        if unit:
            unit.translation_details[lang] = {
                "translated_template": translated_template,
                "final_text": final_text,
            }

    def log_compilation_details(
        self, lang: str, file_path: str, original: str, replacement: str
    ):
        if not self.enabled:
            return
        phase_name = "COMPILATION"
        if phase_name not in self.report.phases:
            self.start_phase(phase_name)

        # This is a simplified way to log compilation. A more robust implementation
        # might link this back to the original string hash.
        self.report.phases[phase_name].content.append(
            f"[{lang}] in '{file_path}':\n  - Replaced: '{original}'\n  - With:     '{replacement}'"
        )

    def finalize(self) -> Optional[str]:
        """
        Finalizes the report, renders it, and returns it as a string.
        Returns None if not enabled.
        """
        if not self.enabled:
            return None
        self.report.run_finished = datetime.now()
        logger.debug("Finalizing structured debug report.")
        return self._render_report()

    def _render_report(self) -> str:
        """Renders the structured report into a string."""
        output = []

        # Header
        output.append("GlocalText Debug Log")
        output.append("=" * 40)
        output.append(f"Run Started: {self.report.run_started.isoformat()}")
        output.append(f"Project Path: {self.report.project_path}")
        output.append("=" * 40 + "\n")

        # Phases
        for phase_name, phase in self.report.phases.items():
            output.append(f"\n[PHASE: {phase.name}]")
            output.append("-" * 40)
            for summary_line in phase.summary:
                output.append(f"- {summary_line}")

            if phase.name == "EXTRACTION":
                for file_unit in self.report.phases.get(
                    "EXTRACTION", LogPhase(name="")
                ).content:
                    if isinstance(file_unit, FileProcessingUnit):
                        output.append(f"\n  Processing File: {file_unit.file_path}")
                        output.append(f"  {'-'*30}")
                        for i, string_unit in enumerate(file_unit.strings):
                            output.append(
                                f"\n    [STRING {i+1}/{len(file_unit.strings)}]"
                            )
                            output.append(f"    - Location:  {string_unit.location}")
                            output.append(
                                f"    - Source:    '{string_unit.source_text}'"
                            )
                            output.append(f"    - Hash:      {string_unit.hash_id}")
                            output.append(
                                f"    - Status:    {string_unit.final_status}"
                            )
                            output.append("    - Actions:")
                            for action in string_unit.actions:
                                output.append(
                                    f"      - ({action.action_type}) {action.details}"
                                )

            elif phase.name == "TRANSLATION":
                for hash_id, string_unit in self._string_map.items():
                    if not string_unit.translation_details:
                        continue
                    output.append(f"\n  [TRANSLATION for {hash_id}]")
                    output.append(f"  - Source Text: '{string_unit.source_text}'")
                    for lang, details in string_unit.translation_details.items():
                        output.append(f"    - Lang: {lang}")
                        output.append(f"      - Translated: '{details['final_text']}'")

            elif phase.name == "COMPILATION":
                for item in phase.content:
                    output.append(f"  {item}")

        # Footer
        duration = (
            self.report.run_finished - self.report.run_started
            if self.report.run_finished
            else "N/A"
        )
        output.append("\n" + "=" * 40)
        output.append(
            f"Run Finished: {self.report.run_finished.isoformat() if self.report.run_finished else 'N/A'}"
        )
        output.append(f"Total Duration: {duration}")
        output.append("=" * 40)

        return "\n".join(output)
