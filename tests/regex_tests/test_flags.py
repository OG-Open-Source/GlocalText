"""
Tests for regex flags.

Tests IGNORECASE, MULTILINE, DOTALL, and VERBOSE flags.
"""

import regex


def test_ignorecase_flag() -> None:
    """Test regex.IGNORECASE flag for case-insensitive matching."""
    text = "Hello World"
    pattern = "hello"

    # Without flag, no match
    match_without = regex.search(pattern, text)
    assert match_without is None

    # With IGNORECASE flag, matches
    match_with = regex.search(pattern, text, regex.IGNORECASE)
    assert match_with is not None
    assert match_with.group() == "Hello"


def test_ignorecase_flag_short() -> None:
    """Test regex.I as shorthand for IGNORECASE."""
    text = "HELLO world"
    pattern = "hello"

    match = regex.search(pattern, text, regex.I)
    assert match is not None
    assert match.group() == "HELLO"


def test_multiline_flag() -> None:
    """Test regex.MULTILINE flag changes ^ and $ behavior."""
    text = "line1\nline2\nline3"
    pattern = r"^line"

    # Without MULTILINE, ^ only matches start of string
    matches_without = regex.findall(pattern, text)
    assert len(matches_without) == 1
    assert matches_without == ["line"]

    # With MULTILINE, ^ matches start of each line
    matches_with = regex.findall(pattern, text, regex.MULTILINE)
    assert len(matches_with) == 3
    assert matches_with == ["line", "line", "line"]


def test_multiline_flag_end_anchor() -> None:
    """Test regex.MULTILINE with $ anchor."""
    text = "end1\nend2\nend3"
    pattern = r"\d$"

    # Without MULTILINE, $ only matches end of string
    matches_without = regex.findall(pattern, text)
    assert matches_without == ["3"]

    # With MULTILINE, $ matches end of each line
    matches_with = regex.findall(pattern, text, regex.MULTILINE)
    assert matches_with == ["1", "2", "3"]


def test_dotall_flag() -> None:
    """Test regex.DOTALL flag makes dot match newlines."""
    text = "first\nsecond"
    pattern = r"first.second"

    # Without DOTALL, dot doesn't match newline
    match_without = regex.search(pattern, text)
    assert match_without is None

    # With DOTALL, dot matches newline
    match_with = regex.search(pattern, text, regex.DOTALL)
    assert match_with is not None
    assert match_with.group() == "first\nsecond"


def test_dotall_flag_short() -> None:
    """Test regex.S as shorthand for DOTALL."""
    text = "line1\nline2"
    pattern = r"line1.line2"

    match = regex.search(pattern, text, regex.S)
    assert match is not None


def test_verbose_flag() -> None:
    """Test regex.VERBOSE flag allows comments and whitespace in pattern."""
    text = "test123"

    # Verbose pattern with comments and whitespace
    pattern = r"""
        test    # Match the word "test"
        \d+     # Followed by one or more digits
    """

    match = regex.search(pattern, text, regex.VERBOSE)
    assert match is not None
    assert match.group() == "test123"


def test_verbose_flag_short() -> None:
    """Test regex.X as shorthand for VERBOSE."""
    text = "abc123"
    pattern = r"""
        [a-z]+  # Letters
        \d+     # Digits
    """

    match = regex.search(pattern, text, regex.X)
    assert match is not None
    assert match.group() == "abc123"


def test_combined_flags() -> None:
    """Test combining multiple flags with bitwise OR."""
    text = "Hello\nWorld"
    pattern = r"^hello.*world$"

    # Combine IGNORECASE, DOTALL, and MULTILINE
    match = regex.search(pattern, text, regex.IGNORECASE | regex.DOTALL | regex.MULTILINE)
    assert match is not None
    assert match.group() == "Hello\nWorld"


def test_inline_flags() -> None:
    """Test inline flag syntax (?i), (?m), (?s), (?x)."""
    # IGNORECASE inline flag
    text = "Hello World"
    pattern = r"(?i)hello"
    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "Hello"


def test_inline_multiline_flag() -> None:
    """Test inline MULTILINE flag."""
    text = "line1\nline2"
    pattern = r"(?m)^line2"
    match = regex.search(pattern, text)
    assert match is not None


def test_inline_dotall_flag() -> None:
    """Test inline DOTALL flag."""
    text = "a\nb"
    pattern = r"(?s)a.b"
    match = regex.search(pattern, text)
    assert match is not None


def test_flag_with_substitution() -> None:
    """Test using flags with regex.sub()."""
    text = "Hello HELLO hello"
    pattern = "hello"
    replacement = "hi"

    result = regex.sub(pattern, replacement, text, flags=regex.IGNORECASE)
    assert result == "hi hi hi"


def test_case_sensitive_by_default() -> None:
    """Test that matching is case-sensitive by default."""
    text = "ABC abc"
    pattern = "abc"

    matches = regex.findall(pattern, text)
    assert matches == ["abc"]
    assert len(matches) == 1


def test_multiline_vs_default() -> None:
    """Test difference between MULTILINE and default behavior."""
    text = "start\nmiddle\nend"

    # Default: ^ matches only start of string
    pattern_start = r"^start"
    match1 = regex.search(pattern_start, text)
    assert match1 is not None

    pattern_middle = r"^middle"
    match2 = regex.search(pattern_middle, text)
    assert match2 is None  # Doesn't match without MULTILINE

    # With MULTILINE: ^ matches start of any line
    match3 = regex.search(pattern_middle, text, regex.MULTILINE)
    assert match3 is not None
