"""Handles the parsing and validation of the GlocalText configuration file."""

import copy
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .types import Rule, TranslationTask


class ReportOptions(BaseModel):
    """Options for generating a summary report."""

    enabled: bool = True
    export_csv: bool = False
    export_dir: str | None = None


class DebugOptions(BaseModel):
    """Options for debugging the translation process."""

    enabled: bool = False
    log_path: str | None = None


class BatchOptions(BaseModel):
    """Batching settings for a provider."""

    enabled: bool = True
    max_tokens_per_batch: int = 8000


class ProviderSettings(BaseModel):
    """Settings for a specific translation provider."""

    api_key: str | None = None
    model: str | None = None
    batch_options: BatchOptions = Field(default_factory=BatchOptions)
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
    'rules' lists are merged with destination rules first, then source rules.
    """
    merged = copy.deepcopy(destination)
    for key, value in source.items():
        if key == "rules" and key in merged and isinstance(value, list):
            # Base rules first, then specific rules
            merged[key].extend(copy.deepcopy(value))
        elif isinstance(value, dict) and key in merged and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(value, merged[key])
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _parse_rule_from_string(rule_str: str) -> dict[str, Any]:
    """
    Parse a rule string into a dictionary representation of a Rule.

    All match patterns are treated as regular expressions.
    """
    if "->" in rule_str:
        pattern, replace_str = [s.strip().strip('"') for s in rule_str.split("->", 1)]
        return {"match": {"regex": pattern}, "action": {"action": "replace", "value": replace_str}}

    if ":" in rule_str:
        action, pattern = [s.strip() for s in rule_str.split(":", 1)]
        action = action.lower()
        pattern = pattern.strip('"')

        if action in ("skip", "protect"):
            return {"match": {"regex": pattern}, "action": {"action": action}}

        msg = f"Unknown rule action: {action}"
        raise ValueError(msg)

    msg = f"Invalid rule format: {rule_str}"
    raise ValueError(msg)


def _apply_shortcuts(task_config: dict[str, Any], shortcuts: dict[str, Any]) -> dict[str, Any]:
    """Apply shortcuts to a task configuration iteratively using an 'extends' key."""
    # Resolve the full inheritance chain first
    alias_chain = []
    current_config = task_config
    visited_aliases = set()

    while (alias_name := current_config.get("extends")) and isinstance(alias_name, str):
        if alias_name in visited_aliases:
            break  # Circular dependency detected
        if alias_name in shortcuts:
            visited_aliases.add(alias_name)
            shortcut_config = shortcuts[alias_name]
            alias_chain.append(shortcut_config)
            current_config = shortcut_config
        else:
            break

    # Start with global defaults, if they exist
    final_config = copy.deepcopy(shortcuts.get(".defaults", {}))

    # Merge from the base of the chain up to the more specific shortcuts
    for alias_config in reversed(alias_chain):
        final_config = _deep_merge(alias_config, final_config)

    # Finally, merge the original task config, which has the highest priority
    final_config = _deep_merge(task_config, final_config)

    final_config.pop("extends", None)
    return final_config


def _process_dict_rule(rule_dict: dict[str, Any], rulesets: dict[str, Any]) -> list[dict[str, Any]]:
    """Process a rule item that is a dictionary, expanding rulesets if necessary."""
    ruleset_name = rule_dict.get("ruleset")
    if isinstance(ruleset_name, str):
        if ruleset_name in rulesets:
            return [_parse_rule_from_string(r_str) for r_str in rulesets[ruleset_name]]
        return []  # Ruleset not found, ignore.
    return [rule_dict]  # Not a ruleset, treat as a single rule.


def _expand_rules(rules_data: list[Any], rulesets: dict[str, Any]) -> list[Rule]:
    """Expand rules from strings and rulesets into Rule objects."""
    if not isinstance(rules_data, list):
        return []

    expanded_rules: list[dict[str, Any]] = []
    for rule_item in rules_data:
        if isinstance(rule_item, str):
            expanded_rules.append(_parse_rule_from_string(rule_item))
        elif isinstance(rule_item, dict):
            expanded_rules.extend(_process_dict_rule(rule_item, rulesets))

    return [Rule(**r) for r in expanded_rules]


def _create_tasks_from_config(
    tasks_data: list[dict[str, Any]],
    shortcuts: dict[str, Any],
    rulesets: dict[str, Any],
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

        rules_data = config.get("rules", [])
        config["rules"] = _expand_rules(rules_data, rulesets)

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
    rulesets: dict[str, Any] = Field(default_factory=dict)
    tasks: list[TranslationTask] = Field(default_factory=list)
    debug_options: DebugOptions = Field(default_factory=DebugOptions)
    report_options: ReportOptions = Field(default_factory=ReportOptions)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GlocalConfig":
        """Create a GlocalConfig object from a dictionary, with validation for v2.1 format."""
        try:
            providers_data = data.get("providers", {})
            providers = _build_providers_from_dict(providers_data)
            debug_options, report_options = _parse_system_settings(data)

            shortcuts = data.get("shortcuts", {})
            rulesets = data.get("rulesets", {})

            tasks_data = data.get("tasks", [])
            tasks = _create_tasks_from_config(tasks_data, shortcuts, rulesets)

            return cls(
                project_root=data.get("project_root"),
                providers=providers,
                shortcuts=shortcuts,
                rulesets=rulesets,
                tasks=tasks,
                debug_options=debug_options,
                report_options=report_options,
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


def _parse_system_settings(
    data: dict[str, Any],
) -> tuple[DebugOptions, ReportOptions]:
    """Parse system-wide settings like debug and report options."""
    debug_options = DebugOptions(**data.get("debug_options", {}))
    report_options = ReportOptions(**data.get("report_options", {}))
    return debug_options, report_options


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
    except (KeyError, TypeError, ValueError) as e:
        msg = f"Invalid or missing configuration: {e}"
        raise ValueError(msg) from e
