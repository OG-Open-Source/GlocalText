"""Tests for the match_state module."""

import dataclasses
import unittest

import pytest

from glocaltext.match_state import (
    SKIP_DRY_RUN,
    SKIP_EMPTY,
    SKIP_SAME_LANGUAGE,
    SKIP_USER_RULE,
    MatchLifecycle,
    SkipReason,
)


class TestMatchLifecycle(unittest.TestCase):
    """Test suite for MatchLifecycle enum."""

    def test_enum_values_are_strings(self) -> None:
        """1. MatchLifecycle enum values are strings for serialization compatibility."""
        assert MatchLifecycle.CAPTURED == "captured"
        assert MatchLifecycle.TRANSLATED == "translated"
        assert MatchLifecycle.SKIPPED == "skipped"

    def test_all_states_are_unique(self) -> None:
        """2. All MatchLifecycle states have unique string values."""
        values = [state.value for state in MatchLifecycle]
        assert len(values) == len(set(values)), "Duplicate lifecycle state values found"

    def test_enum_is_comparable(self) -> None:
        """3. MatchLifecycle states can be compared for equality."""
        state1 = MatchLifecycle.CAPTURED
        state2 = MatchLifecycle.CAPTURED
        state3 = MatchLifecycle.TRANSLATED
        assert state1 == state2
        assert state1 != state3


class TestSkipReason(unittest.TestCase):
    """Test suite for SkipReason dataclass."""

    def test_skip_reason_is_immutable(self) -> None:
        """1. SkipReason is immutable (frozen dataclass)."""
        reason = SkipReason(category="validation", code="test")
        with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):  # type: ignore[attr-defined]
            reason.code = "modified"  # type: ignore[misc]

    def test_skip_reason_str_representation(self) -> None:
        """2. SkipReason has a readable string representation."""
        reason_with_message = SkipReason(
            category="validation",
            code="empty",
            message="Empty text",
        )
        reason_without_message = SkipReason(category="rule", code="user")

        assert str(reason_with_message) == "validation:empty (Empty text)"
        assert str(reason_without_message) == "rule:user"

    def test_predefined_reasons_exist(self) -> None:
        """3. Predefined SkipReason constants are properly defined."""
        assert SKIP_EMPTY.category == "validation"
        assert SKIP_EMPTY.code == "empty"

        assert SKIP_SAME_LANGUAGE.category == "optimization"
        assert SKIP_SAME_LANGUAGE.code == "same_lang"

        assert SKIP_USER_RULE.category == "rule"
        assert SKIP_USER_RULE.code == "user_skip"

        assert SKIP_DRY_RUN.category == "mode"
        assert SKIP_DRY_RUN.code == "dry_run"

    def test_skip_reasons_are_comparable(self) -> None:
        """4. SkipReasons can be compared for equality."""
        reason1 = SkipReason(category="validation", code="empty")
        reason2 = SkipReason(category="validation", code="empty")
        reason3 = SkipReason(category="rule", code="user")

        assert reason1 == reason2
        assert reason1 != reason3


class TestStateModelIntegration(unittest.TestCase):
    """Integration tests for the complete state model."""

    def test_state_model_documentation(self) -> None:
        """1. Integration: All enum values and constants have docstrings."""
        # Verify that key components are well-documented
        assert MatchLifecycle.__doc__ is not None
        assert SkipReason.__doc__ is not None
        assert SKIP_EMPTY.__doc__ is not None


if __name__ == "__main__":
    unittest.main()
