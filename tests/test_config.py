"""Tests for the configuration loading and parsing logic."""

import unittest
from unittest.mock import mock_open, patch

import pytest
import yaml

from glocaltext.config import (
    GlocalConfig,
    load_config,
)
from glocaltext.types import Source


class TestConfigLoading(unittest.TestCase):
    """Test suite for loading and parsing the GlocalText configuration."""

    def test_load_config_success(self) -> None:
        """1. Success: Correctly loads a valid YAML configuration file."""
        yaml_content = """
providers:
  gemini:
    model: 'gemini-pro'
tasks:
  - name: 'Translate Docs'
    source_lang: 'en'
    target_lang: 'ja'
    source:
      include: ['docs/**/*.md']
    translator: 'gemini'
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True):
            config = load_config("dummy_path.yaml")

            assert isinstance(config, GlocalConfig)
            assert "gemini" in config.providers
            assert config.providers["gemini"].model == "gemini-pro"
            assert len(config.tasks) == 1
            assert config.tasks[0].name == "Translate Docs"
            assert config.tasks[0].source.include == ["docs/**/*.md"]

    def test_load_config_file_not_found(self) -> None:
        """2. Failure: Raises FileNotFoundError for a non-existent file."""
        with patch("pathlib.Path.is_file", return_value=False), pytest.raises(FileNotFoundError):
            load_config("non_existent_file.yaml")

    def test_load_config_invalid_yaml(self) -> None:
        """3. Failure: Raises ValueError for a structurally invalid YAML file."""
        invalid_yaml_content = "providers: [gemini: {model: 'pro'}]"
        with patch("pathlib.Path.open", mock_open(read_data=invalid_yaml_content)), patch("pathlib.Path.is_file", return_value=True), pytest.raises(ValueError, match="Invalid or missing configuration"):
            load_config("invalid.yaml")

    def test_apply_shortcuts_and_defaults(self) -> None:
        """4. Logic: Correctly applies .defaults and custom shortcuts."""
        yaml_content = """
shortcuts:
  .defaults: &defaults
    translator: 'gemini'
    source_lang: 'en'
    incremental: true

  .docs: &docs
    <<: *defaults
    source:
      include: ['**/*.md']
    rules:
      - 'protect: `([^`]+)`'

tasks:
  - name: 'Translate README'
    target_lang: 'zh-TW'
    source:
      include: ['README.md'] # Override source

  - name: 'Translate Python Docs'
    <<: *docs
    target_lang: 'py-ja'
    # Inherits source and rules
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True):
            config = load_config("dummy_path.yaml")
            readme_task = config.tasks[0]
            py_docs_task = config.tasks[1]

            # Task 1: Inherits from .defaults only
            assert readme_task.translator == "gemini"
            assert readme_task.source_lang == "en"
            assert readme_task.incremental
            assert readme_task.source.include == ["README.md"]
            assert len(readme_task.rules) == 0

            # Task 2: Inherits from .docs, which inherits from .defaults
            assert py_docs_task.translator == "gemini"
            assert py_docs_task.target_lang == "py-ja"
            assert py_docs_task.source.include == ["**/*.md"]
            assert py_docs_task.incremental
            assert len(py_docs_task.rules) == 1
            assert py_docs_task.rules[0].action.action == "protect"

    def test_new_source_structure_with_exclude(self) -> None:
        """5. Refactor: Correctly parses the new source structure with include and exclude."""
        yaml_content = """
tasks:
  - name: 'Test Exclude'
    source_lang: 'en'
    target_lang: 'fr'
    translator: 'mock'
    source:
      include: ['src/**/*.py']
      exclude: ['src/generated/**', 'src/legacy.py']
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True):
            config = load_config("dummy_path.yaml")
            task = config.tasks[0]

            assert task.source.include == ["src/**/*.py"]
            assert task.source.exclude == ["src/generated/**", "src/legacy.py"]

    def test_removed_features_do_not_break_loading(self) -> None:
        """6. Refactor: Ensures old, removed fields are safely ignored."""
        yaml_content_with_old_fields = """
debug_options:
  enabled: true
report_options:
  export_csv: true
providers:
  gemini:
    batch_options:
      enabled: false
tasks:
  - name: 'Old Task'
    source_lang: 'en'
    target_lang: 'de'
    translator: 'gemini'
    source:
      include: ['*.txt']
    output:
      filename_suffix: '_de'
    regex_rewrites:
      'old': 'new'
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content_with_old_fields)), patch("pathlib.Path.is_file", return_value=True):
            try:
                config = load_config("dummy_path.yaml")
                assert isinstance(config, GlocalConfig)
                assert not hasattr(config, "debug_options")
                assert not hasattr(config, "report_options")
                assert not hasattr(config.providers["gemini"], "batch_options")
                assert not hasattr(config.tasks[0], "regex_rewrites")
                assert not hasattr(config.tasks[0].output, "filename_suffix")
            except (AssertionError, AttributeError) as e:
                self.fail(f"Loading config with old fields failed unexpectedly: {e}")

    def test_load_config_double_quotes_fail(self) -> None:
        """7. Failure: Raises YAMLError when double quotes are used."""
        yaml_content = 'key: "value"'
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True), pytest.raises(yaml.YAMLError, match="Double-quoted string found"):
            load_config("dummy_path.yaml")

    def test_legacy_rules_parsing(self) -> None:
        """8. Logic: Correctly parses the old list-based rule format."""
        yaml_content = """
tasks:
  - name: 'Legacy Rules'
    source_lang: 'en'
    target_lang: 'fr'
    source:
      include: ['*.*']
    rules:
      - 'skip: ^SKIP'
      - 'protect: PROTECTED'
      - 'OLD -> NEW'
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True):
            config = load_config("dummy_path.yaml")
            task = config.tasks[0]
            assert len(task.rules) == 3
            actions = {r.action.action for r in task.rules}
            assert "skip" in actions
            assert "protect" in actions
            assert "replace" in actions

    def test_rules_extends(self) -> None:
        """9. Logic: Correctly resolves 'extends' within a rules block."""
        yaml_content = """
shortcuts:
  .base-rules:
    rules:
      replace:
        'base': 'correct'
  .feature-rules:
    rules:
      extends: '.base-rules'
      skip: ['feature_skip']
tasks:
  - name: 'Test Rules Extends'
    source_lang: 'en'
    target_lang: 'fr'
    source: {include: ['*.*']}
    rules:
      extends: '.feature-rules'
      protect: ['final_protect']
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True):
            config = load_config("dummy_path.yaml")
            task = config.tasks[0]
            assert len(task.rules) == 3
            actions = {r.action.action for r in task.rules}
            assert actions == {"replace", "skip", "protect"}

    def test_invalid_source_type_is_handled(self) -> None:
        """10. Logic: Handles invalid 'source' types gracefully."""
        yaml_content = """
tasks:
  - name: 'Invalid Source'
    source_lang: 'en'
    target_lang: 'fr'
    source: 123 # Invalid type
"""
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True):
            config = load_config("dummy_path.yaml")
            task = config.tasks[0]
            assert task.source == Source(include=[], exclude=[])

    def test_load_config_not_a_dict(self) -> None:
        """11. Failure: Raises TypeError if the YAML root is not a dictionary."""
        yaml_content = "- item1\n- item2"
        with patch("pathlib.Path.open", mock_open(read_data=yaml_content)), patch("pathlib.Path.is_file", return_value=True), pytest.raises(ValueError, match="Config file must be a YAML mapping"):
            load_config("dummy_path.yaml")


if __name__ == "__main__":
    unittest.main()
