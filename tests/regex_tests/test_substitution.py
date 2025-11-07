"""
Tests for regex substitution operations.

CRITICAL: This file contains tests for the user-reported issue with 'who' -> 'are'
replacement in shell commands. This is the primary focus of the test suite.
"""

import regex


def test_who_are_replacement_in_shell_command() -> None:
    """
    **PRIMARY TEST CASE**: Reproduce user-reported issue.

    Test replacing 'who' with 'are' in a shell command containing special characters.
    This is the exact scenario reported by the user where GlocalText replacement failed.
    """
    text = "- 啟動時間：            ${CLR2}$(who -b | awk '{print $3, $4}')${CLR0}"
    pattern = "who"
    replacement = "are"

    result = regex.sub(pattern, replacement, text)
    expected = "- 啟動時間：            ${CLR2}$(are -b | awk '{print $3, $4}')${CLR0}"

    assert result == expected, f"Expected: {expected}\nGot: {result}"


def test_basic_substitution() -> None:
    """Test basic regex.sub() with simple literal replacement."""
    text = "hello world"
    pattern = "world"
    replacement = "universe"

    result = regex.sub(pattern, replacement, text)
    assert result == "hello universe"


def test_substitution_multiple_occurrences() -> None:
    """Test regex.sub() replaces all occurrences by default."""
    text = "cat cat cat"
    pattern = "cat"
    replacement = "dog"

    result = regex.sub(pattern, replacement, text)
    assert result == "dog dog dog"


def test_substitution_with_count() -> None:
    """Test regex.sub() with count parameter limits replacements."""
    text = "cat cat cat"
    pattern = "cat"
    replacement = "dog"

    result = regex.sub(pattern, replacement, text, count=2)
    assert result == "dog dog cat"


def test_subn_returns_tuple() -> None:
    """Test regex.subn() returns tuple with result and count."""
    text = "cat cat cat"
    pattern = "cat"
    replacement = "dog"

    result, count = regex.subn(pattern, replacement, text)
    assert result == "dog dog dog"
    assert count == 3


def test_substitution_no_match() -> None:
    """Test regex.sub() returns original text when no match."""
    text = "hello world"
    pattern = "goodbye"
    replacement = "farewell"

    result = regex.sub(pattern, replacement, text)
    assert result == "hello world"


def test_substitution_in_complex_text() -> None:
    """Test substitution in text with various special characters."""
    text = "$(command --option=value | grep 'pattern')"
    pattern = "command"
    replacement = "script"

    result = regex.sub(pattern, replacement, text)
    expected = "$(script --option=value | grep 'pattern')"
    assert result == expected


def test_substitution_with_dollar_signs() -> None:
    """Test substitution in text containing dollar signs."""
    text = "$VAR and $OTHER_VAR"
    pattern = "VAR"
    replacement = "VARIABLE"

    result = regex.sub(pattern, replacement, text)
    expected = "$VARIABLE and $OTHER_VARIABLE"
    assert result == expected


def test_substitution_with_pipes() -> None:
    """Test substitution in text containing pipe characters."""
    text = "cmd1 | cmd2 | cmd3"
    pattern = "cmd2"
    replacement = "command2"

    result = regex.sub(pattern, replacement, text)
    expected = "cmd1 | command2 | cmd3"
    assert result == expected


def test_substitution_with_parentheses() -> None:
    """Test substitution in text containing parentheses."""
    text = "function(arg1, arg2)"
    pattern = "arg1"
    replacement = "argument1"

    result = regex.sub(pattern, replacement, text)
    expected = "function(argument1, arg2)"
    assert result == expected


def test_substitution_with_brackets() -> None:
    """Test substitution in text containing brackets."""
    text = "array[0] = value"
    pattern = "array"
    replacement = "list"

    result = regex.sub(pattern, replacement, text)
    expected = "list[0] = value"
    assert result == expected


def test_substitution_with_braces() -> None:
    """Test substitution in text containing curly braces."""
    text = "${VAR} and ${OTHER}"
    pattern = "VAR"
    replacement = "VARIABLE"

    result = regex.sub(pattern, replacement, text)
    expected = "${VARIABLE} and ${OTHER}"
    assert result == expected


def test_substitution_preserves_surrounding_text() -> None:
    """Test that substitution only affects the matched pattern."""
    text = "The who command shows who is logged in"
    pattern = "who"
    replacement = "are"

    result = regex.sub(pattern, replacement, text)
    # Note: This will replace ALL occurrences of "who"
    expected = "The are command shows are is logged in"
    assert result == expected


def test_substitution_empty_replacement() -> None:
    """Test substitution with empty string (deletion)."""
    text = "hello world"
    pattern = " world"
    replacement = ""

    result = regex.sub(pattern, replacement, text)
    assert result == "hello"


def test_substitution_in_awk_command() -> None:
    """Test substitution in AWK command similar to user's scenario."""
    text = "awk '{print $1, $2}'"
    pattern = "print"
    replacement = "show"

    result = regex.sub(pattern, replacement, text)
    expected = "awk '{show $1, $2}'"
    assert result == expected


def test_substitution_word_inside_quotes() -> None:
    """Test substitution of words inside single quotes."""
    text = "echo 'who is there'"
    pattern = "who"
    replacement = "are"

    result = regex.sub(pattern, replacement, text)
    expected = "echo 'are is there'"
    assert result == expected


def test_substitution_with_backticks() -> None:
    """Test substitution in text with backticks."""
    text = "`who -b`"
    pattern = "who"
    replacement = "are"

    result = regex.sub(pattern, replacement, text)
    expected = "`are -b`"
    assert result == expected


def test_substitution_mixed_language() -> None:
    """Test substitution in mixed Chinese and English text."""
    text = "使用者：who 命令"
    pattern = "who"
    replacement = "are"

    result = regex.sub(pattern, replacement, text)
    expected = "使用者：are 命令"
    assert result == expected


def test_substitution_with_function_replacement() -> None:
    """Test regex.sub() with a replacement function."""
    text = "value is 5"
    pattern = r"\d+"

    def double_number(match: regex.Match[str]) -> str:
        return str(int(match.group()) * 2)

    result = regex.sub(pattern, double_number, text)
    assert result == "value is 10"


def test_substitution_case_sensitive() -> None:
    """Test that substitution is case-sensitive by default."""
    text = "Who is there who knows"
    pattern = "who"
    replacement = "are"

    result = regex.sub(pattern, replacement, text)
    # Only lowercase 'who' should be replaced
    expected = "Who is there are knows"
    assert result == expected
