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
    batch_size: int | None = None
    rpm: int | None = None
    tpm: int | None = None
    rpd: int | None = None
    retry_attempts: int | None = 3
    retry_delay: float | None = 5.0
    retry_backoff_factor: float | None = 2.0
    extra: dict[str, Any] | None = None


# Dispatch map for provider-specific settings classes
PROVIDER_SETTINGS_MAP: dict[str, type[ProviderSettings]] = {}


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


def _deep_merge_with_list_append(source: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    """
    Deeply merge two dictionaries.

    - Dictionaries are merged recursively.
    - Lists are combined (source items are prepended).
    - Other types from source overwrite destination.
    """
    merged = copy.deepcopy(destination)
    for key, value in source.items():
        dest_value = merged.get(key)
        if isinstance(value, dict) and isinstance(dest_value, dict):
            merged[key] = _deep_merge_with_list_append(value, dest_value)
        elif isinstance(value, list) and isinstance(dest_value, list):
            # Prepend source list to destination to give it priority
            merged[key] = value + dest_value
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _resolve_rules_extends(rules_data: dict[str, Any], shortcuts: dict[str, Any]) -> dict[str, Any]:
    """Resolve the 'extends' key within a 'rules' block and merge the rules."""
    if not isinstance(rules_data, dict) or "extends" not in rules_data:
        return rules_data

    # Make a copy to avoid modifying the original shortcut dicts
    rules_data = copy.deepcopy(rules_data)

    extended_aliases = rules_data.pop("extends", [])
    if isinstance(extended_aliases, str):
        extended_aliases = [extended_aliases]

    final_rules: dict[str, Any] = {}
    # Merge from the base of the chain up
    for alias in extended_aliases:
        shortcut_config = shortcuts.get(alias, {})
        shortcut_rules = shortcut_config.get("rules", {})
        # Recursively resolve extends in the parent first
        resolved_shortcut_rules = _resolve_rules_extends(shortcut_rules, shortcuts)
        final_rules = _deep_merge_with_list_append(resolved_shortcut_rules, final_rules)

    # Finally, merge the task-specific rules, which have the highest priority
    return _deep_merge_with_list_append(rules_data, final_rules)


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
        resolved_rules = _resolve_rules_extends(rules_data, resolved_shortcuts)
        config["rules"] = _parse_rules(resolved_rules)

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


class StrictSingleQuoteLoader(yaml.SafeLoader):
    """
    A custom YAML loader that enforces the use of single quotes for all strings.

    It raises an error if any double-quoted strings are found.
    """


def _construct_scalar(loader: StrictSingleQuoteLoader, node: yaml.ScalarNode) -> Any:  # noqa: ANN401
    """Construct a scalar node, but first check its style."""
    if node.style == '"':
        # Get line and column information for a helpful error message
        line = node.start_mark.line + 1
        col = node.start_mark.column + 1
        msg = f"Double-quoted string found at line {line}, column {col}. Please use single quotes (') instead."
        raise yaml.YAMLError(msg)
    return loader.construct_scalar(node)


# Add the custom constructor to the loader
StrictSingleQuoteLoader.add_constructor("tag:yaml.org,2002:str", _construct_scalar)


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
            data = yaml.load(f, Loader=StrictSingleQuoteLoader)  # noqa: S506

        if not isinstance(data, dict):
            _raise_type_error("Config file must be a YAML mapping (dictionary).")

        return GlocalConfig.from_dict(data)

    except yaml.YAMLError as e:
        msg = f"Error parsing YAML config file: {e}"
        raise yaml.YAMLError(msg) from e
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        msg = f"Invalid or missing configuration: {e}"
        raise ValueError(msg) from e
