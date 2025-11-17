"""
Match lifecycle state management for GlocalText.

This module introduces a clear, type-safe state model for TextMatch objects,
replacing the previous overloaded `provider` field with explicit state tracking.

Design Goals:
- Single Responsibility: Each field represents ONE concept
- Type Safety: Use enums and dataclasses for compile-time checking
- Extensibility: Adding new states/reasons doesn't require code changes elsewhere
- Backward Compatibility: Can coexist with legacy `provider` field during migration

Architecture:
    MatchLifecycle (Enum) → Represents WHERE the match is in the pipeline
    SkipReason (Dataclass) → Represents WHY a match was skipped (if applicable)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class MatchLifecycle(str, Enum):
    """
    Represents the lifecycle state of a TextMatch in the translation pipeline.

    Each match progresses through these states in a defined order, making the
    data flow explicit and testable. The string values are human-readable for
    logging and debugging.

    State Transition Flow:
        CAPTURED → [REPLACED/SKIPPED] → VALIDATED → [CACHED/PENDING_TRANSLATION]
        → TRANSLATED → [DRY_RUN_SIMULATED]

    """

    # Initial capture state
    CAPTURED = "captured"
    """Match was extracted by an extraction rule but not yet processed."""

    # Early termination states
    REPLACED = "replaced"
    """Match was modified by a replace rule (processed_text != original_text)."""

    SKIPPED = "skipped"
    """Match was terminated by a skip rule or system optimization."""

    # Validation state
    VALIDATED = "validated"
    """Match passed validation checks (non-empty, etc.) and is ready for translation."""

    # Translation source states
    CACHED = "cached"
    """Translation was found in the cache and reused."""

    PENDING_TRANSLATION = "pending_translation"
    """Match is waiting to be sent to the translation API."""

    # Completion states
    TRANSLATED = "translated"
    """Match was successfully translated via API call."""

    DRY_RUN_SIMULATED = "dry_run_simulated"
    """Match was processed in dry-run mode (no actual API call made)."""


@dataclass(frozen=True)
class SkipReason:
    """
    Represents why a TextMatch was skipped, using a structured approach.

    Using a value object (immutable dataclass) makes skip reasons:
    - Type-safe (caught at compile time)
    - Self-documenting (category + code + message)
    - Extensible (add new reasons without modifying existing code)

    Attributes:
        category: The high-level category of the skip reason.
        code: A machine-readable identifier for the specific reason.
        message: A human-readable explanation (optional, for logging/debugging).

    """

    category: Literal["validation", "optimization", "rule", "mode"]
    """
    The category of the skip reason:
    - validation: Failed validation checks (e.g., empty text)
    - optimization: Skipped for performance/efficiency (e.g., same language)
    - rule: Skipped by user-defined rule
    - mode: Skipped due to execution mode (e.g., dry-run)
    """

    code: str
    """Machine-readable identifier (e.g., 'empty', 'same_lang', 'user_skip')."""

    message: str | None = None
    """Human-readable explanation for logging/debugging."""

    def __str__(self) -> str:
        """Return a human-readable representation of the skip reason."""
        if self.message:
            return f"{self.category}:{self.code} ({self.message})"
        return f"{self.category}:{self.code}"


# Predefined skip reasons for common cases
# These act as "constants" for frequently used skip reasons, ensuring consistency
# and avoiding magic strings throughout the codebase.

SKIP_EMPTY = SkipReason(
    category="validation",
    code="empty",
    message="Empty or whitespace-only text",
)
"""Skip reason for empty or whitespace-only text matches."""

SKIP_SAME_LANGUAGE = SkipReason(
    category="optimization",
    code="same_lang",
    message="Source and target languages are identical",
)
"""Skip reason when source and target languages are the same."""

SKIP_USER_RULE = SkipReason(
    category="rule",
    code="user_skip",
    message="Skipped by user-defined skip rule",
)
"""Skip reason for matches terminated by user-defined skip rules."""

SKIP_DRY_RUN = SkipReason(
    category="mode",
    code="dry_run",
    message="Skipped due to dry-run execution mode",
)
"""Skip reason for matches in dry-run mode (no actual translation performed)."""
