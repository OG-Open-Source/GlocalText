"""Tests for the GlocalText configuration loading and validation."""

from collections.abc import Callable

import pytest
import yaml
from pyfakefs.fake_filesystem import FakeFilesystem

from glocaltext.config import (
    ActionRule,
    GlocalConfig,
    MatchRule,
    Output,
    load_config,
)


@pytest.fixture
def create_config_file(fs: FakeFilesystem) -> Callable[[str, str], str]:
    """
    Create a fixture to create a config file on the fake filesystem.

    Args:
        fs: The pyfakefs filesystem fixture.

    Returns:
        A function to create a config file.

    """

    def _create_config_file(content: str, path: str) -> str:
        """Create a file with the given content and path."""
        fs.create_file(path, contents=content)
        return path

    return _create_config_file


# region: load_config Tests
def test_load_config_success(create_config_file: Callable[[str, str], str]) -> None:
    """Test loading a valid configuration file."""
    yaml_content = """
tasks:
  - name: "Translate Docs"
    source_lang: "en"
    target_lang: "fr"
    source:
      include: ["docs/**/*.md"]
    extraction_rules: ["markdown"]
"""
    config_path = create_config_file(yaml_content, "config.yaml")
    config = load_config(config_path)
    assert isinstance(config, GlocalConfig)
    assert len(config.tasks) == 1
    assert config.tasks[0].name == "Translate Docs"


def test_load_config_file_not_found() -> None:
    """Test that FileNotFoundError is raised for a non-existent file."""
    with pytest.raises(FileNotFoundError, match=r"Configuration file not found"):
        load_config("non_existent_config.yaml")


def test_load_config_invalid_yaml(create_config_file: Callable[[str, str], str]) -> None:
    """Test that YAMLError is raised for a malformed YAML file."""
    invalid_yaml = "tasks: [name: 'Test'"
    config_path = create_config_file(invalid_yaml, "config.yaml")
    with pytest.raises(yaml.YAMLError, match=r"Error parsing YAML config file"):
        load_config(config_path)


def test_load_config_not_a_dictionary(
    create_config_file: Callable[[str, str], str],
) -> None:
    """Test that a ValueError is raised if the config is not a dictionary."""
    yaml_content = "- item1\n- item2"
    config_path = create_config_file(yaml_content, "config.yaml")
    with pytest.raises(ValueError, match=r"Config file must be a YAML mapping"):
        load_config(config_path)


# endregion


# region: Dataclass and Pydantic Model Validation Tests
def test_output_validation_in_place_with_path() -> None:
    """Test ValueError is raised if 'in_place' is True and 'path' is provided."""
    with pytest.raises(
        ValueError,
        match=r"The 'path' attribute cannot be used when 'in_place' is True\.",
    ):
        Output(in_place=True, path="/some/path")


def test_output_validation_not_in_place_without_path() -> None:
    """Test ValueError is raised if 'in_place' is False and 'path' is not provided."""
    with pytest.raises(
        ValueError,
        match=r"The 'path' attribute is required when 'in_place' is False\.",
    ):
        Output(in_place=False)


def test_match_rule_validation_no_rule() -> None:
    """Test that ValueError is raised if no match rule is provided."""
    with pytest.raises(
        ValueError,
        match=r"One of 'exact', 'contains', or 'regex' must be provided",
    ):
        MatchRule()


def test_match_rule_validation_multiple_rules() -> None:
    """Test that ValueError is raised if multiple match rules are provided."""
    with pytest.raises(ValueError, match=r"cannot be used simultaneously"):
        MatchRule(exact="text", contains="more_text")


def test_action_rule_validation_value_missing() -> None:
    """Test ValueError is raised for 'replace' or 'modify' actions without 'value'."""
    with pytest.raises(ValueError, match=r"The 'value' must be provided for the 'replace' action\."):
        ActionRule(action="replace").__post_init__()

    with pytest.raises(ValueError, match=r"The 'value' must be provided for the 'modify' action\."):
        ActionRule(action="modify").__post_init__()


def test_glocal_config_pydantic_validation_error() -> None:
    """Test that Pydantic's ValidationError is caught and re-raised as ValueError."""
    invalid_data = {"tasks": [{"source_lang": "en"}]}  # Missing required fields
    with pytest.raises(ValueError, match=r"Invalid or missing configuration"):
        GlocalConfig.from_dict(invalid_data)


# endregion


# region: Backward Compatibility Tests
def test_backward_compatibility_output_filename_prefix() -> None:
    """Test backward compatibility for 'filename_prefix' in Output."""
    output = Output(filename_prefix="_old")
    assert output.filename_suffix == "_old"


def test_backward_compatibility_action_rule_type() -> None:
    """Test backward compatibility for 'type' in ActionRule."""
    action_rule = ActionRule(type="skip")
    assert action_rule.action == "skip"


def test_backward_compatibility_full_config(
    create_config_file: Callable[[str, str], str],
) -> None:
    """Test a config with multiple legacy fields."""
    legacy_batch_size = 15
    expected_rule_count = 3
    legacy_yaml = f"""
providers:
  gemma:
    batch_options:
      batch_size: {legacy_batch_size} # Legacy location for batch_size

tasks:
  - name: "Legacy Task"
    source_lang: "en"
    target_lang: "de"
    targets: ["legacy/path/**/*.txt"] # Legacy for source.include
    extraction_rules: ["text"]
    glossary: # Legacy for manual_translations/rules
      "Hello": "Hallo"
    keyword_replacements: # Legacy for rules
      "Apple": "Apfel"
    skip_translations: # Legacy for rules
      - "SKU123"
    output:
      filename_prefix: "_translated" # Legacy for filename_suffix
"""
    config_path = create_config_file(legacy_yaml, "config.yaml")
    config = load_config(config_path)

    # Test provider batch_size backward compatibility
    assert config.providers["gemma"].batch_size == legacy_batch_size

    # Test task-level backward compatibility
    task = config.tasks[0]
    assert task.source.include == ["legacy/path/**/*.txt"]
    assert task.output.filename_suffix == "_translated"

    # Test rule generation from legacy fields
    rules = task.rules
    assert len(rules) == expected_rule_count

    glossary_rule = next(r for r in rules if r.action.value == "Hallo")
    assert glossary_rule.match.exact == "Hello"
    assert glossary_rule.action.action == "replace"

    keyword_rule = next(r for r in rules if r.action.value == "Apfel")
    assert keyword_rule.match.contains == "Apple"
    assert keyword_rule.action.action == "modify"

    skip_rule = next(r for r in rules if r.action.action == "skip")
    assert skip_rule.match.exact == "SKU123"


def test_config_merging_and_overrides() -> None:
    """
    Test that provider settings override base settings and kwargs override file settings.

    This test verifies that:
    1. Provider-specific settings from the config file are correctly applied.
    2. Default values are used for settings not provided in the file.
    3. Config file values override default provider-specific values.
    """
    google_rpm = 50
    gemma_rpm = 100
    gemma_tpm = 15000
    data = {
        "providers": {
            "google": {"api_key": "google_key_from_file", "rpm": google_rpm},
            "gemma": {
                "api_key": "gemma_key_from_file",
                "rpm": gemma_rpm,
            },
        }
    }
    config = GlocalConfig.from_dict(data)

    # Test base provider setting
    assert config.providers["google"].api_key == "google_key_from_file"
    assert config.providers["google"].rpm == google_rpm

    # Test that the value from the config overrides the Gemma-specific default
    assert config.providers["gemma"].api_key == "gemma_key_from_file"
    # The value from the config (100) should override the default (30)
    assert config.providers["gemma"].rpm == gemma_rpm
    assert config.providers["gemma"].tpm == gemma_tpm  # Default from GemmaProviderSettings


# endregion
