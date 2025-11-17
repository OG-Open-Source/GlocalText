"""Tests for the coverage tracking module."""

import unittest

import pytest

from glocaltext.text_coverage import TextCoverage, calculate_total_coverage, merge_ranges


class TestMergeRanges(unittest.TestCase):
    """Test suite for the merge_ranges helper function."""

    def test_empty_ranges(self) -> None:
        """Merging an empty range list should return an empty list."""
        result = merge_ranges([])
        assert result == []

    def test_single_range(self) -> None:
        """A single range should remain unchanged."""
        result = merge_ranges([(0, 5)])
        assert result == [(0, 5)]

    def test_non_overlapping_ranges(self) -> None:
        """Non-overlapping ranges should remain separate."""
        result = merge_ranges([(0, 3), (5, 8), (10, 15)])
        assert result == [(0, 3), (5, 8), (10, 15)]

    def test_overlapping_ranges(self) -> None:
        """Overlapping ranges should be merged."""
        result = merge_ranges([(0, 5), (3, 8), (10, 15)])
        assert result == [(0, 8), (10, 15)]

    def test_adjacent_ranges(self) -> None:
        """Adjacent ranges should be merged."""
        result = merge_ranges([(0, 3), (3, 6)])
        assert result == [(0, 6)]

    def test_completely_overlapping_ranges(self) -> None:
        """Completely overlapping ranges should be merged into one."""
        result = merge_ranges([(0, 10), (2, 5), (3, 7)])
        assert result == [(0, 10)]

    def test_unsorted_ranges(self) -> None:
        """Unsorted ranges should be correctly merged."""
        result = merge_ranges([(10, 15), (0, 5), (3, 8)])
        assert result == [(0, 8), (10, 15)]

    def test_multiple_adjacent_ranges(self) -> None:
        """Multiple adjacent ranges should be merged into one."""
        result = merge_ranges([(0, 3), (3, 6), (6, 9)])
        assert result == [(0, 9)]


class TestCalculateTotalCoverage(unittest.TestCase):
    """Test suite for the calculate_total_coverage helper function."""

    def test_empty_ranges(self) -> None:
        """Total coverage of an empty range list should be 0."""
        result = calculate_total_coverage([])
        assert result == 0

    def test_single_range(self) -> None:
        """Total coverage of a single range should be the range length."""
        result = calculate_total_coverage([(0, 5)])
        assert result == 5

    def test_multiple_non_overlapping_ranges(self) -> None:
        """Total coverage of multiple non-overlapping ranges should be the sum of range lengths."""
        result = calculate_total_coverage([(0, 3), (5, 8), (10, 15)])
        assert result == 11  # 3 + 3 + 5

    def test_zero_length_ranges(self) -> None:
        """Zero-length ranges should not contribute to coverage."""
        result = calculate_total_coverage([(0, 0), (5, 5)])
        assert result == 0


class TestTextCoverageBasic(unittest.TestCase):
    """Test suite for basic TextCoverage functionality."""

    def test_empty_coverage(self) -> None:
        """Newly created TextCoverage should have no coverage ranges."""
        coverage = TextCoverage("Hello World")
        assert coverage.covered_ranges == []
        assert coverage.get_coverage_percentage() == pytest.approx(0.0)
        assert not coverage.is_fully_covered()

    def test_single_range(self) -> None:
        """Adding a single range should be correctly recorded."""
        coverage = TextCoverage("Hello")
        coverage.add_range(0, 5)
        assert len(coverage.covered_ranges) == 1
        assert coverage.covered_ranges[0] == (0, 5)

    def test_multiple_ranges(self) -> None:
        """Adding multiple non-overlapping ranges should be correctly recorded."""
        coverage = TextCoverage("Hello World")
        coverage.add_range(0, 5)
        coverage.add_range(6, 11)
        assert len(coverage.covered_ranges) == 2

    def test_overlapping_ranges(self) -> None:
        """Overlapping ranges should be automatically merged."""
        coverage = TextCoverage("Hello World")
        coverage.add_range(0, 5)
        coverage.add_range(3, 8)
        assert len(coverage.covered_ranges) == 1
        assert coverage.covered_ranges[0] == (0, 8)

    def test_adjacent_ranges(self) -> None:
        """Adjacent ranges should be automatically merged."""
        coverage = TextCoverage("Hello World")
        coverage.add_range(0, 5)
        coverage.add_range(5, 11)
        assert len(coverage.covered_ranges) == 1
        assert coverage.covered_ranges[0] == (0, 11)


class TestTextCoverageFullyCovered(unittest.TestCase):
    """Test suite for fully covered detection."""

    def test_fully_covered(self) -> None:
        """Fully covered text should be correctly identified."""
        coverage = TextCoverage("Hello")
        coverage.add_range(0, 5)
        assert coverage.is_fully_covered()

    def test_fully_covered_multiple_ranges(self) -> None:
        """Text fully covered by multiple ranges should be correctly identified."""
        coverage = TextCoverage("Hello World")
        coverage.add_range(0, 5)
        coverage.add_range(5, 11)
        assert coverage.is_fully_covered()

    def test_partially_covered(self) -> None:
        """Partially covered text should be identified as not fully covered."""
        coverage = TextCoverage("Hello World")
        coverage.add_range(0, 5)
        assert not coverage.is_fully_covered()

    def test_no_coverage(self) -> None:
        """Text with no coverage should be identified as not fully covered."""
        coverage = TextCoverage("Hello")
        assert not coverage.is_fully_covered()

    def test_gap_in_coverage(self) -> None:
        """Coverage with gaps should be identified as not fully covered."""
        coverage = TextCoverage("Hello World")
        coverage.add_range(0, 5)
        coverage.add_range(6, 11)
        assert not coverage.is_fully_covered()


class TestTextCoveragePercentage(unittest.TestCase):
    """Test suite for coverage percentage calculation."""

    def test_coverage_percentage_zero(self) -> None:
        """Percentage should be 0 when there is no coverage."""
        coverage = TextCoverage("Hello")
        assert coverage.get_coverage_percentage() == pytest.approx(0.0)

    def test_coverage_percentage_full(self) -> None:
        """Percentage should be 1.0 when fully covered."""
        coverage = TextCoverage("Hello")
        coverage.add_range(0, 5)
        assert coverage.get_coverage_percentage() == pytest.approx(1.0)

    def test_coverage_percentage_partial(self) -> None:
        """Should return correct percentage when partially covered."""
        coverage = TextCoverage("Hello")
        coverage.add_range(0, 2)  # "He"
        assert coverage.get_coverage_percentage() == pytest.approx(0.4)

    def test_coverage_percentage_with_gaps(self) -> None:
        """Coverage with gaps should calculate correct percentage."""
        coverage = TextCoverage("Hello World")  # 11 chars
        coverage.add_range(0, 5)  # "Hello" = 5 chars
        coverage.add_range(6, 11)  # "World" = 5 chars
        # Total: 10 chars out of 11
        expected = 10 / 11
        assert abs(coverage.get_coverage_percentage() - expected) < 0.001


class TestTextCoverageUncoveredRanges(unittest.TestCase):
    """Test suite for uncovered ranges extraction."""

    def test_uncovered_ranges_full_coverage(self) -> None:
        """Should have no uncovered ranges when fully covered."""
        coverage = TextCoverage("Hello")
        coverage.add_range(0, 5)
        assert coverage.get_uncovered_ranges() == []

    def test_uncovered_ranges_no_coverage(self) -> None:
        """Entire text should be uncovered range when there is no coverage."""
        coverage = TextCoverage("Hello")
        assert coverage.get_uncovered_ranges() == [(0, 5)]

    def test_uncovered_ranges_gap_in_middle(self) -> None:
        """Should return correct uncovered range when there is a gap in the middle."""
        coverage = TextCoverage("Hello World")
        coverage.add_range(0, 5)
        coverage.add_range(6, 11)
        assert coverage.get_uncovered_ranges() == [(5, 6)]

    def test_uncovered_ranges_start(self) -> None:
        """Should correctly identify when the start is uncovered."""
        coverage = TextCoverage("Hello")
        coverage.add_range(2, 5)
        assert coverage.get_uncovered_ranges() == [(0, 2)]

    def test_uncovered_ranges_end(self) -> None:
        """Should correctly identify when the end is uncovered."""
        coverage = TextCoverage("Hello")
        coverage.add_range(0, 3)
        assert coverage.get_uncovered_ranges() == [(3, 5)]

    def test_uncovered_ranges_multiple_gaps(self) -> None:
        """All gaps should be identified."""
        coverage = TextCoverage("Hello World!")  # 12 chars
        coverage.add_range(1, 4)  # "ell"
        coverage.add_range(7, 10)  # "orl"
        expected = [(0, 1), (4, 7), (10, 12)]
        assert coverage.get_uncovered_ranges() == expected


class TestTextCoverageUncoveredText(unittest.TestCase):
    """Test suite for uncovered text extraction."""

    def test_uncovered_text_full_coverage(self) -> None:
        """Uncovered text should be empty when fully covered."""
        coverage = TextCoverage("Hello")
        coverage.add_range(0, 5)
        assert coverage.get_uncovered_text() == ""

    def test_uncovered_text_no_coverage(self) -> None:
        """Uncovered text should be the full text when there is no coverage."""
        coverage = TextCoverage("Hello")
        assert coverage.get_uncovered_text() == "Hello"

    def test_uncovered_text_gap_in_middle(self) -> None:
        """Text in the middle gap should be correctly extracted."""
        coverage = TextCoverage("Hello World")
        coverage.add_range(0, 5)
        coverage.add_range(6, 11)
        assert coverage.get_uncovered_text() == " "

    def test_uncovered_text_multiple_gaps(self) -> None:
        """Text from multiple gaps should be concatenated."""
        coverage = TextCoverage("Hello World")
        coverage.add_range(1, 4)  # "ell"
        coverage.add_range(7, 10)  # "orl"
        assert coverage.get_uncovered_text() == "Ho Wd"


class TestTextCoverageEdgeCases(unittest.TestCase):
    """Test suite for edge cases."""

    def test_empty_text(self) -> None:
        """Empty text should be considered fully covered."""
        coverage = TextCoverage("")
        assert coverage.is_fully_covered()
        assert coverage.get_coverage_percentage() == pytest.approx(1.0)
        assert coverage.get_uncovered_ranges() == []
        assert coverage.get_uncovered_text() == ""

    def test_invalid_range_start_greater_than_end(self) -> None:
        """Start > end should raise ValueError."""
        coverage = TextCoverage("Hello")
        with pytest.raises(ValueError) as ctx:
            coverage.add_range(5, 3)
        assert "start" in str(ctx.value).lower()

    def test_invalid_range_negative_start(self) -> None:
        """Negative start should raise ValueError."""
        coverage = TextCoverage("Hello")
        with pytest.raises(ValueError) as ctx:
            coverage.add_range(-1, 3)
        assert "start" in str(ctx.value).lower()

    def test_invalid_range_end_exceeds_text_length(self) -> None:
        """End exceeding text length should raise ValueError."""
        coverage = TextCoverage("Hello")
        with pytest.raises(ValueError) as ctx:
            coverage.add_range(0, 10)
        assert "end" in str(ctx.value).lower()

    def test_zero_length_range(self) -> None:
        """Zero-length range should be ignored."""
        coverage = TextCoverage("Hello")
        coverage.add_range(2, 2)
        assert coverage.covered_ranges == []

    def test_unicode_text(self) -> None:
        """Should correctly handle Unicode text."""
        coverage = TextCoverage("你好世界")
        coverage.add_range(0, 2)
        coverage.add_range(2, 4)
        assert coverage.is_fully_covered()

    def test_emoji_text(self) -> None:
        """Should correctly handle emoji text."""
        coverage = TextCoverage("Hello 👋 World 🌍")
        coverage.add_range(0, len("Hello 👋 World 🌍"))
        assert coverage.is_fully_covered()


class TestTextCoverageScenarios(unittest.TestCase):
    """Test suite for real-world scenarios from the design document."""

    def test_scenario_1_fully_covered_by_multiple_rules(self) -> None:
        """
        Scenario 1: Multiple rules fully cover - "who are you".

        Rule coverage:
        - "who" [0, 3)
        - "are" [4, 7)
        - "you" [8, 11)
        Total length: 11, fully covered
        """
        text = "who are you"
        coverage = TextCoverage(text)

        # Simulate three skip rules' coverage
        coverage.add_range(0, 3)  # "who"
        coverage.add_range(4, 7)  # "are"
        coverage.add_range(8, 11)  # "you"

        # Verify not fully covered (because spaces are not covered)
        assert not coverage.is_fully_covered()
        expected_percentage = 9 / 11  # 3 + 3 + 3 = 9 covered out of 11
        assert abs(coverage.get_coverage_percentage() - expected_percentage) < 0.001
        assert coverage.get_uncovered_ranges() == [(3, 4), (7, 8)]  # Two spaces
        assert coverage.get_uncovered_text() == "  "

        # If we cover the spaces too, it should be truly fully covered
        coverage.add_range(3, 4)
        coverage.add_range(7, 8)
        assert coverage.is_fully_covered()
        assert coverage.get_uncovered_ranges() == []

    def test_scenario_2_partially_covered(self) -> None:
        """
        Scenario 2: Partially covered - "who are you and me".

        Rule coverage:
        - "who" [0, 3)
        - "are" [4, 7)
        - "you" [8, 11)
        Uncovered: " and me" [11, 18)
        Total length: 18, partially covered
        """
        text = "who are you and me"
        coverage = TextCoverage(text)

        # Simulate three skip rules' coverage
        coverage.add_range(0, 3)  # "who"
        coverage.add_range(4, 7)  # "are"
        coverage.add_range(8, 11)  # "you"

        # Verify partial coverage
        assert not coverage.is_fully_covered()
        expected_percentage = 9 / 18  # 3 + 3 + 3 = 9 covered out of 18
        assert abs(coverage.get_coverage_percentage() - expected_percentage) < 0.001

        # Verify uncovered ranges
        uncovered = coverage.get_uncovered_ranges()
        assert (11, 18) in uncovered  # " and me"

        # Verify uncovered text contains "and me"
        uncovered_text = coverage.get_uncovered_text()
        assert "and me" in uncovered_text

    def test_scenario_3_overlapping_rules(self) -> None:
        """
        Scenario 3: Overlapping rules coverage.

        Simulate the situation where multiple rules may overlap.
        """
        text = "Hello World"
        coverage = TextCoverage(text)

        # Rule 1: Cover "Hello W"
        coverage.add_range(0, 7)
        # Rule 2: Cover "World"
        coverage.add_range(6, 11)

        # Should merge into one complete coverage
        assert coverage.is_fully_covered()
        assert len(coverage.covered_ranges) == 1
        assert coverage.covered_ranges[0] == (0, 11)

    def test_scenario_4_adjacent_rules(self) -> None:
        """
        Scenario 4: Adjacent rules coverage.

        Simulate the situation where multiple rules are exactly adjacent.
        """
        text = "ABC"
        coverage = TextCoverage(text)

        # Three adjacent rules
        coverage.add_range(0, 1)  # "A"
        coverage.add_range(1, 2)  # "B"
        coverage.add_range(2, 3)  # "C"

        # Should merge into complete coverage
        assert coverage.is_fully_covered()
        assert len(coverage.covered_ranges) == 1
        assert coverage.covered_ranges[0] == (0, 3)


if __name__ == "__main__":
    unittest.main()
