"""
Tests for various regex patterns.

Tests word boundaries, character classes, quantifiers, groups, and other patterns.
"""

import regex


def test_word_boundary() -> None:
    r"""Test word boundary metacharacter \\b."""
    text = "the cat and category"
    pattern = r"\bcat\b"
    matches = regex.findall(pattern, text)

    # Should match "cat" but not "cat" in "category"
    assert matches == ["cat"]


def test_word_boundary_start() -> None:
    """Test word boundary at start of word."""
    text = "category cat"
    pattern = r"\bcat"
    matches = regex.findall(pattern, text)

    # Should match both occurrences (start of "category" and standalone "cat")
    assert len(matches) == 2


def test_word_boundary_end() -> None:
    """Test word boundary at end of word."""
    text = "cat cats"
    pattern = r"cat\b"
    matches = regex.findall(pattern, text)

    # Should match "cat" but not "cat" in "cats"
    assert matches == ["cat"]


def test_character_class_digits() -> None:
    """Test character class for digits."""
    text = "abc123def456"
    pattern = r"\d+"
    matches = regex.findall(pattern, text)

    assert matches == ["123", "456"]


def test_character_class_word_chars() -> None:
    """Test character class for word characters."""
    text = "hello_world 123"
    pattern = r"\w+"
    matches = regex.findall(pattern, text)

    assert matches == ["hello_world", "123"]


def test_character_class_whitespace() -> None:
    """Test character class for whitespace."""
    text = "hello world\ttab\nnewline"
    pattern = r"\s+"
    matches = regex.findall(pattern, text)

    assert len(matches) == 3


def test_custom_character_class() -> None:
    """Test custom character class."""
    text = "aeiou bcdfg"
    pattern = r"[aeiou]+"
    matches = regex.findall(pattern, text)

    # Only "aeiou" contains vowels; "bcdfg" has none
    assert matches == ["aeiou"]


def test_negated_character_class() -> None:
    """Test negated character class."""
    text = "abc123"
    pattern = r"[^0-9]+"
    matches = regex.findall(pattern, text)

    assert matches == ["abc"]


def test_quantifier_star() -> None:
    """Test * quantifier (zero or more)."""
    text = "a aa aaa b"
    pattern = r"a*"
    matches = regex.findall(pattern, text)

    # Will match even empty strings between characters
    assert "a" in matches
    assert "aa" in matches
    assert "aaa" in matches


def test_quantifier_plus() -> None:
    """Test + quantifier (one or more)."""
    text = "a aa aaa b"
    pattern = r"a+"
    matches = regex.findall(pattern, text)

    assert matches == ["a", "aa", "aaa"]


def test_quantifier_question() -> None:
    """Test ? quantifier (zero or one)."""
    text = "color colour"
    pattern = r"colou?r"
    matches = regex.findall(pattern, text)

    assert matches == ["color", "colour"]


def test_quantifier_exact() -> None:
    """Test {n} quantifier (exactly n times)."""
    text = "12 123 1234"
    pattern = r"\d{3}"
    matches = regex.findall(pattern, text)

    assert matches == ["123", "123"]


def test_quantifier_range() -> None:
    """Test {n,m} quantifier (between n and m times)."""
    text = "1 12 123 1234"
    pattern = r"\d{2,3}"
    matches = regex.findall(pattern, text)

    assert matches == ["12", "123", "123"]


def test_capturing_group() -> None:
    """Test capturing group ()."""
    text = "John Doe"
    pattern = r"(\w+) (\w+)"
    match = regex.search(pattern, text)

    assert match is not None
    assert match.group(1) == "John"
    assert match.group(2) == "Doe"
    assert match.group(0) == "John Doe"


def test_non_capturing_group() -> None:
    """Test non-capturing group (?:...)."""
    text = "color: red"
    pattern = r"(?:color): (\w+)"
    match = regex.search(pattern, text)

    assert match is not None
    assert match.group(1) == "red"
    # group(0) is the entire match
    assert match.group(0) == "color: red"


def test_alternation() -> None:
    """Test alternation with pipe |."""
    text = "cat dog bird"
    pattern = r"cat|dog"
    matches = regex.findall(pattern, text)

    assert matches == ["cat", "dog"]


def test_greedy_quantifier() -> None:
    """Test greedy quantifier behavior."""
    text = "<tag>content</tag>"
    pattern = r"<.*>"
    match = regex.search(pattern, text)

    # Greedy: matches the entire string
    assert match is not None
    assert match.group() == "<tag>content</tag>"


def test_non_greedy_quantifier() -> None:
    """Test non-greedy quantifier with ?."""
    text = "<tag>content</tag>"
    pattern = r"<.*?>"
    matches = regex.findall(pattern, text)

    # Non-greedy: matches shortest possible
    assert matches == ["<tag>", "</tag>"]


def test_anchors_start() -> None:
    """Test ^ anchor (start of string)."""
    text = "hello world"
    pattern = r"^hello"
    match = regex.search(pattern, text)

    assert match is not None

    pattern_fail = r"^world"
    match_fail = regex.search(pattern_fail, text)
    assert match_fail is None


def test_anchors_end() -> None:
    """Test $ anchor (end of string)."""
    text = "hello world"
    pattern = r"world$"
    match = regex.search(pattern, text)

    assert match is not None

    pattern_fail = r"hello$"
    match_fail = regex.search(pattern_fail, text)
    assert match_fail is None


def test_dot_metacharacter() -> None:
    """Test . metacharacter (matches any character except newline)."""
    text = "cat cot cut"
    pattern = r"c.t"
    matches = regex.findall(pattern, text)

    assert matches == ["cat", "cot", "cut"]


def test_findall_multiple_groups() -> None:
    """Test findall with multiple capturing groups."""
    text = "John:25 Jane:30 Bob:35"
    pattern = r"(\w+):(\d+)"
    matches = regex.findall(pattern, text)

    # Returns list of tuples
    assert matches == [("John", "25"), ("Jane", "30"), ("Bob", "35")]


def test_split_with_pattern() -> None:
    """Test regex.split() with pattern."""
    text = "one,two;three:four"
    pattern = r"[,;:]"
    parts = regex.split(pattern, text)

    assert parts == ["one", "two", "three", "four"]


def test_finditer() -> None:
    """Test regex.finditer() returns iterator of Match objects."""
    text = "cat dog cat"
    pattern = r"cat"
    matches = list(regex.finditer(pattern, text))

    assert len(matches) == 2
    assert matches[0].start() == 0
    assert matches[1].start() == 8
