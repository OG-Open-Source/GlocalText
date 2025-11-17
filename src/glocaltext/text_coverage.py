"""
Text coverage tracking module.

This module provides text coverage range tracking functionality for determining
whether various rules (skip, replace, protect) fully cover the text content.
This enables us to detect fully covered text and skip translation to improve
performance and accuracy.

Main components:
- TextCoverage: Core class for tracking coverage ranges
- merge_ranges(): Helper function for merging overlapping ranges
- calculate_total_coverage(): Helper function for calculating total covered characters

Usage example:
    >>> coverage = TextCoverage("Hello World")
    >>> coverage.add_range(0, 5)   # "Hello"
    >>> coverage.add_range(6, 11)  # "World"
    >>> coverage.is_fully_covered()
    False  # Because the space in the middle is not covered
    >>> coverage.add_range(5, 6)   # Add space coverage
    >>> coverage.is_fully_covered()
    True
"""

from dataclasses import dataclass, field


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    Merge overlapping or adjacent ranges.

    Algorithm: Sort all ranges first, then linearly scan to merge adjacent or overlapping ranges.
    Time complexity: O(n log n), where n is the number of ranges.
    Space complexity: O(n).

    Args:
        ranges: List of ranges, each range is a (start, end) tuple representing [start, end)

    Returns:
        Merged list of ranges, guaranteed non-overlapping and sorted

    Examples:
        >>> merge_ranges([(0, 3), (2, 5), (7, 9)])
        [(0, 5), (7, 9)]
        >>> merge_ranges([(0, 3), (3, 5)])  # Adjacent ranges are also merged
        [(0, 5)]

    """
    if not ranges:
        return []

    # Sort by start position
    sorted_ranges = sorted(ranges, key=lambda r: r[0])

    merged: list[tuple[int, int]] = [sorted_ranges[0]]

    for current_start, current_end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]

        # If current range overlaps or is adjacent to the last range, merge them
        if current_start <= last_end:
            # Merge ranges, taking the maximum end position of both
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # Otherwise add new range
            merged.append((current_start, current_end))

    return merged


def calculate_total_coverage(ranges: list[tuple[int, int]]) -> int:
    """
    Calculate the total number of characters covered by the range list.

    Note: This function assumes ranges are already merged (non-overlapping).
    If ranges overlap, merge_ranges() should be called first.

    Args:
        ranges: List of ranges, each range is a (start, end) tuple

    Returns:
        Total number of covered characters

    Examples:
        >>> calculate_total_coverage([(0, 3), (5, 8)])
        6
        >>> calculate_total_coverage([])
        0

    """
    return sum(end - start for start, end in ranges)


@dataclass
class TextCoverage:
    """
    Track text coverage ranges to determine if rules fully cover the text content.

    This class maintains a set of coverage ranges and provides methods to:
    - Add new coverage ranges
    - Check if text is fully covered
    - Calculate coverage percentage
    - Extract uncovered ranges and text

    Attributes:
        original_text: Original text string
        covered_ranges: List of covered ranges, each range is a (start, end) tuple

    Usage example:
        >>> coverage = TextCoverage("Hello World")
        >>> coverage.add_range(0, 5)   # "Hello"
        >>> coverage.add_range(6, 11)  # "World"
        >>> coverage.is_fully_covered()
        True
        >>> coverage.get_coverage_percentage()
        1.0

    """

    original_text: str
    covered_ranges: list[tuple[int, int]] = field(default_factory=list)

    def add_range(self, start: int, end: int) -> None:
        """
        Add a coverage range [start, end).

        Ranges are automatically merged to maintain internal consistency.
        Validates range validity (start <= end, within text bounds).

        Args:
            start: Start position (inclusive)
            end: End position (exclusive)

        Raises:
            ValueError: If range is invalid (start > end or exceeds text bounds)

        Examples:
            >>> coverage = TextCoverage("Hello")
            >>> coverage.add_range(0, 5)
            >>> len(coverage.covered_ranges)
            1

        """
        # Validate range validity
        if start > end:
            msg = f"Invalid range: start ({start}) cannot be greater than end ({end})"
            raise ValueError(msg)

        if start < 0:
            msg = f"Invalid range: start ({start}) cannot be less than 0"
            raise ValueError(msg)

        if end > len(self.original_text):
            msg = f"Invalid range: end ({end}) exceeds text length ({len(self.original_text)})"
            raise ValueError(msg)

        # If empty range, don't add
        if start == end:
            return

        # Add range and re-merge
        self.covered_ranges.append((start, end))
        self.covered_ranges = merge_ranges(self.covered_ranges)

    def is_fully_covered(self) -> bool:
        """
        Check if text is fully covered.

        Full coverage definition: Merged ranges form a continuous interval [0, len(text)).

        Returns:
            True if text is fully covered, False otherwise

        Examples:
            >>> coverage = TextCoverage("Hi")
            >>> coverage.add_range(0, 2)
            >>> coverage.is_fully_covered()
            True
            >>> coverage2 = TextCoverage("Hi")
            >>> coverage2.add_range(0, 1)
            >>> coverage2.is_fully_covered()
            False

        """
        # Empty text is considered fully covered
        if len(self.original_text) == 0:
            return True

        # No coverage ranges
        if not self.covered_ranges:
            return False

        # Check if there is only one range that covers the entire text
        merged = merge_ranges(self.covered_ranges)
        return len(merged) == 1 and merged[0] == (0, len(self.original_text))

    def get_coverage_percentage(self) -> float:
        """
        Calculate coverage percentage (0.0 - 1.0).

        Returns:
            Coverage percentage, ranging from 0.0 (no coverage) to 1.0 (full coverage)

        Examples:
            >>> coverage = TextCoverage("Hello")
            >>> coverage.add_range(0, 2)  # "He"
            >>> coverage.get_coverage_percentage()
            0.4

        """
        text_length = len(self.original_text)

        # Empty text is considered 100% covered
        if text_length == 0:
            return 1.0

        merged = merge_ranges(self.covered_ranges)
        covered_chars = calculate_total_coverage(merged)

        return covered_chars / text_length

    def get_uncovered_ranges(self) -> list[tuple[int, int]]:
        """
        Return list of uncovered ranges.

        This method calculates which parts of the original text are not yet covered by any rule.

        Returns:
            List of uncovered ranges, each range is a (start, end) tuple

        Examples:
            >>> coverage = TextCoverage("Hello World")
            >>> coverage.add_range(0, 5)   # "Hello"
            >>> coverage.add_range(6, 11)  # "World"
            >>> coverage.get_uncovered_ranges()
            [(5, 6)]  # Space character

        """
        text_length = len(self.original_text)

        # If no coverage ranges, entire text is uncovered
        if not self.covered_ranges:
            return [(0, text_length)] if text_length > 0 else []

        merged = merge_ranges(self.covered_ranges)
        uncovered: list[tuple[int, int]] = []

        # Check before the first range
        if merged[0][0] > 0:
            uncovered.append((0, merged[0][0]))

        # Check gaps between adjacent ranges
        for i in range(len(merged) - 1):
            gap_start = merged[i][1]
            gap_end = merged[i + 1][0]
            if gap_start < gap_end:
                uncovered.append((gap_start, gap_end))

        # Check after the last range
        if merged[-1][1] < text_length:
            uncovered.append((merged[-1][1], text_length))

        return uncovered

    def get_uncovered_text(self) -> str:
        """
        Extract uncovered text content.

        This method concatenates text from all uncovered ranges.

        Returns:
            Uncovered text content (may contain multiple non-contiguous fragments)

        Examples:
            >>> coverage = TextCoverage("Hello World")
            >>> coverage.add_range(0, 5)   # "Hello"
            >>> coverage.add_range(6, 11)  # "World"
            >>> coverage.get_uncovered_text()
            ' '  # Only the space in the middle is uncovered

        """
        uncovered_ranges = self.get_uncovered_ranges()
        return "".join(self.original_text[start:end] for start, end in uncovered_ranges)
