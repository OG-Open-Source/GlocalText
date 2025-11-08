"""Core translation logic for GlocalText."""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import regex

from .config import GlocalConfig, ProviderSettings
from .coverage import TextCoverage
from .models import TextMatch
from .translators import TRANSLATOR_MAPPING
from .translators.base import BaseTranslator, TranslationResult
from .types import PreProcessedText, Rule, TranslationTask

logger = logging.getLogger(__name__)

# Pattern truncation length for debug logging
_PATTERN_LOG_MAX_LENGTH = 50

# A cache to store initialized translator instances to avoid re-creating them.
_translator_cache: dict[str, BaseTranslator] = {}
# A session-level counter for requests-per-day limits.
_rpd_session_counts: dict[str, int] = defaultdict(int)


@dataclass
class ProcessingContext:
    """
    Encapsulates the context for processing translation matches.

    This reduces function parameter count and improves maintainability
    by grouping related configuration into a single object.
    """

    task: TranslationTask
    translator: BaseTranslator
    provider_name: str
    debug: bool
    dry_run: bool = False


def _get_translator(provider_name: str, settings: ProviderSettings | None) -> BaseTranslator | None:
    """
    Instantiate a translator class using a dictionary-based factory pattern.

    This function retrieves the correct translator class from the central
    `TRANSLATOR_MAPPING` and initializes it with the provided settings.
    This approach replaces a complex if/elif/else structure, reducing
    cyclomatic complexity and making the system more extensible.

    Args:
        provider_name: The name of the provider (e.g., "gemini", "google").
        settings: The provider-specific settings object from the main config.

    Returns:
        An initialized translator instance, or None if instantiation fails.

    """
    provider_name_lower = provider_name.lower()
    if provider_name_lower not in TRANSLATOR_MAPPING:
        logger.warning("Unknown translator provider: '%s'", provider_name)
        return None

    translator_class = TRANSLATOR_MAPPING.get(provider_name_lower)
    if not translator_class:
        # This case should ideally not be hit if the enum and mapping are aligned,
        # but it's a safeguard.
        logger.warning("No translator class mapped for provider: '%s'", provider_name)
        return None

    try:
        # Factory: Instantiate the translator class with its settings.
        return translator_class(settings=settings)
    except (ImportError, AttributeError, KeyError, ValueError) as e:
        # Gracefully handle errors during instantiation (e.g., missing API key).
        logger.warning("Could not initialize translator '%s': %s", provider_name, e)
        return None


def get_translator(provider_name: str, config: GlocalConfig) -> BaseTranslator | None:
    """
    Retrieve an initialized translator instance, using a cache to avoid re-initialization.

    Args:
        provider_name: The name of the provider to retrieve.
        config: The global configuration object.

    Returns:
        An initialized and cached translator instance, or None if it fails.

    """
    if provider_name in _translator_cache:
        return _translator_cache[provider_name]

    provider_settings = config.providers.get(provider_name)
    if provider_settings is None:
        msg = f"Provider '{provider_name}' is not configured in your settings file."
        raise ValueError(msg)

    translator = _get_translator(provider_name, provider_settings)

    if translator:
        _translator_cache[provider_name] = translator
        logger.debug("Provider '%s' initialized.", provider_name)

    return translator


def _check_rule_match(text: str, rule: Rule) -> tuple[bool, str | None]:
    """Check if a text matches a given rule's regex pattern."""
    conditions = [rule.match.regex] if isinstance(rule.match.regex, str) else rule.match.regex
    for r in conditions:
        try:
            if regex.search(r, text, regex.DOTALL):
                return True, r
        except regex.error as e:  # noqa: PERF203
            # Backreferences in pattern (e.g., from sed-style replace rules)
            # cannot be used directly in regex matching
            logger.debug("[Rule Match] Skipping pattern with regex error: '%s...' - %s", r[:_PATTERN_LOG_MAX_LENGTH] if len(r) > _PATTERN_LOG_MAX_LENGTH else r, e)
    return False, None


def _handle_skip_action(matches: list[TextMatch]) -> bool:
    """Mark all matches as skipped."""
    for match in matches:
        match.provider = "skipped"
    return True


def _handle_replace_action(text: str, matched_value: str, rule: Rule) -> str:
    """
    Replace text using regex substitution, supporting backreferences.

    This function handles all 'replace' actions, including those parsed
    from the '->' syntax.
    """
    if rule.action.value is None:
        return text  # Should not happen due to pydantic validation

    logger.debug("[REPLACE ACTION] Input text: '%s'", text[:200])
    logger.debug("[REPLACE ACTION] Pattern to match: '%s'", matched_value)
    logger.debug("[REPLACE ACTION] Replacement value: '%s'", rule.action.value)

    try:
        # regex.sub correctly handles backreferences like \1, \g<name>, etc.
        modified_text = regex.sub(matched_value, rule.action.value, text, regex.DOTALL)
        logger.debug("[REPLACE ACTION] Output text: '%s'", modified_text[:200])
        logger.debug("[REPLACE ACTION] Text changed: %s", text != modified_text)
    except regex.error as e:
        logger.warning("Invalid regex substitution with pattern '%s': %s", matched_value, e)
        return text
    else:
        logger.debug("Text replaced: '%s' -> '%s'", text, modified_text)
        return modified_text


def _apply_regex_protection(text: str, matched_value: str, protected_map: dict[str, str]) -> str:
    """Apply protection for 'regex' matches."""
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
    except regex.error as e:
        logger.warning("Error during regex protection for pattern '%s': %s", matched_value, e)
        return text
    else:
        return new_text


def _apply_protection(text: str, matched_value: str, protected_map: dict[str, str]) -> str:
    """Apply protection to the text based on the rule's matched value."""
    return _apply_regex_protection(text, matched_value, protected_map)


def _handle_rule_action(
    text: str,
    matches: list[TextMatch],
    rule: Rule,
    protected_map: dict[str, str],
) -> tuple[str, bool]:
    """Dispatch a rule action to the appropriate handler."""
    match_found, matched_value = _check_rule_match(text, rule)
    if not match_found or not matched_value:
        return text, False

    action = rule.action.action
    is_handled = False

    if action == "skip":
        is_handled = _handle_skip_action(matches)
    elif action == "replace":
        # Since 'replace' now handles regex, it's a text modification, not a final assignment.
        # The final assignment happens in the calling context if needed.
        text = _handle_replace_action(text, matched_value, rule)
    elif action == "protect":
        text = _apply_protection(text, matched_value, protected_map)

    return text, is_handled


def _apply_pre_processing_rules(original_text: str, matches: list[TextMatch], task: TranslationTask) -> tuple[str, dict[str, str]]:
    """
    Apply pre-processing rules (currently only 'protect' rules).

    Note: Replace rules are now handled in apply_terminating_rules() BEFORE
    coverage detection (Solution A implementation). This ensures replace rules
    always execute regardless of coverage status.

    Args:
        original_text: The original text to process
        matches: List of TextMatch instances
        task: TranslationTask containing the rules

    Returns:
        tuple: (processed_text, protected_map) where protected_map contains
               placeholder mappings for protected text segments

    """
    logger.debug("[Pre-processing Rules] Function called with %d rules", len(task.rules))
    text_to_process = original_text
    protected_map: dict[str, str] = {}

    # Pre-processing rules are now ONLY 'protect' rules.
    # Replace rules are handled earlier in apply_terminating_rules().
    for rule in task.rules:
        logger.debug("[Pre-processing Rules] Processing rule: action=%s", rule.action.action)
        if rule.action.action == "protect":
            # 'protect' rules are always pre-processing.
            text_to_process, _ = _handle_rule_action(text_to_process, list(matches), rule, protected_map)
            logger.debug("[Pre-processing Protect] Protected text segments: %d", len(protected_map))

    return text_to_process, protected_map


def _try_terminate_with_replace(match: TextMatch, text: str, rule: Rule, matched_pattern: str) -> bool:
    """
    Attempt to terminate a match with a 'replace' rule.

    A 'replace' rule is terminating if it matches the ENTIRE string or replaces with an empty value.
    Returns True if the match was successfully terminated.
    """
    is_full_match = regex.fullmatch(matched_pattern, text, regex.DOTALL) is not None
    is_replace_to_empty = rule.action.value == ""

    if not (is_full_match or is_replace_to_empty):
        return False

    modified_text = _handle_replace_action(text, matched_pattern, rule)
    if modified_text != text:
        match.translated_text = modified_text
        match.provider = "rule:replace"
        return True

    return False


def _get_terminating_rule_patterns(rules: list[Rule]) -> list[str]:
    """
    Extract regex patterns from terminating rules.

    Args:
        rules: List of rules to filter

    Returns:
        List of regex patterns from skip/replace/protect rules

    """
    patterns = []
    for rule in rules:
        # Only process skip, replace, and protect rules for coverage
        if rule.action.action not in ("skip", "replace", "protect"):
            continue

        rule_patterns = [rule.match.regex] if isinstance(rule.match.regex, str) else rule.match.regex
        patterns.extend(rule_patterns)

    return patterns


def _track_pattern_coverage(pattern: str, text: str, coverage: TextCoverage, rule_action: str) -> None:
    """
    Track coverage of a single regex pattern in the text.

    Args:
        pattern: Regex pattern to search for
        text: Text to search in
        coverage: TextCoverage instance to update with matched ranges
        rule_action: Action type of the rule (skip, replace, protect)

    """
    # Replace rules should not contribute to coverage detection
    # because their purpose is to transform text, not to skip translation
    if rule_action == "replace":
        logger.debug("[Coverage Detection] Skipping replace rule - replace rules do not contribute to coverage")
        return

    try:
        # Find all matches of this pattern in the text
        for regex_match in regex.finditer(pattern, text, regex.DOTALL):
            start = regex_match.start()
            end = regex_match.end()
            coverage.add_range(start, end)
            logger.debug(
                "[Coverage Detection] Rule '%s' matched range [%d, %d) in text: '%s...'",
                pattern[:50],
                start,
                end,
                text[:50],
            )
    except regex.error as e:
        # Backreferences in pattern are invalid for coverage detection
        # This is expected for replace rules with sed-style patterns
        logger.debug("[Coverage Detection] Skipping pattern with regex error: '%s...' - %s", pattern[:_PATTERN_LOG_MAX_LENGTH] if len(pattern) > _PATTERN_LOG_MAX_LENGTH else pattern, e)
        return


def _select_text_for_coverage_check(match: TextMatch, original_text_for_coverage: str | None) -> str:
    """
    Select the appropriate text to use for coverage detection.

    CRITICAL: Uses explicit None checks to handle empty string ("") correctly.
    Empty strings from replace-to-empty rules should be treated as valid text.

    Args:
        match: The TextMatch instance
        original_text_for_coverage: Optional original text override

    Returns:
        The text to use for coverage checking

    """
    if match.processed_text is not None:
        return match.processed_text
    if original_text_for_coverage is not None:
        return original_text_for_coverage
    return match.original_text


def _get_non_replace_rules(rules: list[Rule]) -> list[Rule]:
    """
    Filter out replace rules from the rule list.

    Replace rules don't contribute to coverage detection because their purpose
    is to transform text, not to skip translation.

    Args:
        rules: List of all rules

    Returns:
        List of rules excluding replace rules (only skip/protect rules)

    """
    return [r for r in rules if r.action.action != "replace"]


def _check_full_coverage(match: TextMatch, rules: list[Rule], original_text_for_coverage: str | None = None) -> bool:
    """
    Check if terminating rules (skip/protect) fully cover the text.

    Replace rules are excluded from coverage detection because their purpose is
    to transform text, not to skip translation.

    This function creates a TextCoverage tracker for the match and applies only
    skip/protect rules to determine if they collectively cover 100% of the text.
    When fully covered, the match can skip translation entirely.

    Args:
        match: The TextMatch instance to check
        rules: List of terminating rules to check (will be filtered internally)
        original_text_for_coverage: Optional original text to use for coverage detection.
                                   If provided, this will be used instead of match.original_text.
                                   This is necessary when match.original_text has been modified
                                   by replace rules but we need to check coverage against the
                                   true original text.

    Returns:
        True if rules fully cover the text, False otherwise

    """
    # Select the appropriate text for coverage checking
    text_to_check = _select_text_for_coverage_check(match, original_text_for_coverage)

    # Empty text is considered fully covered
    if not text_to_check:
        return True

    # Filter out replace rules - they don't contribute to coverage
    non_replace_rules = _get_non_replace_rules(rules)

    logger.debug(
        "[Coverage Detection] Checking %d non-replace rules (filtered out %d replace rules)",
        len(non_replace_rules),
        len(rules) - len(non_replace_rules),
    )

    # Create coverage tracker for this match
    coverage = TextCoverage(text_to_check)

    # Track coverage for each non-replace rule
    for rule in non_replace_rules:
        if rule.match and rule.match.regex:
            rule_patterns = [rule.match.regex] if isinstance(rule.match.regex, str) else rule.match.regex
            for pattern in rule_patterns:
                _track_pattern_coverage(pattern, text_to_check, coverage, rule.action.action)

    # Check if text is fully covered
    is_fully_covered = coverage.is_fully_covered()

    if is_fully_covered:
        logger.info("[Full Coverage Detected] Text is 100%% covered by skip/protect rules: '%s...'", text_to_check[:50])
    else:
        coverage_pct = coverage.get_coverage_percentage()
        uncovered_ranges = coverage.get_uncovered_ranges()
        logger.debug("[Partial Coverage] Text is %.1f%% covered, uncovered ranges: %s", coverage_pct * 100, uncovered_ranges)

    return is_fully_covered


def _is_match_terminated(match: TextMatch, rules: list[Rule]) -> bool:
    """
    Check if a match should be terminated by a 'skip' rule.

    Coverage-aware design: Replace rules NO LONGER terminate translation flow.
    They only transform text. Termination is now solely determined by skip/protect
    rules through full coverage detection.

    This function handles traditional termination (single skip rule that fully matches
    the entire text). It does NOT handle full coverage detection - that's done by
    _check_full_coverage().

    Note: Skip rules now require full match to terminate. Partial skip matches are handled
    by the full coverage detection in _check_full_coverage().

    IMPORTANT: Uses processed_text (if available) to check skip rules, ensuring that
    skip rules are evaluated against text AFTER replace rules have executed.
    """
    # Use processed_text if available (after replace rules), otherwise use original_text
    text_to_process = match.processed_text or match.original_text
    logger.debug("[Terminating Check] Checking if match should be terminated: '%s...' (using %s)", text_to_process[:50], "processed_text" if match.processed_text else "original_text")
    for rule in rules:
        logger.debug("[Terminating Check] Testing rule: action=%s, regex=%s", rule.action.action, rule.match.regex)
        # Only skip rules can traditionally terminate (replace rules no longer terminate)
        if rule.action.action != "skip":
            continue

        match_found, matched_pattern = _check_rule_match(text_to_process, rule)
        if not match_found or not matched_pattern:
            continue

        # For skip rules, only terminate if the pattern fully matches the entire text
        # Check if this is a full match (covers entire text)
        if regex.fullmatch(matched_pattern, text_to_process, regex.DOTALL):
            _handle_skip_action([match])
            logger.debug("[Terminating Check] Skip rule fully matched entire text, terminating")
            return True
        # Partial match - let full coverage detection handle it
        logger.debug("[Terminating Check] Skip rule only partially matched, continuing")

    return False


def _classify_terminating_rules(rules: list[Rule]) -> tuple[list[Rule], list[Rule], list[Rule]]:
    """
    Classify rules into replace, other terminating, and all terminating rules.

    Args:
        rules: List of all rules

    Returns:
        tuple: (replace_rules, other_terminating_rules, terminating_rules)
               - replace_rules: Rules with action "replace"
               - other_terminating_rules: Rules with action "skip" or "protect"
               - terminating_rules: All rules with terminating actions

    """
    replace_rules = [r for r in rules if r.action.action == "replace"]
    other_terminating_rules = [r for r in rules if r.action.action in ("skip", "protect")]
    terminating_rules = [r for r in rules if r.action.action in ("skip", "replace", "protect")]
    return replace_rules, other_terminating_rules, terminating_rules


def _apply_replace_rules_to_match(match: TextMatch, replace_rules: list[Rule]) -> None:
    """
    Apply all replace rules to a match, modifying its processed_text field.

    CRITICAL: This function modifies match.processed_text (not match.original_text)
    to preserve cache consistency.

    Args:
        match: The TextMatch to process (modified in-place)
        replace_rules: List of replace rules to apply

    """
    text_before_any_replacement = match.original_text
    modified_text = match.original_text

    for rule in replace_rules:
        match_found, matched_pattern = _check_rule_match(modified_text, rule)
        if match_found and matched_pattern:
            modified_text = _handle_replace_action(modified_text, matched_pattern, rule)
            logger.debug(
                "[Replace Rule Applied] Pattern '%s...' replaced in text. Changed: %s",
                matched_pattern[:30],
                text_before_any_replacement != modified_text,
            )

    # Store the processed text if it was modified
    if modified_text != match.original_text:
        logger.info(
            "[Replace Rules] Text modified by replace rules: '%s...' -> '%s...'",
            match.original_text[:50],
            modified_text[:50],
        )
        match.processed_text = modified_text


def _determine_match_termination(
    match: TextMatch,
    terminating_rules: list[Rule],
    terminated_matches: list[TextMatch],
    unhandled_matches: list[TextMatch],
) -> None:
    """
    Determine if a match should be terminated and add it to the appropriate list.

    Args:
        match: The TextMatch to evaluate
        terminating_rules: All terminating rules to check
        terminated_matches: List to append terminated matches (modified in-place)
        unhandled_matches: List to append unhandled matches (modified in-place)

    """
    if _check_full_coverage(match, terminating_rules):
        # Text is fully covered by terminating rules - skip translation
        match.provider = "fully_covered"
        # Use processed_text if available (from replace rules), otherwise use original_text
        match.translated_text = match.processed_text if match.processed_text else match.original_text
        terminated_matches.append(match)
        logger.info("[Full Coverage] Match fully covered by rules, skipping translation: '%s...'", match.original_text[:50])
    elif _is_match_terminated(match, terminating_rules):
        # Traditional termination (single rule match)
        terminated_matches.append(match)
    else:
        # Not terminated, proceed with translation
        unhandled_matches.append(match)


def apply_terminating_rules(
    matches: list[TextMatch],
    task: TranslationTask,
) -> tuple[list[TextMatch], list[TextMatch]]:
    """
    Apply terminating rules (skip, replace, protect) and partition matches.

    This function now executes replace rules FIRST (before coverage detection),
    then includes full coverage detection. When terminating rules
    (skip/replace/protect) fully cover the entire text, translation is skipped
    to save API costs and improve performance.

    Solution A Implementation: Replace rules are applied to match.original_text
    BEFORE coverage detection, ensuring they always execute regardless of
    coverage status.

    Args:
        matches: List of TextMatch instances to process
        task: TranslationTask containing the rules to apply

    Returns:
        tuple: (unhandled_matches, terminated_matches) where terminated_matches
               includes both traditionally terminated and fully covered matches

    """
    logger.debug("[Terminating Rules] Function called with %d matches and %d rules", len(matches), len(task.rules))
    unhandled_matches: list[TextMatch] = []
    terminated_matches: list[TextMatch] = []

    # Classify rules into different categories
    replace_rules, other_terminating_rules, terminating_rules = _classify_terminating_rules(task.rules)

    logger.debug("[Terminating Rules] Found %d replace rules, %d other terminating rules", len(replace_rules), len(other_terminating_rules))

    if not terminating_rules:
        logger.debug("[Terminating Rules] No terminating rules found, returning all matches as unhandled")
        return matches, []

    logger.debug("[Terminating Rules] Starting to check %d matches against terminating rules", len(matches))
    for match in matches:
        logger.debug("[Terminating Rules] Checking match: '%s...'", match.original_text[:50])

        # PHASE 1: Apply all replace rules FIRST (before coverage detection)
        _apply_replace_rules_to_match(match, replace_rules)

        # PHASE 2: Check if rules fully cover the text and determine termination
        _determine_match_termination(match, terminating_rules, terminated_matches, unhandled_matches)

    return unhandled_matches, terminated_matches


def _apply_translation_rules(unique_texts: dict[str, list[TextMatch]], task: TranslationTask) -> list[PreProcessedText]:
    pre_processed_texts: list[PreProcessedText] = []
    for original_text, matches in unique_texts.items():
        # Use processed_text if available (from replace rules), otherwise use original_text
        # This ensures replace rules are applied before protect rules
        first_match = matches[0] if matches else None
        text_for_processing = first_match.processed_text if first_match and first_match.processed_text else original_text

        text_to_process, protected_map = _apply_pre_processing_rules(text_for_processing, matches, task)
        pre_processed_texts.append(
            PreProcessedText(
                original_text=original_text,  # Keep original for cache consistency
                text_to_process=text_to_process,
                protected_map=protected_map,
                matches=matches,
            ),
        )
    return pre_processed_texts


def _log_oversized_batch_warning(
    translator: BaseTranslator,
    batch: list[str],
    tpm: int,
    prompts: dict[str, str] | None,
) -> None:
    """Check and log a warning if a single-item batch exceeds the TPM limit."""
    single_item_tokens = translator.count_tokens(batch, prompts)
    if single_item_tokens > tpm:
        logger.warning(
            "A single text item (%d tokens) exceeds the TPM limit (%d). It will be sent in an oversized batch. This may cause API errors.",
            single_item_tokens,
            tpm,
        )


def _create_simple_batches(texts_to_translate: list[str], batch_size: int) -> list[list[str]]:
    """Create simple, size-based batches."""
    if not texts_to_translate:
        return []
    effective_batch_size = batch_size if batch_size > 0 else len(texts_to_translate)
    if not effective_batch_size:
        return []
    return [texts_to_translate[i : i + effective_batch_size] for i in range(0, len(texts_to_translate), effective_batch_size)]


def _create_smart_batches(
    translator: BaseTranslator,
    texts_to_translate: list[str],
    batch_size: int,
    tpm: int,
    prompts: dict[str, str] | None,
) -> list[list[str]]:
    """Create smart batches considering size and token limits."""
    batches: list[list[str]] = []
    current_batch: list[str] = []

    for text in texts_to_translate:
        if not current_batch:
            current_batch.append(text)
            _log_oversized_batch_warning(translator, current_batch, tpm, prompts)
        else:
            predicted_batch = [*current_batch, text]
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
    texts_to_translate: list[str],
    batch_size: int,
    tpm: int | None,
    prompts: dict[str, str] | None,
) -> list[list[str]]:
    """Create smart batches by delegating to simple or smart batching strategies."""
    if tpm is None or tpm <= 0:
        return _create_simple_batches(texts_to_translate, batch_size)

    if not texts_to_translate:
        return []

    return _create_smart_batches(translator, texts_to_translate, batch_size, tpm, prompts)


def _select_provider(task: TranslationTask, available_providers: list[str]) -> str:
    """Select the translation provider based on task and availability."""
    if not task.translator:
        msg = f"Task '{task.name}' does not specify a 'translator'. This is required in v2.1+."
        raise ValueError(msg)

    if task.translator in available_providers:
        return task.translator

    msg = f"Task '{task.name}' specified translator '{task.translator}', but it is not configured in 'providers'."
    raise ValueError(msg)


def _translate_batch(
    translator: BaseTranslator,
    batch: list[str],
    task: TranslationTask,
    provider_name: str,
    *,
    debug: bool,
) -> list[TranslationResult] | None:
    """Translate a single batch of texts and handle exceptions."""
    try:
        return translator.translate(
            texts=batch,
            target_language=task.target_lang,
            source_language=task.source_lang,
            debug=debug,
            prompts=task.prompts if task.prompts else None,
        )
    except Exception:
        logger.exception("Error translating batch with %s", provider_name)
        return None


def _restore_protected_text(translated_text: str, protected_map: dict[str, str]) -> str:
    for placeholder, original_word in protected_map.items():
        translated_text = translated_text.replace(placeholder, original_word)
    return translated_text


def _update_matches_on_success(
    batch: list[str],
    translated_results: list[Any],
    item_map: dict[str, PreProcessedText],
    provider_name: str,
) -> None:
    for text_to_process, result in zip(batch, translated_results, strict=False):
        processed_item = item_map.get(text_to_process)
        if not processed_item:
            continue

        # Use the item's own protected_map
        restored_text = _restore_protected_text(result.translated_text, processed_item.protected_map)

        # Update all associated matches
        for match in processed_item.matches:
            match.translated_text = restored_text
            match.provider = provider_name
            if result.tokens_used is not None:
                match.tokens_used = (match.tokens_used or 0) + result.tokens_used


def _update_matches_on_failure(
    batch: list[str],
    item_map: dict[str, PreProcessedText],
    provider_name: str,
) -> None:
    for text_to_process in batch:
        processed_item = item_map.get(text_to_process)
        if not processed_item:
            continue
        for match in processed_item.matches:
            match.provider = f"error_{provider_name}"


def _handle_rpd_limit(
    provider_name: str,
    rpd: int | None,
    batches: list[list[str]],
    current_batch_index: int,
    item_map: dict[str, PreProcessedText],
) -> bool:
    """
    Check and handle the Requests Per Day (RPD) limit.

    If the limit is reached, log a warning, mark remaining matches as failed,
    and return True.

    Args:
        provider_name: The name of the translation provider.
        rpd: The configured RPD limit.
        batches: The list of all batches to be processed.
        current_batch_index: The index of the current batch being processed.
        item_map: A map from text to PreProcessedText.

    Returns:
        True if the RPD limit is reached, False otherwise.

    """
    if rpd and _rpd_session_counts[provider_name] >= rpd:
        remaining_batches = len(batches) - current_batch_index
        logger.warning(
            "Request Per Day limit (%d) for '%s' reached. Skipping remaining %d batches.",
            rpd,
            provider_name,
            remaining_batches,
        )
        for remaining_batch in batches[current_batch_index:]:
            _update_matches_on_failure(remaining_batch, item_map, "rpd_limit")
        return True
    return False


def _translate_and_update_matches(  # noqa: PLR0913
    translator: BaseTranslator,
    batches: list[list[str]],
    pre_processed_items: list[PreProcessedText],
    task: TranslationTask,
    provider_name: str,
    rpm: int | None,
    rpd: int | None,
    *,
    debug: bool,
) -> None:
    """Translate batches and handle rate limiting, errors, and match updates."""
    delay = 60 / rpm if rpm and rpm > 0 else 0
    item_map = {item.text_to_process: item for item in pre_processed_items}

    for i, batch in enumerate(batches):
        if not batch:
            continue

        if _handle_rpd_limit(provider_name, rpd, batches, i, item_map):
            break

        logger.info(
            "Translating batch %d/%d (%d unique texts) using '%s'.",
            i + 1,
            len(batches),
            len(batch),
            provider_name,
        )
        translated_results = _translate_batch(translator, batch, task, provider_name, debug=debug)

        if rpd:
            _rpd_session_counts[provider_name] += 1

        if translated_results:
            _update_matches_on_success(
                batch,
                translated_results,
                item_map,
                provider_name,
            )
        else:
            _update_matches_on_failure(batch, item_map, provider_name)

        if i < len(batches) - 1 and delay > 0:
            logger.debug("RPM delay: sleeping for %.2f seconds.", delay)
            time.sleep(delay)


def _handle_dry_run_mode(
    texts_to_translate_api: list[str],
    pre_processed_items: list[PreProcessedText],
) -> None:
    """
    Handle dry-run mode by marking matches without calling the API.

    Args:
        texts_to_translate_api: List of texts that would be translated
        pre_processed_items: Pre-processed items containing matches to update

    """
    logger.info("[DRY RUN] Pre-processing rules applied. Skipping actual API translation for %d texts.", len(texts_to_translate_api))
    item_map = {item.text_to_process: item for item in pre_processed_items}
    for text_to_process in texts_to_translate_api:
        processed_item = item_map.get(text_to_process)
        if processed_item:
            for match in processed_item.matches:
                match.provider = "dry_run_skipped"
                # In dry-run, show the pre-processed text (with rules applied) as the result
                match.translated_text = processed_item.text_to_process


def _determine_batching_strategy(
    context: ProcessingContext,
    texts_to_translate_api: list[str],
    provider_settings: ProviderSettings,
) -> list[list[str]]:
    """
    Determine the batching strategy based on provider configuration.

    Args:
        context: Processing context containing translator and task info
        texts_to_translate_api: Texts to be translated
        provider_settings: Provider-specific settings

    Returns:
        List of text batches ready for translation

    """
    rpm = provider_settings.rpm
    tpm = provider_settings.tpm
    rpd = provider_settings.rpd
    batch_size = provider_settings.batch_size if provider_settings.batch_size is not None else 20

    if rpm is None or tpm is None:
        logger.info(
            "Provider '%s' is not configured for intelligent scheduling (RPM/TPM). Sending as a single batch.",
            context.provider_name,
        )
        return [texts_to_translate_api]

    logger.debug(
        "Provider '%s' configured for intelligent scheduling: RPM=%s, TPM=%s, RPD=%s.",
        context.provider_name,
        rpm,
        tpm,
        rpd or "N/A",
    )
    return _create_batches(
        translator=context.translator,
        texts_to_translate=texts_to_translate_api,
        batch_size=batch_size,
        tpm=tpm,
        prompts=context.task.prompts if context.task.prompts else None,
    )


def _process_genai_matches(
    matches: list[TextMatch],
    context: ProcessingContext,
) -> None:
    """Process matches using a GenAI provider with batching and rule processing."""
    if not matches:
        return

    unique_texts: dict[str, list[TextMatch]] = defaultdict(list)
    for match in matches:
        unique_texts[match.original_text].append(match)
    logger.info("Found %d unique text strings to process for API translation.", len(unique_texts))

    # Always apply pre-processing rules (protect and replace), even in dry-run mode
    logger.debug("[Pre-processing] Applying translation rules to %d unique texts.", len(unique_texts))
    pre_processed_items = _apply_translation_rules(unique_texts, context.task)
    texts_to_translate_api = list(dict.fromkeys(item.text_to_process for item in pre_processed_items if item.text_to_process and item.text_to_process.strip()))

    if not texts_to_translate_api:
        logger.info("All texts were handled by pre-processing or were empty. No API call needed.")
        return

    # In dry-run mode, skip actual API translation but mark matches appropriately
    if context.dry_run:
        _handle_dry_run_mode(texts_to_translate_api, pre_processed_items)
        return

    provider_settings = context.translator.settings or ProviderSettings()
    batches = _determine_batching_strategy(context, texts_to_translate_api, provider_settings)

    _translate_and_update_matches(
        context.translator,
        batches,
        pre_processed_items,
        context.task,
        context.provider_name,
        rpm=provider_settings.rpm,
        rpd=provider_settings.rpd,
        debug=context.debug,
    )


def _process_simple_matches(
    matches: list[TextMatch],
    context: ProcessingContext,
) -> None:
    """Process matches using a simple, non-batching, non-GenAI translator."""
    if not matches:
        return

    # In dry-run mode, skip actual API translation
    if context.dry_run:
        logger.info("[DRY RUN] Skipping simple translator API calls for %d matches.", len(matches))
        for match in matches:
            match.provider = "dry_run_skipped"
            match.translated_text = match.original_text
        return

    # Simple providers handle one text at a time.
    for match in matches:
        try:
            results = context.translator.translate(
                texts=[match.original_text],
                target_language=context.task.target_lang,
                source_language=context.task.source_lang,
                debug=context.debug,
                prompts=None,  # Simple providers don't use prompts
            )
            if results:
                match.translated_text = results[0].translated_text
                match.tokens_used = results[0].tokens_used
                match.provider = context.provider_name
        except Exception:  # noqa: PERF203
            logger.exception("Error translating text '%s' with %s", match.original_text, context.provider_name)
            match.provider = f"error_{context.provider_name}"


def process_matches(
    matches: list[TextMatch],
    task: TranslationTask,
    config: GlocalConfig,
    *,
    debug: bool,
    dry_run: bool = False,
) -> None:
    """
    Process a list of text matches for a given translation task.

    This function orchestrates the main translation workflow by dispatching
    to the appropriate handler based on the selected provider type.

    Args:
        matches: List of text matches to process.
        task: The translation task configuration.
        config: Global configuration.
        debug: Whether to enable debug mode.
        dry_run: If True, apply pre-processing rules but skip actual API translation.

    """
    provider_name = _select_provider(task, list(TRANSLATOR_MAPPING.keys()))
    translator = get_translator(provider_name, config)

    if not translator:
        logger.error("CRITICAL: Could not initialize any translator for task '%s'. Aborting.", task.name)
        for match in matches:
            match.provider = "initialization_error"
        return

    # Create processing context
    context = ProcessingContext(
        task=task,
        translator=translator,
        provider_name=provider_name,
        debug=debug,
        dry_run=dry_run,
    )

    # --- Dispatch based on provider type ---
    if provider_name in ("gemini", "gemma"):
        _process_genai_matches(matches, context)
    else:
        # Fallback for simple, non-GenAI translators like 'google' or 'mock'
        _process_simple_matches(matches, context)
