# src/glocaltext/core/postprocessor.py

import re
from typing import List

from glocaltext.core.config import L10nConfig, ProtectionRule


class PostProcessor:
    """
    Handles post-processing of translated strings to restore protected patterns.
    """

    def __init__(self, config: L10nConfig):
        """
        Initializes the PostProcessor with the given configuration.

        Args:
            config: The localization configuration.
        """
        self.config = config

    def restore_protected_patterns(
        self, original_text: str, translated_text: str
    ) -> str:
        """
        Restores protected patterns from the original text to the translated text.

        This method finds all substrings in the original text that match the
        protection rules and intelligently inserts them back into the translated
        text.

        Args:
            original_text: The original source string.
            translated_text: The machine-translated string.

        Returns:
            The translated string with protected patterns restored.
        """
        # A lenient regex to find anything that looks like a placeholder,
        # covering {placeholder}, %s/%d, and $variable styles.
        lenient_placeholder_regex = r"(\{[^\}]+\}|%[sd]|\$[a-zA-Z0-9_]+)"

        # 1. Combine all protection rules into a single regex to find all placeholders at once,
        #    preserving their order.
        if not self.config.protection_rules:
            return translated_text

        combined_pattern = "|".join(
            rule.pattern for rule in self.config.protection_rules
        )
        original_placeholders = re.findall(combined_pattern, original_text)

        if not original_placeholders:
            return translated_text

        # 2. Find all potential (possibly garbled) placeholders in the translated text.
        translated_placeholders = re.findall(lenient_placeholder_regex, translated_text)

        # 3. If the counts match, replace them in order. This assumes that the
        #    order of placeholders is preserved during translation.
        if len(original_placeholders) != len(translated_placeholders):
            # If counts don't match, we cannot safely restore. Return as is.
            # TODO: Add logging here to warn the user.
            return translated_text

        restored_text = translated_text
        for original_ph, translated_ph in zip(
            original_placeholders, translated_placeholders
        ):
            # Replace only the first occurrence to handle duplicates correctly.
            restored_text = restored_text.replace(translated_ph, original_ph, 1)

        return restored_text
