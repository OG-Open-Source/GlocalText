"""Defines shared data structures and types for GlocalText."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from glocaltext.match_state import MatchLifecycle, SkipReason

if TYPE_CHECKING:
    from glocaltext.text_coverage import TextCoverage


@dataclass
class Output:
    """Defines the output behavior for a translation task."""

    in_place: bool = True
    path: str | None = None
    filename: str | None = None

    def __post_init__(self) -> None:
        """Validate attributes."""
        if self.in_place and self.path is not None:
            msg = "The 'path' attribute cannot be used when 'in_place' is True."
            raise ValueError(msg)
        if not self.in_place and self.path is None:
            msg = "The 'path' attribute is required when 'in_place' is False."
            raise ValueError(msg)


@dataclass
class MatchRule:
    """Defines the matching criteria for a rule, which is always a regex pattern."""

    regex: str


@dataclass
class ActionRule:
    """Defines the action to be taken when a rule matches."""

    action: Literal["skip", "replace", "protect"]
    value: str | None = None

    def __post_init__(self) -> None:
        """Validate that 'value' is provided for actions that require it."""
        if self.action == "replace" and self.value is None:
            msg = f"The 'value' must be provided for the '{self.action}' action."
            raise ValueError(msg)


@dataclass
class Rule:
    """A single rule combining a match condition and an action."""

    match: MatchRule
    action: ActionRule


@dataclass
class Source:
    """Defines the source files for a translation task."""

    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)


@dataclass
class TextMatch:
    """
    Represents a piece of text extracted from a source file that is a candidate for translation.

    Attributes:
        original_text: The exact text captured by the extraction rule.
        source_file: The path to the file from which the text was extracted.
        span: A tuple (start, end) indicating the character position of the text in the source file.
        match_id: A unique identifier for this specific match instance.
        task_name: The name of the task this match belongs to.
        extraction_rule: The rule used to extract this match.
        translated_text: The translated text. None if not yet translated.
        provider: [DEPRECATED] Legacy field. Use 'lifecycle' and 'skip_reason' instead.
        tokens_used: The number of tokens consumed for the translation by an AI provider.
        coverage: Optional coverage tracking for this match. Used to determine
            if rules have fully covered the text, enabling translation skip optimization.
        lifecycle: The current state of this match in the translation pipeline.
        skip_reason: If lifecycle is SKIPPED, provides the structured reason why.
        processed_text: Store the text after replace rules are applied, while keeping
            original_text unchanged for cache consistency.

    """

    original_text: str
    source_file: Path
    span: tuple[int, int]
    task_name: str
    extraction_rule: str
    translated_text: str | None = None
    tokens_used: int | None = None
    match_id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False, repr=False)
    coverage: Optional["TextCoverage"] = None
    processed_text: str | None = None

    # State tracking fields
    lifecycle: MatchLifecycle = MatchLifecycle.CAPTURED
    skip_reason: SkipReason | None = None

    def __hash__(self) -> int:
        """Return the hash of the match instance."""
        # Hash based on the unique identifier of the match instance.
        return hash(self.match_id)

    def __eq__(self, other: object) -> bool:
        """Check equality against another object."""
        # Equality is based on the unique identifier.
        if not isinstance(other, TextMatch):
            return NotImplemented
        return self.match_id == other.match_id

    # Convenience properties for state queries
    @property
    def is_skipped(self) -> bool:
        """Check if this match has been skipped."""
        return self.lifecycle == MatchLifecycle.SKIPPED

    @property
    def needs_translation(self) -> bool:
        """Check if this match needs to be translated."""
        return self.lifecycle == MatchLifecycle.PENDING_TRANSLATION and not self.is_skipped

    @property
    def is_translated(self) -> bool:
        """Check if this match has been successfully translated."""
        return self.lifecycle == MatchLifecycle.TRANSLATED

    @property
    def was_cached(self) -> bool:
        """Check if this match was resolved from cache."""
        return self.lifecycle == MatchLifecycle.CACHED

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the dataclass instance to a JSON-serializable dictionary.

        Note: coverage is intentionally excluded from serialization
        as it's a runtime optimization detail, not persistent data.
        """
        result: dict[str, Any] = {
            "match_id": self.match_id,
            "original_text": self.original_text,
            "task_name": self.task_name,
            "extraction_rule": self.extraction_rule,
            "translated_text": self.translated_text,
            "source_file": str(self.source_file),
            "span": self.span,
            "tokens_used": self.tokens_used,
            "lifecycle": self.lifecycle.value,
        }

        # Include skip_reason only if present (avoid cluttering output with None)
        if self.skip_reason is not None:
            result["skip_reason"] = {
                "category": self.skip_reason.category,
                "code": self.skip_reason.code,
                "message": self.skip_reason.message,
            }

        return result


@dataclass
class PreProcessedText:
    """Represents a unique original text and its pre-processing results."""

    original_text: str
    text_to_process: str
    protected_map: dict[str, str]
    matches: list[TextMatch]


class TranslationList(BaseModel):
    """Defines the expected JSON structure for the list of translations."""

    translations: list[str] = Field(description="A list of translated strings.")


class TranslationTask(BaseModel):
    """A single task defining what to translate and how."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    source_lang: str
    target_lang: str
    source: Source
    translator: str | None = None
    model: str | None = None
    prompts: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    output: Output = Field(default_factory=Output)
    rules: list[Rule] = Field(default_factory=list)
    extraction_rules: list[str] = Field(default_factory=list)
    incremental: bool = False
    cache_path: str | None = None
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this task. Auto-generated if not provided.")
