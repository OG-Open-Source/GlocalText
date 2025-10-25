import logging
import os
from collections import defaultdict
from typing import Dict, List, Tuple

import regex

from .config import BatchOptions, GlocalConfig, Rule, TranslationTask
from .models import TextMatch
from .translators.base import BaseTranslator
from .translators.gemini_translator import GeminiTranslator
from .translators.google_translator import GoogleTranslator
from .translators.mock_translator import MockTranslator


def initialize_translators(config: GlocalConfig) -> Dict[str, BaseTranslator]:
    """Initializes all available translation providers based on the config."""
    translators: Dict[str, BaseTranslator] = {}

    # Initialize Gemini if configured
    if config.providers.gemini:
        api_key = os.environ.get("GEMINI_API_KEY") or config.providers.gemini.api_key
        if api_key:
            try:
                translators["gemini"] = GeminiTranslator(
                    api_key=api_key,
                    model_name=config.providers.gemini.model or "gemini-1.0-pro",
                )
                gemini_translator = translators["gemini"]
                if isinstance(gemini_translator, GeminiTranslator):
                    logging.info(f"Gemini provider initialized with default model '{gemini_translator.model_name}'.")
            except Exception as e:
                logging.error(f"Failed to initialize Gemini provider: {e}")
        else:
            logging.warning("Gemini provider is configured in glocaltext_config.yaml but no API key was found in the GEMINI_API_KEY environment variable or the config file. It will be unavailable.")

    # Initialize Mock if configured
    if config.providers.mock is not None:
        translators["mock"] = MockTranslator()
        logging.info("Mock provider initialized.")

    # Always initialize Google as a fallback
    if "google" not in translators:
        translators["google"] = GoogleTranslator()
        logging.info("Google (deep-translator) initialized as a fallback provider.")

    return translators


def _check_exact_match(text: str, rule: Rule) -> Tuple[bool, str | None]:
    """Checks for an exact match."""
    if not rule.match.exact:
        return False, None
    conditions = [rule.match.exact] if isinstance(rule.match.exact, str) else rule.match.exact
    if text in conditions:
        return True, text
    return False, None


def _check_contains_match(text: str, rule: Rule) -> Tuple[bool, str | None]:
    """Checks for a contains match."""
    if not rule.match.contains:
        return False, None
    conditions = [rule.match.contains] if isinstance(rule.match.contains, str) else rule.match.contains
    for c in conditions:
        if c in text:
            return True, c
    return False, None


def _check_regex_match(text: str, rule: Rule) -> Tuple[bool, str | None]:
    """Checks for a regex match."""
    if not rule.match.regex:
        return False, None
    conditions = [rule.match.regex] if isinstance(rule.match.regex, str) else rule.match.regex
    for r in conditions:
        try:
            if regex.search(r, text, regex.DOTALL):
                return True, r
        except regex.error as e:
            logging.warning(f"Invalid regex '{r}' in rule: {e}")
    return False, None


def _check_rule_match(text: str, rule: Rule) -> Tuple[bool, str | None]:
    """Checks if a text matches a given rule by delegating to specific match-type functions."""
    is_match, matched_value = _check_exact_match(text, rule)
    if is_match:
        return True, matched_value

    is_match, matched_value = _check_contains_match(text, rule)
    if is_match:
        return True, matched_value

    is_match, matched_value = _check_regex_match(text, rule)
    if is_match:
        return True, matched_value

    return False, None


def _handle_skip_action(matches: List[TextMatch], rule: Rule, text: str) -> bool:
    if rule.match.exact and text != matches[0].original_text:
        match_found_orig, _ = _check_rule_match(matches[0].original_text, rule)
        if not match_found_orig:
            return False
    for match in matches:
        match.provider = "skipped"
    return True


def _handle_replace_action(matches: List[TextMatch], rule: Rule) -> bool:
    for match in matches:
        match.translated_text = rule.action.value
        match.provider = "rule"
    return True


def _handle_modify_action(text: str, matched_value: str, rule: Rule) -> str:
    if rule.action.value is None:
        return text
    if rule.match.regex:
        try:
            modified_text = regex.sub(matched_value, rule.action.value, text, regex.DOTALL)
            logging.debug(f"Text modified by regex rule: '{text}' -> '{modified_text}'")
            return modified_text
        except regex.error as e:
            logging.warning(f"Invalid regex substitution with pattern '{matched_value}': {e}")
            return text
    modified_text = text.replace(matched_value, rule.action.value)
    logging.debug(f"Text modified by rule: '{text}' -> '{modified_text}'")
    return modified_text


def _apply_protection(text: str, matched_value: str, rule: Rule, protected_map: Dict[str, str]) -> str:
    """Applies protection to the text based on the rule's matched value."""
    if not rule.match.regex:
        # Handles 'exact' and 'contains' matches.
        # The 'matched_value' is the exact substring to protect.
        if matched_value not in protected_map.values():
            placeholder_key = f"__PROTECT_{len(protected_map)}__"
            protected_map[placeholder_key] = matched_value
            logging.debug(f"Protected text: '{matched_value}' replaced with '{placeholder_key}'")
        # If it's already in the map, find the placeholder to use for replacement
        placeholder = next((k for k, v in protected_map.items() if v == matched_value), None)
        return text.replace(matched_value, placeholder) if placeholder else text

    # Handles 'regex' matches.
    try:
        new_text = ""
        last_end = 0
        # 'matched_value' is the regex pattern string.
        for m in regex.finditer(matched_value, text, regex.DOTALL):
            original_substring = m.group(0)

            # Find existing placeholder or create a new one.
            placeholder = next((k for k, v in protected_map.items() if v == original_substring), None)
            if not placeholder:
                placeholder = f"__PROTECT_{len(protected_map)}__"
                protected_map[placeholder] = original_substring

            new_text += text[last_end : m.start()] + placeholder
            last_end = m.end()

        new_text += text[last_end:]
        return new_text
    except regex.error as e:
        logging.warning(f"Error during regex protection for pattern '{matched_value}': {e}")
        return text


def _handle_rule_action(
    text: str,
    matches: List[TextMatch],
    rule: Rule,
    protected_map: Dict[str, str],
) -> Tuple[str, bool]:
    """Dispatches a rule action to the appropriate handler."""
    match_found, matched_value = _check_rule_match(text, rule)
    if not match_found or not matched_value:
        return text, False

    action = rule.action.action
    is_handled = False

    if action == "skip":
        is_handled = _handle_skip_action(matches, rule, text)
    elif action == "replace":
        is_handled = _handle_replace_action(matches, rule)
    elif action == "modify":
        text = _handle_modify_action(text, matched_value, rule)
    elif action == "protect":
        text = _apply_protection(text, matched_value, rule, protected_map)

    return text, is_handled


def _apply_pre_processing_rules(original_text: str, matches: List[TextMatch], task: TranslationTask) -> Tuple[str, Dict[str, str]]:
    text_to_process = original_text
    protected_map: Dict[str, str] = {}

    modify_rules = [r for r in task.rules if r.action.action == "modify"]
    for rule in modify_rules:
        text_to_process, _ = _handle_rule_action(text_to_process, matches, rule, protected_map)

    protect_rules = [r for r in task.rules if r.action.action == "protect"]
    for rule in protect_rules:
        text_to_process, _ = _handle_rule_action(text_to_process, matches, rule, protected_map)

    return text_to_process, protected_map


def apply_terminating_rules(
    matches: List[TextMatch],
    task: TranslationTask,
) -> Tuple[List[TextMatch], List[TextMatch]]:
    unhandled_matches: List[TextMatch] = []
    terminated_matches: List[TextMatch] = []
    terminating_rules = [r for r in task.rules if r.action.action in ["skip", "replace"]]

    if not terminating_rules:
        return matches, []

    for match in matches:
        is_handled = False
        for rule in terminating_rules:
            text_to_check = match.original_text
            _, is_handled_by_rule = _handle_rule_action(text_to_check, [match], rule, {})
            if is_handled_by_rule:
                is_handled = True
                break
        if is_handled:
            terminated_matches.append(match)
        else:
            unhandled_matches.append(match)

    return unhandled_matches, terminated_matches


def _apply_translation_rules(unique_texts: Dict[str, List[TextMatch]], task: TranslationTask) -> Tuple[Dict[str, List[TextMatch]], Dict[str, Dict[str, str]]]:
    texts_to_translate_api: Dict[str, List[TextMatch]] = {}
    protected_maps: Dict[str, Dict[str, str]] = {}

    for original_text, matches in unique_texts.items():
        text_to_process, protected_map = _apply_pre_processing_rules(original_text, matches, task)
        if text_to_process in texts_to_translate_api:
            texts_to_translate_api[text_to_process].extend(matches)
        else:
            texts_to_translate_api[text_to_process] = matches
        if protected_map:
            protected_maps[text_to_process] = protected_map

    return texts_to_translate_api, protected_maps


def _create_batches(texts: List[str], batch_options: BatchOptions) -> List[List[str]]:
    if not batch_options.enabled or not texts:
        return [texts] if texts else []
    batches: List[List[str]] = []
    for i in range(0, len(texts), batch_options.batch_size):
        batches.append(texts[i : i + batch_options.batch_size])
    return batches


def _select_provider(task: TranslationTask, translators: Dict[str, BaseTranslator]) -> str:
    """Selects the translation provider based on task and availability, with robust fallbacks."""
    # 1. Use task-specific translator if specified.
    if task.translator:
        if task.translator in translators:
            return task.translator
        else:
            logging.warning(f"Task '{task.name}' specified translator '{task.translator}', but it is not available. Check your configuration and API keys. Falling back to default provider.")

    # 2. Otherwise, fall back to a default provider in a preferred order.
    if "gemini" in translators:
        return "gemini"
    if "mock" in translators:
        return "mock"
    return "google"


def _translate_batch(
    translator: BaseTranslator,
    batch: List[str],
    task: TranslationTask,
    debug: bool,
    provider_name: str,
):
    try:
        return translator.translate(
            texts=batch,
            target_language=task.target_lang,
            source_language=task.source_lang,
            debug=debug,
            prompts=task.prompts,
        )
    except Exception as e:
        logging.error(f"Error translating batch with {provider_name}: {e}")
        return None


def _restore_protected_text(translated_text: str, protected_map: Dict[str, str]) -> str:
    for placeholder, original_word in protected_map.items():
        translated_text = translated_text.replace(placeholder, original_word)
    return translated_text


def _update_matches_on_success(
    batch: List[str],
    translated_results: list,
    texts_to_translate_api: Dict[str, List[TextMatch]],
    provider_name: str,
    protected_maps: Dict[str, Dict[str, str]],
):
    for original_text, result in zip(batch, translated_results):
        protected_map = protected_maps.get(original_text, {})
        restored_text = _restore_protected_text(result.translated_text, protected_map)
        for match in texts_to_translate_api[original_text]:
            match.translated_text = restored_text
            match.provider = provider_name
            if result.tokens_used is not None:
                match.tokens_used = (match.tokens_used or 0) + result.tokens_used


def _update_matches_on_failure(
    batch: List[str],
    texts_to_translate_api: Dict[str, List[TextMatch]],
    provider_name: str,
):
    for original_text in batch:
        for match in texts_to_translate_api[original_text]:
            match.provider = f"error_{provider_name}"


def _translate_and_update_matches(
    translator: BaseTranslator,
    batches: List[List[str]],
    texts_to_translate_api: Dict[str, List[TextMatch]],
    task: TranslationTask,
    config: GlocalConfig,
    provider_name: str,
    protected_maps: Dict[str, Dict[str, str]],
):
    for i, batch in enumerate(batches):
        if not batch:
            continue
        logging.info(f"Translating batch {i + 1}/{len(batches)} ({len(batch)} unique texts) using '{provider_name}'.")
        translated_results = _translate_batch(translator, batch, task, config.debug_options.enabled, provider_name)
        if translated_results:
            _update_matches_on_success(
                batch,
                translated_results,
                texts_to_translate_api,
                provider_name,
                protected_maps,
            )
        else:
            _update_matches_on_failure(batch, texts_to_translate_api, provider_name)


def process_matches(
    matches: List[TextMatch],
    translators: Dict[str, BaseTranslator],
    task: TranslationTask,
    config: GlocalConfig,
):
    if not matches:
        return
    unique_texts: Dict[str, List[TextMatch]] = defaultdict(list)
    for match in matches:
        unique_texts[match.original_text].append(match)
    logging.info(f"Found {len(unique_texts)} unique text strings to process for API translation.")
    texts_to_translate_api, protected_maps = _apply_translation_rules(unique_texts, task)
    if not texts_to_translate_api:
        logging.info("All texts were handled by pre-processing or were empty. No API call needed.")
        return
    provider_name = _select_provider(task, translators)
    logging.info(f"Translator for task '{task.name}': '{provider_name}' (Task-specific: {task.translator or 'Not set'}).")
    translator = translators[provider_name]

    # Correctly getting provider settings
    provider_settings = getattr(config.providers, provider_name, None)
    batch_options = provider_settings.batch_options if provider_settings and hasattr(provider_settings, "batch_options") else BatchOptions()

    batches = _create_batches(list(texts_to_translate_api.keys()), batch_options)
    _translate_and_update_matches(
        translator,
        batches,
        texts_to_translate_api,
        task,
        config,
        provider_name,
        protected_maps,
    )
