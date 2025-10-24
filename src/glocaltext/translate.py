import logging
import os
from collections import defaultdict
from typing import Dict, List, Tuple

from .config import BatchOptions, GlocalConfig, Rule, TranslationTask
from .models import TextMatch
from .translators.base import BaseTranslator
from .translators.gemini_translator import GeminiTranslator
from .translators.google_translator import GoogleTranslator


def initialize_translators(config: GlocalConfig) -> Dict[str, BaseTranslator]:
    """Initializes all available translation providers based on the config."""
    translators: Dict[str, BaseTranslator] = {}

    # Initialize Gemini if configured
    gemini_settings = config.providers.get("gemini")
    if gemini_settings:
        # Prioritize API key from environment, then from config
        api_key = os.environ.get("GEMINI_API_KEY") or gemini_settings.api_key
        if api_key:
            try:
                # The model_name here is the GLOBAL default.
                translators["gemini"] = GeminiTranslator(
                    api_key=api_key,
                    model_name=gemini_settings.model or "gemini-1.0-pro",
                )
                gemini_translator = translators["gemini"]
                if isinstance(gemini_translator, GeminiTranslator):
                    logging.info(f"Gemini provider initialized with default model '{gemini_translator.model_name}'.")
            except Exception as e:
                logging.error(f"Failed to initialize Gemini provider: {e}")
        else:
            logging.warning("Gemini provider is configured but no API key was found in GEMINI_API_KEY environment variable or config.")

    # Always initialize Google as a fallback
    translators["google"] = GoogleTranslator()
    logging.info("Google (deep-translator) initialized as default fallback.")

    return translators


def _check_rule_match(text: str, rule: Rule) -> Tuple[bool, str | None]:
    """Checks if a text matches a given rule."""
    # Check for 'exact' match
    if rule.match.exact:
        conditions = [rule.match.exact] if isinstance(rule.match.exact, str) else rule.match.exact
        if text in conditions:
            return True, text

    # Check for 'contains' match
    if rule.match.contains:
        conditions = [rule.match.contains] if isinstance(rule.match.contains, str) else rule.match.contains
        for c in conditions:
            if c in text:
                return True, c

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
    if rule.action.value:
        modified_text = text.replace(matched_value, rule.action.value)
        logging.debug(f"Text modified by rule: '{text}' -> '{modified_text}'")
        return modified_text
    return text


def _handle_protect_action(text: str, matched_value: str, protected_map: Dict[str, str]) -> str:
    placeholder_key = f"__PROTECT_{len(protected_map)}__"
    protected_map[placeholder_key] = matched_value
    protected_text = text.replace(matched_value, placeholder_key)
    logging.debug(f"Protected text: '{matched_value}' replaced with '{placeholder_key}'")
    return protected_text


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
        text = _handle_protect_action(text, matched_value, protected_map)

    return text, is_handled


def _apply_pre_processing_rules(original_text: str, matches: List[TextMatch], task: TranslationTask) -> Tuple[str, Dict[str, str]]:
    """Applies non-terminating rules like 'protect' and 'modify'."""
    text_to_process = original_text
    protected_map: Dict[str, str] = {}
    for rule in task.rules:
        if rule.action.action in ["protect", "modify"]:
            text_to_process, _ = _handle_rule_action(text_to_process, matches, rule, protected_map)
    return text_to_process, protected_map


def _apply_terminating_rules(
    text_to_process: str,
    original_text: str,
    matches: List[TextMatch],
    task: TranslationTask,
) -> bool:
    """Applies terminating rules like 'skip' and 'replace'."""
    for rule in task.rules:
        if rule.action.action in ["skip", "replace"]:
            text_to_check = original_text if rule.match.exact else text_to_process
            _, is_handled = _handle_rule_action(text_to_check, matches, rule, {})
            if is_handled:
                return True
    return False


def _apply_translation_rules(unique_texts: Dict[str, List[TextMatch]], task: TranslationTask) -> Tuple[Dict[str, List[TextMatch]], Dict[str, Dict[str, str]], int]:
    """Applies translation rules by separating pre-processing and terminating actions."""
    skipped_count = 0
    texts_to_translate_api: Dict[str, List[TextMatch]] = {}
    protected_maps: Dict[str, Dict[str, str]] = {}

    for original_text, matches in unique_texts.items():
        text_to_process, protected_map = _apply_pre_processing_rules(original_text, matches, task)

        is_handled = _apply_terminating_rules(text_to_process, original_text, matches, task)

        if is_handled:
            skipped_count += 1
            continue

        if protected_map:
            protected_maps[text_to_process] = protected_map

        if text_to_process != original_text:
            texts_to_translate_api.setdefault(text_to_process, []).extend(matches)
        else:
            texts_to_translate_api[original_text] = matches

    return texts_to_translate_api, protected_maps, skipped_count


def _create_batches(texts: List[str], batch_options: BatchOptions) -> List[List[str]]:
    """Splits a list of texts into batches based on size."""
    if not batch_options.enabled or not texts:
        return [texts] if texts else []

    batches: List[List[str]] = []
    for i in range(0, len(texts), batch_options.batch_size):
        batches.append(texts[i : i + batch_options.batch_size])
    return batches


def _select_provider(task: TranslationTask, translators: Dict[str, BaseTranslator]) -> str:
    """Selects the translation provider based on task and availability."""
    # 1. Use task-specific translator if available and initialized.
    if task.translator and task.translator in translators:
        return task.translator
    # 2. Otherwise, fall back to a default provider.
    if "gemini" in translators:
        return "gemini"  # Prefer Gemini if available.
    return "google"  # Ultimate fallback.


def _translate_batch(
    translator: BaseTranslator,
    batch: List[str],
    task: TranslationTask,
    debug: bool,
    provider_name: str,
):
    """Helper to translate a single batch and handle errors."""
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
    """Restores placeholders in the translated text with their original protected values."""
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
    """Updates TextMatch objects on successful translation."""
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
    """Updates TextMatch objects on translation failure."""
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
    """Translates batches and updates the corresponding TextMatch objects."""
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
) -> int:
    """Processes all text matches for a given task, from bucketing to translation."""
    if not matches:
        return 0

    unique_texts: Dict[str, List[TextMatch]] = defaultdict(list)
    for match in matches:
        unique_texts[match.original_text].append(match)
    logging.info(f"Found {len(unique_texts)} unique text strings to process.")

    texts_to_translate_api, protected_maps, skipped_count = _apply_translation_rules(unique_texts, task)

    if not texts_to_translate_api:
        logging.info("All texts were handled by rules. No API call needed.")
        return skipped_count

    provider_name = _select_provider(task, translators)
    logging.info(f"Translator for task '{task.name}': '{provider_name}' (Task-specific: {task.translator or 'Not set'}).")

    translator = translators[provider_name]
    provider_settings = config.providers.get(provider_name)
    batch_options = provider_settings.batch_options if provider_settings else BatchOptions()

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

    return skipped_count
