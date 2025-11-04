"""Handles the parsing and validation of the GlocalText configuration file."""

import copy
import logging
import uuid
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruamel.yaml import YAML

from .types import ActionRule, MatchRule, Rule, TranslationTask

logger = logging.getLogger(__name__)


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


def _generate_stable_task_id(config: dict[str, Any]) -> str:
    """
    Generate a stable UUID v5 based on task's key characteristics.

    This ensures the same logical task always gets the same ID, even if the name changes.
    """
    # Create a deterministic hash from key task properties
    key_properties = {
        "source_lang": config.get("source_lang", ""),
        "target_lang": config.get("target_lang", ""),
        "source": config.get("source", {}),
        "extraction_rules": config.get("extraction_rules", []),
    }

    # Convert to a stable string representation
    stable_string = yaml.dump(key_properties, sort_keys=True, default_flow_style=False)

    # Generate UUID v5 using a namespace (DNS namespace is standard practice)
    namespace = uuid.NAMESPACE_DNS
    task_uuid = uuid.uuid5(namespace, stable_string)

    return str(task_uuid)


def _create_tasks_from_config(
    tasks_data: list[dict[str, Any]],
    shortcuts: dict[str, Any],
) -> tuple[list[TranslationTask], list[int]]:
    """
    Build a list of TranslationTask objects from a list of dictionaries.

    Returns:
        A tuple of (tasks, generated_indices) where generated_indices contains
        the indices of tasks that had their task_id auto-generated.

    """
    tasks = []
    generated_indices = []  # Track which tasks had task_id auto-generated

    # First, resolve shortcuts within the shortcuts themselves
    resolved_shortcuts = {}
    for name, shortcut_data in shortcuts.items():
        if name != ".defaults":
            resolved_shortcuts[name] = _apply_shortcuts(shortcut_data, shortcuts)
        else:
            resolved_shortcuts[name] = shortcut_data

    for idx, task_data in enumerate(tasks_data):
        config = _apply_shortcuts(task_data, resolved_shortcuts)

        rules_data = config.get("rules", {})
        resolved_rules = _resolve_rules_extends(rules_data, resolved_shortcuts)
        config["rules"] = _parse_rules(resolved_rules)

        source_val = config.get("source")
        if isinstance(source_val, str):
            config["source"] = {"include": [source_val]}
        elif not isinstance(source_val, dict):
            config["source"] = {}

        # Generate stable task_id if not provided (for better cache management)
        # Users can manually specify task_id in config to override this
        if "task_id" not in config or config["task_id"] is None:
            config["task_id"] = _generate_stable_task_id(config)
            generated_indices.append(idx)  # Mark this task as having generated task_id

        tasks.append(TranslationTask(**config))
    return tasks, generated_indices


class GlocalConfig(BaseModel):
    """The root configuration for GlocalText."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    providers: dict[str, ProviderSettings] = Field(default_factory=dict)
    shortcuts: dict[str, Any] = Field(default_factory=dict)
    tasks: list[TranslationTask] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> tuple["GlocalConfig", list[int]]:
        """
        Create a GlocalConfig object from a dictionary, with validation for v2.1 format.

        Returns:
            A tuple of (config, generated_indices) where generated_indices contains
            the indices of tasks that had their task_id auto-generated.

        """
        providers_data = data.get("providers", {})
        providers = _build_providers_from_dict(providers_data)

        shortcuts = data.get("shortcuts", {})

        tasks_data = data.get("tasks", [])
        tasks, generated_indices = _create_tasks_from_config(tasks_data, shortcuts)

        try:
            config = cls(
                providers=providers,
                shortcuts=shortcuts,
                tasks=tasks,
            )
        except ValidationError as e:
            msg = f"Invalid or missing configuration: {e}"
            raise ValueError(msg) from e
        else:
            return config, generated_indices


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


def _write_task_ids_to_config(
    config_path: Path,
    tasks: list[TranslationTask],
    generated_indices: list[int],
) -> None:
    """
    Write auto-generated task_ids back to the configuration file.

    This function uses ruamel.yaml to preserve the original formatting,
    comments, and structure of the YAML file.

    Args:
        config_path: Path to the configuration file
        tasks: List of TranslationTask objects with task_ids
        generated_indices: Indices of tasks that had their task_id auto-generated

    Note:
        Only updates tasks whose indices are in generated_indices.
        If the write fails, logs a warning but does not raise an exception
        to avoid disrupting the main workflow.

    """
    if not generated_indices:
        # No task_ids were generated, nothing to write
        return

    try:
        # Use ruamel.yaml to preserve formatting and comments
        yaml_handler = YAML()
        yaml_handler.preserve_quotes = True
        yaml_handler.default_flow_style = False

        # Read the current config file
        with config_path.open(encoding="utf-8") as f:
            config_data = yaml_handler.load(f)

        # Update only the tasks that had task_id generated
        if "tasks" in config_data and isinstance(config_data["tasks"], list):
            for idx in generated_indices:
                if idx < len(config_data["tasks"]) and idx < len(tasks):
                    # Add task_id to the config data
                    config_data["tasks"][idx]["task_id"] = tasks[idx].task_id
                    logger.info(
                        "Auto-generated task_id for task '%s': %s",
                        tasks[idx].name,
                        tasks[idx].task_id,
                    )

        # Write back to file
        with config_path.open("w", encoding="utf-8") as f:
            yaml_handler.dump(config_data, f)

        logger.info(
            "Successfully wrote %d task_id(s) back to %s",
            len(generated_indices),
            config_path,
        )

    except (OSError, ValueError, TypeError) as e:
        # Log warning but don't raise - this is a convenience feature, not critical
        logger.warning(
            "Failed to write task_ids back to config file %s: %s. This will not affect translation functionality.",
            config_path,
            e,
        )


def load_config(config_path: str) -> GlocalConfig:
    """
    Load, parse, and validate the YAML configuration file.

    This function will automatically write back any auto-generated task_ids
    to the configuration file for persistence across runs.

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

        # from_dict() returns (config, generated_indices)
        config, generated_indices = GlocalConfig.from_dict(data)

    except yaml.YAMLError as e:
        msg = f"Error parsing YAML config file: {e}"
        raise yaml.YAMLError(msg) from e
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        msg = f"Invalid or missing configuration: {e}"
        raise ValueError(msg) from e
    else:
        # Write back auto-generated task_ids to the config file
        _write_task_ids_to_config(path, config.tasks, generated_indices)
        return config
