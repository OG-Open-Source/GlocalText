import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import regex

from .config import GlocalConfig, ProviderSettings, Rule, TranslationTask
from .models import TextMatch
from .translators import TRANSLATOR_MAPPING
from .translators.base import BaseTranslator

logger = logging.getLogger(__name__)

# A cache to store initialized translator instances to avoid re-creating them.
_translator_cache: Dict[str, BaseTranslator] = {}
# A session-level counter for requests-per-day limits.
_rpd_session_counts: Dict[str, int] = defaultdict(int)


def _get_translator(provider_name: str, settings: Optional[ProviderSettings]) -> Optional[BaseTranslator]:
    """
    Instantiates a translator class based on the provider name and settings.

    This function acts as a factory, retrieving the correct translator class
    from a central mapping and initializing it with the provided settings.
    It includes a try-except block to gracefully handle initialization
    errors, such as missing API keys.

    Args:
        provider_name: The name of the provider (e.g., "gemini", "google").
        settings: The provider-specific settings object from the main config.

    Returns:
        An initialized translator instance, or None if instantiation fails.
    """
    translator_class = TRANSLATOR_MAPPING.get(provider_name)
    if not translator_class:
        logger.warning(f"Unknown translator provider: '{provider_name}'")
        return None

    try:
        # The translator's __init__ is responsible for parsing its settings
        # and raising ValueError if they are incomplete.
        return translator_class(settings=settings)
    except Exception as e:
        # Catches both ValueError for incomplete settings and other unexpected errors.
        logger.warning(f"Could not initialize translator '{provider_name}': {e}")
        return None


def get_translator(provider_name: str, config: GlocalConfig) -> Optional[BaseTranslator]:
    """
    Retrieves an initialized translator instance, using a cache to avoid re-initialization.

    Args:
        provider_name: The name of the provider to retrieve.
        config: The global configuration object.

    Returns:
        An initialized and cached translator instance, or None if it fails.
    """
    if provider_name in _translator_cache:
        return _translator_cache[provider_name]

    provider_settings = getattr(config.providers, provider_name, None)

    translator = _get_translator(provider_name, provider_settings)

    if translator:
        _translator_cache[provider_name] = translator
        logger.info(f"Provider '{provider_name}' initialized.")

    return translator


def _check_exact_match(text: str, rule: Rule) -> Tuple[bool, str | None]:
    """
    Check if the text exactly matches one of the conditions in the rule.

    Args:
        text: The text to check.
        rule: The rule containing the match conditions.

    Returns:
        A tuple containing a boolean indicating if a match was found,
        and the matched value if found.
    """
    if not rule.match.exact:
        return False, None
    conditions = [rule.match.exact] if isinstance(rule.match.exact, str) else rule.match.exact
    if text in conditions:
        return True, text
    return False, None


def _check_contains_match(text: str, rule: Rule) -> Tuple[bool, str | None]:
    """
    Check if the text contains one of the substrings specified in the rule.

    Args:
        text: The text to check.
        rule: The rule containing the match conditions.

    Returns:
        A tuple containing a boolean indicating if a match was found,
        and the matched value if found.
    """
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
            logger.warning(f"Invalid regex '{r}' in rule: {e}")
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
            logger.debug(f"Text modified by regex rule: '{text}' -> '{modified_text}'")
            return modified_text
        except regex.error as e:
            logger.warning(f"Invalid regex substitution with pattern '{matched_value}': {e}")
            return text
    modified_text = text.replace(matched_value, rule.action.value)
    logger.debug(f"Text modified by rule: '{text}' -> '{modified_text}'")
    return modified_text


def _apply_simple_protection(text: str, matched_value: str, protected_map: Dict[str, str]) -> str:
    """Applies protection for 'exact' and 'contains' matches."""
    if matched_value not in protected_map.values():
        placeholder_key = f"__PROTECT_{len(protected_map)}__"
        protected_map[placeholder_key] = matched_value
        logger.debug(f"Protected text: '{matched_value}' replaced with '{placeholder_key}'")

    placeholder = next((k for k, v in protected_map.items() if v == matched_value), None)
    return text.replace(matched_value, placeholder) if placeholder else text


def _apply_regex_protection(text: str, matched_value: str, protected_map: Dict[str, str]) -> str:
    """Applies protection for 'regex' matches."""
    try:
        new_text = ""
        last_end = 0
        for m in regex.finditer(matched_value, text, regex.DOTALL):
            original_substring = m.group(0)

            placeholder = next((k for k, v in protected_map.items() if v == original_substring), None)
            if not placeholder:
                placeholder = f"__PROTECT_{len(protected_map)}__"
                protected_map[placeholder] = original_substring

            new_text += text[last_end : m.start()] + placeholder
            last_end = m.end()

        new_text += text[last_end:]
        return new_text
    except regex.error as e:
        logger.warning(f"Error during regex protection for pattern '{matched_value}': {e}")
        return text


def _apply_protection(text: str, matched_value: str, rule: Rule, protected_map: Dict[str, str]) -> str:
    """Applies protection to the text based on the rule's matched value."""
    if rule.match.regex:
        return _apply_regex_protection(text, matched_value, protected_map)
    else:
        return _apply_simple_protection(text, matched_value, protected_map)


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


def _log_oversized_batch_warning(
    translator: BaseTranslator,
    batch: List[str],
    tpm: int,
    prompts: Optional[Dict[str, str]],
):
    """Checks and logs a warning if a single-item batch exceeds the TPM limit."""
    single_item_tokens = translator.count_tokens(batch, prompts)
    if single_item_tokens > tpm:
        logger.warning(
            f"A single text item ({single_item_tokens} tokens) exceeds the TPM limit ({tpm}). "
            "It will be sent in an oversized batch. This may cause API errors."
        )


def _create_simple_batches(texts_to_translate: List[str], batch_size: int) -> List[List[str]]:
    """Creates simple, size-based batches."""
    if not texts_to_translate:
        return []
    effective_batch_size = batch_size if batch_size > 0 else len(texts_to_translate)
    if not effective_batch_size:
        return []
    return [texts_to_translate[i : i + effective_batch_size] for i in range(0, len(texts_to_translate), effective_batch_size)]


def _create_smart_batches(
    translator: BaseTranslator,
    texts_to_translate: List[str],
    batch_size: int,
    tpm: int,
    prompts: Optional[Dict[str, str]],
) -> List[List[str]]:
    """Creates smart batches considering size and token limits."""
    batches: List[List[str]] = []
    current_batch: List[str] = []

    for text in texts_to_translate:
        if not current_batch:
            current_batch.append(text)
            _log_oversized_batch_warning(translator, current_batch, tpm, prompts)
        else:
            predicted_batch = current_batch + [text]
            predicted_tokens = translator.count_tokens(predicted_batch, prompts)

            if len(predicted_batch) <= batch_size and predicted_tokens <= tpm:
                current_batch = predicted_batch
            else:
                batches.append(current_batch)
                current_batch = [text]
                _log_oversized_batch_warning(translator, current_batch, tpm, prompts)

    if current_batch:
        batches.append(current_batch)

    return batches


def _create_batches(
    translator: BaseTranslator,
    texts_to_translate: List[str],
    batch_size: int,
    tpm: Optional[int],
    prompts: Optional[Dict[str, str]],
) -> List[List[str]]:
    """Creates smart batches by delegating to simple or smart batching strategies."""
    provider_settings = translator.settings
    if not provider_settings or not provider_settings.batch_options.enabled or tpm is None:
        return _create_simple_batches(texts_to_translate, batch_size)

    if not texts_to_translate:
        return []

    return _create_smart_batches(translator, texts_to_translate, batch_size, tpm, prompts)


def _select_provider(task: TranslationTask, available_providers: List[str]) -> str:
    """Selects the translation provider based on task and availability, with robust fallbacks."""
    # 1. Use task-specific translator if specified.
    if task.translator:
        if task.translator in available_providers:
            return task.translator
        else:
            logger.warning(f"Task '{task.name}' specified translator '{task.translator}', but it is not available. Check your configuration. Falling back to default provider.")

    # 2. Otherwise, fall back to a default provider in a preferred order.
    preferred_order = ["gemini", "mock", "google"]
    for provider in preferred_order:
        if provider in available_providers:
            return provider

    # This should ideally not be reached if 'google' is always available,
    # but as a safeguard, we return it.
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
        logger.error(f"Error translating batch with {provider_name}: {e}")
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


def _handle_rpd_limit(
    provider_name: str,
    rpd: Optional[int],
    batches: List[List[str]],
    current_batch_index: int,
    texts_to_translate_api: Dict[str, List[TextMatch]],
) -> bool:
    """
    Checks if the Requests Per Day (RPD) limit has been reached.

    If the limit is reached, it logs a warning, marks all remaining matches
    as failed, and returns True. Otherwise, it returns False.

    Args:
        provider_name: The name of the translation provider.
        rpd: The configured RPD limit.
        batches: The list of all batches to be processed.
        current_batch_index: The index of the current batch being processed.
        texts_to_translate_api: The dictionary of texts to translate.

    Returns:
        True if the RPD limit is reached, False otherwise.
    """
    global _rpd_session_counts
    if rpd and _rpd_session_counts[provider_name] >= rpd:
        logger.warning(
            f"Request Per Day limit ({rpd}) for '{provider_name}' reached. "
            f"Skipping remaining {len(batches) - current_batch_index} batches."
        )
        for remaining_batch in batches[current_batch_index:]:
            _update_matches_on_failure(remaining_batch, texts_to_translate_api, "error_rpd_limit")
        return True
    return False


def _translate_and_update_matches(
    translator: BaseTranslator,
    batches: List[List[str]],
    texts_to_translate_api: Dict[str, List[TextMatch]],
    task: TranslationTask,
    config: GlocalConfig,
    provider_name: str,
    protected_maps: Dict[str, Dict[str, str]],
    rpm: Optional[int],
    rpd: Optional[int],
):
    """Translates batches and handles rate limiting (RPM, RPD) and error handling."""
    global _rpd_session_counts
    delay = 60 / rpm if rpm and rpm > 0 else 0

    for i, batch in enumerate(batches):
        if not batch:
            continue

        if _handle_rpd_limit(provider_name, rpd, batches, i, texts_to_translate_api):
            break

        logger.info(f"Translating batch {i + 1}/{len(batches)} ({len(batch)} unique texts) using '{provider_name}'.")
        translated_results = _translate_batch(translator, batch, task, config.debug_options.enabled, provider_name)

        if rpd:
            _rpd_session_counts[provider_name] += 1

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

        if i < len(batches) - 1 and delay > 0:
            logger.info(f"RPM delay: sleeping for {delay:.2f} seconds.")
            time.sleep(delay)


def process_matches(
    matches: List[TextMatch],
    task: TranslationTask,
    config: GlocalConfig,
):
    if not matches:
        return
    unique_texts: Dict[str, List[TextMatch]] = defaultdict(list)
    for match in matches:
        unique_texts[match.original_text].append(match)
    logger.info(f"Found {len(unique_texts)} unique text strings to process for API translation.")
    texts_to_translate_api, protected_maps = _apply_translation_rules(unique_texts, task)
    if not texts_to_translate_api:
        logger.info("All texts were handled by pre-processing or were empty. No API call needed.")
        return
    provider_name = _select_provider(task, list(TRANSLATOR_MAPPING.keys()))
    logger.info(f"Selected translator for task '{task.name}': '{provider_name}' (Task-specific: {task.translator or 'Not set'}).")
    translator = get_translator(provider_name, config)

    # Fallback logic if the selected provider fails to initialize
    if not translator:
        logger.warning(f"Failed to initialize primary provider '{provider_name}'. Trying fallback 'google'.")
        provider_name = "google"
        translator = get_translator(provider_name, config)
        if not translator:
            logger.error("CRITICAL: Fallback provider 'google' also failed to initialize. Aborting translation.")
            _update_matches_on_failure(list(texts_to_translate_api.keys()), texts_to_translate_api, "initialization_error")
            return

    provider_settings = getattr(config.providers, provider_name, ProviderSettings())
    rpm = provider_settings.rpm
    tpm = provider_settings.tpm
    rpd = provider_settings.rpd
    batch_size = provider_settings.batch_size if provider_settings.batch_size is not None else 20

    # If key rate limits are not set, fall back to a single, un-throttled batch.
    if rpm is None or tpm is None:
        logger.info(f"Provider '{provider_name}' is not configured for intelligent scheduling (RPM/TPM). Sending as a single batch.")
        batches = [list(texts_to_translate_api.keys())]
    else:
        logger.info(f"Provider '{provider_name}' configured for intelligent scheduling: RPM={rpm}, TPM={tpm}, RPD={rpd or 'N/A'}.")
        batches = _create_batches(
            translator=translator,
            texts_to_translate=list(texts_to_translate_api.keys()),
            batch_size=batch_size,
            tpm=tpm,
            prompts=task.prompts,
        )

    _translate_and_update_matches(
        translator,
        batches,
        texts_to_translate_api,
        task,
        config,
        provider_name,
        protected_maps,
        rpm=rpm,
        rpd=rpd,
    )
