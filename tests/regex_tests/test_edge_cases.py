"""
Tests for edge cases and boundary conditions.

Tests empty strings, special characters, escape sequences, long text, and error handling.
"""

import regex


def test_empty_string_pattern() -> None:
    """Test matching with empty pattern."""
    text = "hello"
    pattern = ""

    match = regex.search(pattern, text)
    # Empty pattern matches at start
    assert match is not None
    assert match.start() == 0


def test_empty_string_text() -> None:
    """Test matching in empty text."""
    text = ""
    pattern = "hello"

    match = regex.search(pattern, text)
    assert match is None


def test_both_empty_strings() -> None:
    """Test matching when both pattern and text are empty."""
    text = ""
    pattern = ""

    match = regex.search(pattern, text)
    assert match is not None


def test_special_char_pipe() -> None:
    """Test literal pipe character (needs escaping in pattern)."""
    text = "cmd1 | cmd2"
    pattern = r"\|"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "|"


def test_special_char_dollar() -> None:
    """Test literal dollar sign (needs escaping in pattern)."""
    text = "$100"
    pattern = r"\$"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "$"


def test_special_char_parentheses() -> None:
    """Test literal parentheses (need escaping in pattern)."""
    text = "func()"
    pattern = r"\(\)"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "()"


def test_special_char_brackets() -> None:
    """Test literal brackets (need escaping in pattern)."""
    text = "array[]"
    pattern = r"\[\]"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "[]"


def test_special_char_braces() -> None:
    """Test literal braces (need escaping in pattern)."""
    text = "{}"
    pattern = r"\{\}"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "{}"


def test_special_char_asterisk() -> None:
    """Test literal asterisk (needs escaping in pattern)."""
    text = "a*b"
    pattern = r"\*"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "*"


def test_special_char_plus() -> None:
    """Test literal plus sign (needs escaping in pattern)."""
    text = "a+b"
    pattern = r"\+"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "+"


def test_special_char_question() -> None:
    """Test literal question mark (needs escaping in pattern)."""
    text = "what?"
    pattern = r"\?"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "?"


def test_special_char_dot() -> None:
    """Test literal dot (needs escaping in pattern)."""
    text = "file.txt"
    pattern = r"\."

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "."


def test_special_char_caret() -> None:
    """Test literal caret (needs escaping in pattern)."""
    text = "x^2"
    pattern = r"\^"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "^"


def test_backslash_escaping() -> None:
    """Test literal backslash (needs double escaping)."""
    text = r"C:\path"
    pattern = r"\\"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "\\"


def test_newline_in_text() -> None:
    """Test matching across newlines."""
    text = "line1\nline2"
    pattern = "line1"

    match = regex.search(pattern, text)
    assert match is not None


def test_tab_character() -> None:
    """Test matching tab character."""
    text = "word1\tword2"
    pattern = r"\t"

    match = regex.search(pattern, text)
    assert match is not None


def test_very_long_text() -> None:
    """Test regex performance with long text."""
    text = "a" * 10000 + "needle" + "b" * 10000
    pattern = "needle"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "needle"


def test_many_repetitions() -> None:
    """Test pattern with many repetitions."""
    text = "a" * 100
    pattern = r"a+"

    match = regex.search(pattern, text)
    assert match is not None
    assert len(match.group()) == 100


def test_invalid_regex_pattern() -> None:
    """Test handling of invalid regex pattern."""
    text = "hello"
    pattern = "["  # Unclosed character class

    try:
        regex.search(pattern, text)
        # If no error raised, fail the test
        assert False, "Expected regex.error to be raised"  # noqa: B011, PT015
    except regex.error:
        # Expected behavior
        pass


def test_nested_groups() -> None:
    """Test deeply nested capturing groups."""
    text = "abc"
    pattern = r"((a)(b)(c))"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group(0) == "abc"
    assert match.group(1) == "abc"
    assert match.group(2) == "a"
    assert match.group(3) == "b"
    assert match.group(4) == "c"


def test_null_byte() -> None:
    """Test handling of null byte in text."""
    text = "hello\x00world"
    pattern = "hello"

    match = regex.search(pattern, text)
    assert match is not None


def test_unicode_escape() -> None:
    """Test Unicode escape sequences in pattern."""
    text = "hello"
    pattern = r"h\u0065llo"  # \u0065 is 'e'

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "hello"


def test_substitution_with_empty_replacement() -> None:
    """Test substitution with empty string removes matched text."""
    text = "hello world"
    pattern = "world"
    replacement = ""

    result = regex.sub(pattern, replacement, text)
    assert result == "hello "


def test_substitution_no_match_returns_original() -> None:
    """Test that sub returns original text when no match."""
    text = "hello"
    pattern = "goodbye"
    replacement = "hi"

    result = regex.sub(pattern, replacement, text)
    assert result == "hello"


def test_zero_width_assertion() -> None:
    """Test zero-width assertions."""
    text = "test123"
    # Positive lookahead
    pattern = r"test(?=\d)"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "test"


def test_overlapping_matches() -> None:
    """Test findall with overlapping matches."""
    text = "aaa"
    pattern = "aa"

    # Standard findall doesn't find overlapping matches
    matches = regex.findall(pattern, text)
    assert len(matches) == 1

    # regex module supports overlapped parameter
    try:
        matches_overlapped = regex.findall(pattern, text, overlapped=True)
        assert len(matches_overlapped) == 2
    except TypeError:
        # If overlapped not supported, skip this part
        pass
