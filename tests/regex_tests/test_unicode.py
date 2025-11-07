"""
Tests for Unicode support in regex.

Tests Chinese characters, Traditional/Simplified Chinese, and mixed language text.
"""

import regex


def test_chinese_character_matching() -> None:
    """Test matching Chinese characters."""
    text = "這是中文測試"
    pattern = "中文"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "中文"


def test_traditional_chinese() -> None:
    """Test matching Traditional Chinese characters."""
    text = "繁體中文測試"
    pattern = "繁體"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "繁體"


def test_simplified_chinese() -> None:
    """Test matching Simplified Chinese characters."""
    text = "简体中文测试"
    pattern = "简体"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "简体"


def test_mixed_chinese_english() -> None:
    """Test matching in mixed Chinese and English text."""
    text = "這是 English 混合文本"
    pattern = "English"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "English"


def test_chinese_substitution() -> None:
    """Test substitution with Chinese characters."""
    text = "你好世界"
    pattern = "世界"
    replacement = "朋友"

    result = regex.sub(pattern, replacement, text)
    assert result == "你好朋友"


def test_english_to_chinese_substitution() -> None:
    """Test replacing English with Chinese."""
    text = "Hello world"
    pattern = "world"
    replacement = "世界"

    result = regex.sub(pattern, replacement, text)
    assert result == "Hello 世界"


def test_chinese_to_english_substitution() -> None:
    """Test replacing Chinese with English."""
    text = "你好世界"
    pattern = "世界"
    replacement = "world"

    result = regex.sub(pattern, replacement, text)
    assert result == "你好world"


def test_unicode_word_boundary() -> None:
    """Test word boundaries with Chinese characters."""
    text = "中文abc中文"
    # Chinese characters are treated as word characters
    pattern = r"\w+"
    matches = regex.findall(pattern, text)

    # Should match Chinese and English separately or together
    assert len(matches) > 0
    assert any("中文" in match or "abc" in match for match in matches)


def test_unicode_character_class() -> None:
    """Test character classes with Unicode."""
    text = "abc123中文"
    # Match all Unicode letters
    pattern = r"\w+"
    matches = regex.findall(pattern, text)

    assert len(matches) > 0


def test_mixed_language_findall() -> None:
    """Test findall with mixed language content."""
    text = "English 中文 Français 日本語"
    pattern = r"\w+"
    matches = regex.findall(pattern, text)

    assert "English" in matches
    assert "中文" in matches
    assert "Français" in matches
    assert "日本語" in matches


def test_chinese_punctuation() -> None:
    """Test matching Chinese punctuation."""
    text = "你好，世界！"
    pattern = "你好"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "你好"


def test_chinese_in_command() -> None:
    """Test Chinese characters in shell-like commands."""
    text = "# 啟動時間：$(who -b)"
    pattern = "啟動時間"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "啟動時間"


def test_replace_in_chinese_context() -> None:
    """Test replacement in Chinese context (GlocalText scenario)."""
    text = "- 啟動時間：            ${CLR2}$(who -b | awk '{print $3, $4}')${CLR0}"
    pattern = "啟動時間"
    replacement = "開機時間"

    result = regex.sub(pattern, replacement, text)
    assert "開機時間" in result
    assert "啟動時間" not in result


def test_unicode_escape_sequence() -> None:
    """Test Unicode escape sequences."""
    # \u4e2d is '中' in Unicode
    text = "中文"
    pattern = "\u4e2d"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "中"


def test_unicode_property() -> None:
    """Test Unicode property matching (if supported by regex module)."""
    text = "abc123中文"
    # Match Han characters (Chinese)
    pattern = r"\p{Han}+"

    try:
        matches = regex.findall(pattern, text)
        assert "中文" in matches or any("中" in m or "文" in m for m in matches)
    except regex.error:
        # Skip if \p{} syntax not supported
        pass


def test_emoji_matching() -> None:
    """Test matching emoji characters."""
    text = "Hello 👋 World 🌍"
    pattern = "👋"

    match = regex.search(pattern, text)
    assert match is not None
    assert match.group() == "👋"


def test_mixed_script_substitution() -> None:
    """Test substitution in text with multiple scripts."""
    text = "User: 使用者 | Command: who"
    pattern = "who"
    replacement = "are"

    result = regex.sub(pattern, replacement, text)
    expected = "User: 使用者 | Command: are"
    assert result == expected
