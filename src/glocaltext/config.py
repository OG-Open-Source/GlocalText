from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import yaml


@dataclass
class ReportOptions:
    """Options for generating a summary report."""

    enabled: bool = True
    export_csv: bool = False
    export_dir: Optional[str] = None


@dataclass
class DebugOptions:
    """Options for debugging the translation process."""

    enabled: bool = False
    log_path: Optional[str] = None


@dataclass
class BatchOptions:
    """Batching settings for a provider."""

    enabled: bool = True
    batch_size: int = 20
    max_tokens_per_batch: int = 8000


@dataclass
class ProviderSettings:
    """Settings for a specific translation provider."""

    api_key: str | None = None
    model: str | None = None
    batch_options: BatchOptions = field(default_factory=BatchOptions)
    retry_attempts: Optional[int] = 3
    retry_delay: Optional[float] = 1.0
    retry_backoff_factor: Optional[float] = 2.0


@dataclass
class Providers:
    """Container for provider-specific settings."""

    gemini: Optional[ProviderSettings] = None
    mock: Optional[ProviderSettings] = None


@dataclass
class Output:
    """Defines the output behavior for a translation task."""

    in_place: bool = True
    path: str | None = None
    filename_suffix: Optional[str] = None
    filename: Optional[str] = None
    # The 'filename_prefix' is included for backward compatibility with older configs.
    # It will be handled and converted to 'filename_suffix' in __post_init__.
    filename_prefix: Optional[str] = None

    def __post_init__(self):
        """Handles backward compatibility and validates attributes."""
        # If 'filename_prefix' is provided, use it to populate 'filename_suffix'
        # to maintain backward compatibility.
        if self.filename_prefix is not None:
            if self.filename_suffix is None:
                self.filename_suffix = self.filename_prefix

        # Original validation logic
        if self.in_place and self.path is not None:
            raise ValueError("The 'path' attribute cannot be used when 'in_place' is True.")
        if not self.in_place and self.path is None:
            raise ValueError("The 'path' attribute is required when 'in_place' is False.")


@dataclass
class MatchRule:
    """Defines the matching criteria for a rule."""

    exact: Optional[Union[str, List[str]]] = None
    contains: Optional[Union[str, List[str]]] = None
    regex: Optional[Union[str, List[str]]] = None

    def __post_init__(self):
        """Validates that exactly one of 'exact', 'contains', or 'regex' is provided."""
        provided_rules = [self.exact, self.contains, self.regex]
        num_provided = sum(1 for rule in provided_rules if rule is not None)

        if num_provided == 0:
            raise ValueError("One of 'exact', 'contains', or 'regex' must be provided for a match rule.")
        if num_provided > 1:
            raise ValueError("'exact', 'contains', and 'regex' cannot be used simultaneously in a match rule.")


@dataclass
class ActionRule:
    """Defines the action to be taken when a rule matches."""

    action: Literal["skip", "replace", "modify", "protect"]
    value: Optional[str] = None

    def __init__(self, **kwargs):
        """Initializes the ActionRule with backward compatibility for 'type'."""
        # Provide backward compatibility for configs using 'type' instead of 'action'.
        if "type" in kwargs:
            kwargs["action"] = kwargs.pop("type")

        # Set attributes from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __post_init__(self):
        """Validates that 'value' is provided for actions that require it."""
        if self.action in ["replace", "modify"] and self.value is None:
            raise ValueError(f"The 'value' must be provided for the '{self.action}' action.")


@dataclass
class Rule:
    """A single rule combining a match condition and an action.
    This class is designed to be constructed from a dictionary,
    so the from_dict method in GlocalConfig will handle the nested instantiation.
    """

    match: MatchRule
    action: ActionRule

    def __init__(self, match: Dict[str, Any], action: Dict[str, Any]):
        self.match = MatchRule(**match)
        self.action = ActionRule(**action)


@dataclass
class Source:
    """Defines the source files for a translation task."""

    include: List[str] = field(default_factory=list)


@dataclass
class TranslationTask:
    """A single task defining what to translate and how."""

    name: str
    source_lang: str
    target_lang: str
    source: Source
    extraction_rules: List[str]
    translator: Optional[str] = None
    model: Optional[str] = None
    prompts: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    exclude: List[str] = field(default_factory=list)
    output: Output = field(default_factory=Output)
    rules: List[Rule] = field(default_factory=list)
    regex_rewrites: Dict[str, str] = field(default_factory=dict)
    incremental: bool = False
    cache_path: Optional[str] = None


@dataclass
class GlocalConfig:
    """The root configuration for GlocalText."""

    providers: Providers = field(default_factory=Providers)
    tasks: List[TranslationTask] = field(default_factory=list)
    debug_options: DebugOptions = field(default_factory=DebugOptions)
    report_options: ReportOptions = field(default_factory=ReportOptions)

    @staticmethod
    def _handle_manual_translations(task_data: Dict[str, Any]) -> List[Rule]:
        """Handles backward compatibility for 'manual_translations' and 'glossary'."""
        rules = []
        manual_translations = task_data.get("manual_translations", task_data.get("glossary", {}))
        for source, target in manual_translations.items():
            rules.append(Rule(match={"exact": source}, action={"action": "replace", "value": target}))
        return rules

    @staticmethod
    def _handle_keyword_replacements(task_data: Dict[str, Any]) -> List[Rule]:
        """Handles backward compatibility for 'keyword_replacements'."""
        rules = []
        keyword_replacements = task_data.get("keyword_replacements", {})
        for keyword, replacement in keyword_replacements.items():
            rules.append(Rule(match={"contains": keyword}, action={"action": "modify", "value": replacement}))
        return rules

    @staticmethod
    def _handle_skip_translations(task_data: Dict[str, Any], global_skip_translations: List[str]) -> List[Rule]:
        """Handles backward compatibility for 'skip_translations'."""
        rules = []
        task_skip = task_data.get("skip_translations", [])
        all_skips = set(global_skip_translations) | set(task_skip)
        for text in all_skips:
            rules.append(Rule(match={"exact": text}, action={"action": "skip"}))
        return rules

    @staticmethod
    def _apply_backward_compatibility_rules(task_data: Dict[str, Any], global_skip_translations: List[str]) -> List[Rule]:
        """
        Builds a list of rules from various legacy configuration fields.

        This is to ensure backward compatibility with older configuration formats that defined
        rules like glossaries, keyword replacements, and skip lists outside the main 'rules' list.
        """
        # Start with rules from the new 'rules' field
        rules = [Rule(**r) for r in task_data.get("rules", [])]

        # Define a list of backward compatibility rule handlers
        rule_handlers = [
            GlocalConfig._handle_manual_translations,
            GlocalConfig._handle_keyword_replacements,
        ]

        # Apply each handler to the task data
        for handler in rule_handlers:
            rules.extend(handler(task_data))

        # Handle skip translations, which also requires global skips
        rules.extend(GlocalConfig._handle_skip_translations(task_data, global_skip_translations))

        return rules

    @staticmethod
    def _prepare_source_data(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepares the source configuration, handling backward compatibility for the 'targets' key.

        In older versions, source files were defined under 'targets'. This function ensures
        they are correctly moved to 'source.include' for the new data model.
        """
        source_data = task_data.get("source", {})
        if "targets" in task_data:
            # If 'targets' exists, merge it into the 'include' list.
            # setdefault is used to avoid overwriting 'include' if it's already present in 'source'.
            source_data.setdefault("include", task_data["targets"])
        return source_data

    @staticmethod
    def _build_tasks_from_list(tasks_data: List[Dict[str, Any]], global_skip_translations: List[str]) -> List[TranslationTask]:
        """
        Builds a list of TranslationTask objects from a list of dictionaries.

        This function orchestrates the parsing of each task definition, delegating
        backward compatibility handling and data preparation to helper methods.
        """
        tasks = []
        for t in tasks_data:
            # Consolidate all rule definitions, including backward-compatible ones.
            # This keeps the task construction logic clean by handling legacy fields separately.
            rules = GlocalConfig._apply_backward_compatibility_rules(t, global_skip_translations)

            # Prepare the source data, handling legacy 'targets' field.
            # This isolates the logic for source file definition.
            source_data = GlocalConfig._prepare_source_data(t)

            tasks.append(
                TranslationTask(
                    name=t.get("name", "Unnamed Task"),
                    enabled=t.get("enabled", True),
                    source_lang=t["source_lang"],
                    target_lang=t["target_lang"],
                    source=Source(**source_data),
                    translator=t.get("translator"),
                    model=t.get("model"),
                    prompts=t.get("prompts", {}),
                    exclude=t.get("exclude", []),
                    extraction_rules=t.get("extraction_rules", []),
                    output=Output(**t.get("output", {})),
                    rules=rules,
                    regex_rewrites=t.get("regex_rewrites", {}),
                    incremental=t.get("incremental", False),
                    cache_path=t.get("cache_path"),
                )
            )
        return tasks

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlocalConfig":
        """Creates a GlocalConfig object from a dictionary, with validation."""
        providers_data = data.get("providers", {}) or {}

        def _parse_provider_settings(name: str) -> Optional[ProviderSettings]:
            if name not in providers_data:
                return None

            p_config = providers_data[name]
            if not isinstance(p_config, dict):
                # Handles case like `mock:` which parses to `None`
                p_config = {}

            if "batch_options" in p_config:
                p_config["batch_options"] = BatchOptions(**p_config.pop("batch_options", {}))

            return ProviderSettings(**p_config)

        providers = Providers(
            gemini=_parse_provider_settings("gemini"),
            mock=_parse_provider_settings("mock"),
        )

        tasks_data = data.get("tasks", [])
        global_skip_translations = data.get("skip_translations", [])
        tasks = cls._build_tasks_from_list(tasks_data, global_skip_translations)

        debug_options = DebugOptions(**data.get("debug_options", {}))
        report_options = ReportOptions(**data.get("report_options", {}))

        return cls(
            providers=providers,
            tasks=tasks,
            debug_options=debug_options,
            report_options=report_options,
        )


def load_config(config_path: str) -> GlocalConfig:
    """Loads, parses, and validates the YAML configuration file.

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
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise TypeError("Config file must be a YAML mapping (dictionary).")

        return GlocalConfig.from_dict(data)

    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML config file: {e}")
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Invalid or missing configuration: {e}")
