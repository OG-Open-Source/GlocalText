# glocaltext/core/config.py

"""
Handles loading and validation of user configuration files (`i18n-rules.yaml`, `l10n-rules.yaml`)
using Pydantic models.
"""

import yaml
from pathlib import Path
from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel, Field, field_validator


class BaseConfig(BaseModel):
    @classmethod
    def from_yaml(cls, path: Path):
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file not found at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)


# ======================================================================================
# Models for i18n-rules.yaml
# ======================================================================================


class ExtractionRule(BaseModel):
    """Defines a regex pattern for extracting a string."""

    pattern: str
    capture_group: int = 1


class I18nSource(BaseModel):
    """Specifies which files to include and exclude for i18n."""

    include: List[str]
    exclude: List[str] = []


class ProtectionRule(BaseModel):
    """Defines a regex pattern for protecting parts of a string from translation."""

    pattern: str


class I18nConfig(BaseConfig):
    """Configuration for the internationalization (i18n) process."""

    source: I18nSource
    capture_rules: List[ExtractionRule]
    ignore_rules: List[ExtractionRule] = Field(default_factory=list)
    protection_rules: List[ProtectionRule] = Field(default_factory=list)

    @field_validator("capture_rules", "ignore_rules", "protection_rules", mode="before")
    @classmethod
    def convert_str_to_extraction_rule(cls, v: Any) -> Any:
        """Allow users to provide a simple list of strings for rules."""
        if not isinstance(v, list):
            return v  # Let default validation handle non-list types

        processed_rules = []
        for item in v:
            if isinstance(item, str):
                # If a simple string is provided, convert it to a dict
                # that matches the ExtractionRule model.
                processed_rules.append({"pattern": item})
            else:
                # If it's already a dict or something else, pass it through.
                processed_rules.append(item)
        return processed_rules


# ======================================================================================
# Models for l10n-rules.yaml
# ======================================================================================


class TranslationSettings(BaseModel):
    """General settings for the localization (l10n) process."""

    source_lang: str
    target_lang: List[str]
    provider: Literal["google", "gemini", "openai", "ollama"]


class GeminiPrompts(BaseModel):
    """Prompt templates for the Gemini provider."""

    system: str
    contxt: str


class GeminiConfig(BaseModel):
    """Configuration specific to the Gemini provider."""

    model: str
    api_key: Optional[str] = None
    prompts: Optional[GeminiPrompts] = None


class OpenAIPrompts(BaseModel):
    """Prompt templates for the OpenAI provider."""

    system: str
    contxt: str


class OpenAIConfig(BaseModel):
    """Configuration specific to the OpenAI provider."""

    model: str
    base_url: str
    api_key: str
    prompts: Optional[OpenAIPrompts] = None


class OllamaConfig(BaseModel):
    """Configuration specific to the Ollama provider."""

    model: str
    base_url: str = "http://localhost:11434"


class ProviderConfigs(BaseModel):
    """Container for all supported translation provider configurations."""

    gemini: Optional[GeminiConfig] = None
    openai: Optional[OpenAIConfig] = None
    ollama: Optional[OllamaConfig] = None


class L10nConfig(BaseConfig):
    """Configuration for the localization (l10n) process."""

    translation_settings: TranslationSettings
    provider_configs: Optional[ProviderConfigs] = Field(default_factory=ProviderConfigs)
    glossary: Optional[Dict[str, str]] = None
    glossary_file: Optional[str] = None


# ======================================================================================
# Main Config Container
# ======================================================================================


class Config(BaseModel):
    """Top-level container for all loaded configurations."""

    i18n: I18nConfig
    l10n: L10nConfig
