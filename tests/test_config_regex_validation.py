"""Tests for regex pattern validation in configuration rules."""

import unittest
from unittest.mock import mock_open, patch

import pytest

from glocaltext.config import load_config


class TestRegexValidation(unittest.TestCase):
    """Test suite for regex pattern validation in rules."""

    def test_valid_regex_patterns_success(self) -> None:
        """1. Valid regex patterns in all rule types should load successfully."""
        yaml_content = """
tasks:
  - name: 'Valid Patterns'
    source_lang: 'en'
    target_lang: 'fr'
    source:
      include: ['*.txt']
    rules:
      skip: ['^SKIP.*', '\\d{3}-\\d{4}']
      protect: ['`[^`]+`', '\\[.*?\\]']
      replace:
        'old': 'new'
        '\\bfoo\\b': 'bar'
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True):
            config = load_config("dummy_path.yaml")
            assert len(config.tasks) == 1
            assert len(config.tasks[0].rules) == 6

    def test_invalid_regex_in_skip_rule(self) -> None:
        """2. Invalid regex syntax in skip rule should raise ValueError."""
        yaml_content = """
tasks:
  - name: 'Invalid Skip'
    source_lang: 'en'
    target_lang: 'fr'
    source:
      include: ['*.txt']
    rules:
      skip: ['[invalid']
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True), pytest.raises(ValueError, match="Invalid regex pattern in skip rule"):
            load_config("dummy_path.yaml")

    def test_invalid_regex_in_protect_rule(self) -> None:
        """3. Invalid regex syntax in protect rule should raise ValueError."""
        yaml_content = """
tasks:
  - name: 'Invalid Protect'
    source_lang: 'en'
    target_lang: 'fr'
    source:
      include: ['*.txt']
    rules:
      protect: ['(?P<incomplete']
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True), pytest.raises(ValueError, match="Invalid regex pattern in protect rule"):
            load_config("dummy_path.yaml")

    def test_invalid_regex_in_replace_rule(self) -> None:
        """4. Invalid regex syntax in replace rule should raise ValueError."""
        yaml_content = """
tasks:
  - name: 'Invalid Replace'
    source_lang: 'en'
    target_lang: 'fr'
    source:
      include: ['*.txt']
    rules:
      replace:
        '*invalid*': 'replacement'
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True), pytest.raises(ValueError, match="Invalid regex pattern in replace rule"):
            load_config("dummy_path.yaml")

    def test_mixed_valid_and_invalid_patterns(self) -> None:
        """5. Mixed valid and invalid patterns should fail at first invalid pattern."""
        yaml_content = """
tasks:
  - name: 'Mixed Patterns'
    source_lang: 'en'
    target_lang: 'fr'
    source:
      include: ['*.txt']
    rules:
      skip: ['^valid', '[invalid']
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True), pytest.raises(ValueError, match="Invalid regex pattern"):
            load_config("dummy_path.yaml")

    def test_legacy_format_with_invalid_regex(self) -> None:
        """6. Legacy list format with invalid regex should raise ValueError."""
        yaml_content = """
tasks:
  - name: 'Legacy Invalid'
    source_lang: 'en'
    target_lang: 'fr'
    source:
      include: ['*.txt']
    rules:
      - 'skip: [unclosed'
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True), pytest.raises(ValueError, match="Invalid regex pattern"):
            load_config("dummy_path.yaml")


if __name__ == "__main__":
    unittest.main()
