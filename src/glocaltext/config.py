"""Handles the parsing and validation of the GlocalText configuration file."""

import copy
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .types import ActionRule, MatchRule, Rule, TranslationTask


class ProviderSettings(BaseModel):
    """Settings for a specific translation provider."""

    api_key: str | None = None
    model: str | None = None
    max_tokens_per_batch: int | None = None
    batch_size: int | None = 20
    rpm: int | None = None
    tpm: int | None = None
    rpd: int | None = None
    retry_attempts: int | None = 3
    retry_delay: float | None = 1.0
    retry_backoff_factor: float | None = 2.0
    extra: dict[str, Any] | None = None


class GemmaProviderSettings(ProviderSettings):
    """Specific settings for the Gemma provider."""

    rpm: int | None = 30
    tpm: int | None = 15000
    rpd: int | None = 14400


# Dispatch map for provider-specific settings classes
PROVIDER_SETTINGS_MAP: dict[str, type[ProviderSettings]] = {
    "gemma": GemmaProviderSettings,
}


def _deep_merge(source: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    """
    Non-destructively merge two dictionaries.

    Source values overwrite destination values.
    Nested dictionaries (including 'rules') are merged recursively.
    """
    merged = copy.deepcopy(destination)
    for key, value in source.items():
        if isinstance(value, dict) and key in merged and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(value, merged[key])
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _resolve_shortcut_chain(current_config: dict[str, Any], shortcuts: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve the full inheritance chain of shortcuts."""
    alias_chain = []
    visited_aliases = set()
    current_alias = current_config.get("extends")

    while isinstance(current_alias, str) and current_alias not in visited_aliases and current_alias in shortcuts:
        visited_aliases.add(current_alias)
        shortcut_config = shortcuts[current_alias]
        alias_chain.append(shortcut_config)
        current_alias = shortcut_config.get("extends")

    return alias_chain


def _apply_shortcuts(task_config: dict[str, Any], shortcuts: dict[str, Any]) -> dict[str, Any]:
    """Apply shortcuts to a task configuration iteratively using an 'extends' key."""
    alias_chain = _resolve_shortcut_chain(task_config, shortcuts)

    # Start with global defaults, if they exist
    final_config = copy.deepcopy(shortcuts.get(".defaults", {}))

    # Merge from the base of the chain up to the more specific shortcuts
    for alias_config in reversed(alias_chain):
        final_config = _deep_merge(alias_config, final_config)

    # Finally, merge the original task config, which has the highest priority
    final_config = _deep_merge(task_config, final_config)

    final_config.pop("extends", None)
    return final_config


def _parse_simple_action_rules(patterns: str | list[str] | None, action_type: Literal["skip", "protect"]) -> list[Rule]:
    """Parse simple action rules (skip, protect) from a string or list."""
    if not patterns:
        return []

    if isinstance(patterns, str):
        patterns = [patterns]

    rules = []
    if isinstance(patterns, list):
        for pattern in patterns:
            if isinstance(pattern, str):
                rule = Rule(
                    match=MatchRule(regex=pattern),
                    action=ActionRule(action=action_type),
                )
                rules.append(rule)
    return rules


def _parse_rules_from_legacy_list(rules_list: list) -> dict[str, Any]:
    """Convert old list-based rule format to the new dictionary format."""
    skip_rules: list[str] = []
    protect_rules: list[str] = []
    replace_rules_map: dict[str, str] = {}
    for item in rules_list:
        if not isinstance(item, str):
            continue

        if "->" in item:
            pattern, replacement = (part.strip() for part in item.split("->", 1))
            replace_rules_map[pattern] = replacement
        elif ":" in item:
            action, pattern = (part.strip() for part in item.split(":", 1))
            action_lower = action.lower()
            if action_lower == "skip":
                skip_rules.append(pattern)
            elif action_lower == "protect":
                protect_rules.append(pattern)
    return {
        "skip": skip_rules,
        "protect": protect_rules,
        "replace": replace_rules_map,
    }


def _parse_rules(rules_data: dict[str, Any] | list) -> list[Rule]:
    """Parse rules from a dictionary (new format) or list (old format) into Rule objects."""
    rules_dict: dict[str, Any]

    # Handle backward compatibility for old list-based rule format
    if isinstance(rules_data, list):
        rules_dict = _parse_rules_from_legacy_list(rules_data)
    elif isinstance(rules_data, dict):
        rules_dict = rules_data
    else:
        # If it's neither a list nor a dict, there are no rules to parse.
        return []

    expanded_rules: list[Rule] = []

    # Handle single-action rules like 'skip' and 'protect'
    for action_type in ("skip", "protect"):
        patterns = rules_dict.get(action_type)
        expanded_rules.extend(_parse_simple_action_rules(patterns, action_type))

    # Handle 'replace' rules
    replace_rules = rules_dict.get("replace")
    if isinstance(replace_rules, dict):
        for pattern, replacement in replace_rules.items():
            rule = Rule(
                match=MatchRule(regex=pattern),
                action=ActionRule(action="replace", value=str(replacement)),
            )
            expanded_rules.append(rule)

    return expanded_rules


def _create_tasks_from_config(
    tasks_data: list[dict[str, Any]],
    shortcuts: dict[str, Any],
) -> list[TranslationTask]:
    """Build a list of TranslationTask objects from a list of dictionaries."""
    tasks = []
    # First, resolve shortcuts within the shortcuts themselves
    resolved_shortcuts = {}
    for name, shortcut_data in shortcuts.items():
        if name != ".defaults":
            resolved_shortcuts[name] = _apply_shortcuts(shortcut_data, shortcuts)
        else:
            resolved_shortcuts[name] = shortcut_data

    for task_data in tasks_data:
        config = _apply_shortcuts(task_data, resolved_shortcuts)

        rules_data = config.get("rules", {})
        config["rules"] = _parse_rules(rules_data)

        source_val = config.get("source")
        if isinstance(source_val, str):
            config["source"] = {"include": [source_val]}
        elif not isinstance(source_val, dict):
            config["source"] = {}

        tasks.append(TranslationTask(**config))
    return tasks


class GlocalConfig(BaseModel):
    """The root configuration for GlocalText."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    project_root: str | None = None
    providers: dict[str, ProviderSettings] = Field(default_factory=dict)
    shortcuts: dict[str, Any] = Field(default_factory=dict)
    tasks: list[TranslationTask] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GlocalConfig":
        """Create a GlocalConfig object from a dictionary, with validation for v2.1 format."""
        try:
            providers_data = data.get("providers", {})
            providers = _build_providers_from_dict(providers_data)

            shortcuts = data.get("shortcuts", {})

            tasks_data = data.get("tasks", [])
            tasks = _create_tasks_from_config(tasks_data, shortcuts)

            return cls(
                project_root=data.get("project_root"),
                providers=providers,
                shortcuts=shortcuts,
                tasks=tasks,
            )
        except ValidationError as e:
            msg = f"Invalid or missing configuration: {e}"
            raise ValueError(msg) from e


def _build_providers_from_dict(providers_data: dict[str, Any]) -> dict[str, ProviderSettings]:
    """Build a dictionary of ProviderSettings objects from a dictionary."""
    providers = {}
    for name, p_config in providers_data.items():
        config_data = p_config if isinstance(p_config, dict) else {}
        provider_class = PROVIDER_SETTINGS_MAP.get(name, ProviderSettings)
        providers[name] = provider_class(**config_data)
    return providers


def load_config(config_path: str) -> GlocalConfig:
    """
    Load, parse, and validate the YAML configuration file.

    Args:
        config_path: The path to the config.yaml file.

    Returns:
        A GlocalConfig object representing the validated configuration.

    Raises:
        FileNotFoundError: If the config file does not exist.
        yaml.YAMLError: If there is a syntax error in the YAML file.
        ValueError: If the configuration is invalid.

    """
    path = Path(config_path)
    if not path.is_file():
        msg = f"Configuration file not found at: {config_path}"
        raise FileNotFoundError(msg)

    def _raise_type_error(msg: str) -> None:
        """Raise a TypeError with a specific message."""
        raise TypeError(msg)

    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            _raise_type_error("Config file must be a YAML mapping (dictionary).")

        return GlocalConfig.from_dict(data)

    except yaml.YAMLError as e:
        msg = f"Error parsing YAML config file: {e}"
        raise yaml.YAMLError(msg) from e
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        msg = f"Invalid or missing configuration: {e}"
        raise ValueError(msg) from e
