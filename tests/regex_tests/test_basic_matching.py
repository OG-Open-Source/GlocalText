"""
Tests for basic regex matching operations.

Tests the fundamental matching functions: search(), match(), and fullmatch().
Validates literal string matching and special character escaping.
"""

import regex


def test_search_partial_match() -> None:
    """Test regex.search() finds pattern anywhere in string."""
    text = "The quick brown fox"
    pattern = "quick"
    match = regex.search(pattern, text)

    assert match is not None
    assert match.group() == "quick"
    assert match.start() == 4


def test_search_not_found() -> None:
    """Test regex.search() returns None when pattern not found."""
    text = "The quick brown fox"
    pattern = "slow"
    match = regex.search(pattern, text)

    assert match is None


def test_match_from_beginning() -> None:
    """Test regex.match() only matches from the start of string."""
    text = "The quick brown fox"
    pattern = "The"
    match = regex.match(pattern, text)

    assert match is not None
    assert match.group() == "The"


def test_match_not_from_beginning() -> None:
    """Test regex.match() returns None if pattern not at start."""
    text = "The quick brown fox"
    pattern = "quick"
    match = regex.match(pattern, text)

    assert match is None


def test_fullmatch_entire_string() -> None:
    """Test regex.fullmatch() matches entire string exactly."""
    text = "hello"
    pattern = "hello"
    match = regex.fullmatch(pattern, text)

    assert match is not None
    assert match.group() == "hello"


def test_fullmatch_partial_fails() -> None:
    """Test regex.fullmatch() fails on partial matches."""
    text = "hello world"
    pattern = "hello"
    match = regex.fullmatch(pattern, text)

    assert match is None


def test_literal_string_matching() -> None:
    """Test matching literal strings without regex metacharacters."""
    text = "who is there"
    pattern = "who"
    match = regex.search(pattern, text)

    assert match is not None
    assert match.group() == "who"


def test_case_sensitive_matching() -> None:
    """Test that matching is case-sensitive by default."""
    text = "Hello World"
    pattern = "hello"
    match = regex.search(pattern, text)

    assert match is None


def test_escape_special_characters_dot() -> None:
    """Test escaping the dot metacharacter."""
    text = "file.txt"
    # Without escaping, dot matches any character
    pattern_unescaped = "file.txt"
    match_unescaped = regex.search(pattern_unescaped, "fileXtxt")
    assert match_unescaped is not None

    # With escaping, dot matches literal dot
    pattern_escaped = r"file\.txt"
    match_escaped = regex.search(pattern_escaped, text)
    assert match_escaped is not None
    assert match_escaped.group() == "file.txt"


def test_escape_special_characters_parentheses() -> None:
    """Test escaping parentheses metacharacters."""
    text = "function(arg)"
    pattern = r"function\(arg\)"
    match = regex.search(pattern, text)

    assert match is not None
    assert match.group() == "function(arg)"


def test_multiple_matches_find_first() -> None:
    """Test regex.search() finds the first occurrence."""
    text = "cat cat cat"
    pattern = "cat"
    match = regex.search(pattern, text)

    assert match is not None
    assert match.start() == 0
    assert match.group() == "cat"


def test_empty_pattern() -> None:
    """Test matching with empty pattern."""
    text = "hello"
    pattern = ""
    match = regex.search(pattern, text)

    # Empty pattern matches at position 0
    assert match is not None
    assert match.start() == 0
    assert match.group() == ""


def test_empty_string() -> None:
    """Test searching in empty string."""
    text = ""
    pattern = "hello"
    match = regex.search(pattern, text)

    assert match is None


def test_match_object_attributes() -> None:
    """Test accessing Match object attributes."""
    text = "The quick brown"
    pattern = "quick"
    match = regex.search(pattern, text)

    assert match is not None
    assert match.group() == "quick"
    assert match.start() == 4
    assert match.end() == 9
    assert match.span() == (4, 9)
