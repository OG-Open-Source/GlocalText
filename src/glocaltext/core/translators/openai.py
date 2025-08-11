import time
import openai
import logging
import functools
from typing import List, Optional, Dict, Any

from .base import Translator
from glocaltext.core.config import OpenAIConfig

logger = logging.getLogger(__name__)


def rate_limit_retry(max_retries=10, base_delay=2):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except openai.RateLimitError as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            f"Rate limit exceeded. Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error("Max retries exceeded for rate limit.")
                        raise e
            return None

        return wrapper

    return decorator


class OpenAITranslator(Translator):
    def __init__(self, config: OpenAIConfig):
        self.config = config
        logger.debug(f"Initializing OpenAITranslator with model '{config.model}'")
        self.client = openai.OpenAI(base_url=config.base_url, api_key=config.api_key)

    def _build_system_prompt(
        self,
        target_language: str,
        source_language: str,
        glossary: Optional[Dict[str, str]],
    ) -> str:
        """Builds the system prompt for the OpenAI API."""
        if self.config.prompts:
            system_prompt = self.config.prompts.system.format(
                target_lang=target_language, source_lang=source_language
            )
        else:
            system_prompt = (
                "You are an expert translator specializing in software localization. "
                "Your task is to translate text accurately while preserving the original structure, "
                "placeholders, and variables."
            )

        if glossary:
            glossary_str = ", ".join(f'"{k}": "{v}"' for k, v in glossary.items())
            system_prompt += f"\n\nAdhere to this glossary: {glossary_str}"

        return system_prompt

    @rate_limit_retry()
    def _translate_single_text(
        self,
        text: str,
        system_prompt: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """Helper function to translate a single piece of text."""
        if self.config.prompts:
            user_prompt = self.config.prompts.contxt.format(
                source_lang=source_language, target_lang=target_language, text=text
            )
        else:
            user_prompt = (
                f"Translate the following text from '{source_language}' to '{target_language}'. "
                "Maintain all original formatting, including whitespace, and do not translate "
                f"placeholders like '{{...}}', '$...', or '%...%'.\n\n'{text}'"
            )

        logger.debug(f"[OpenAI] Inp: {user_prompt}")

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        logger.debug(f"[OpenAI] Oup: {response.choices[0].message.content}")
        return response.choices[0].message.content.strip()

    def translate(
        self,
        texts: List[str],
        target_language: str,
        source_language: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """
        Translates a list of texts using the OpenAI API.
        """

        system_prompt = self._build_system_prompt(
            target_language, source_language, glossary
        )
        logger.debug(f"System prompt: {system_prompt}")

        translated_texts = []
        for text in texts:
            logger.debug(
                f"Translating with OpenAI to '{target_language}': '{text[:50]}...'"
            )
            time.sleep(1)  # Add a 1-second delay to avoid rate limiting

            try:
                translated_text = self._translate_single_text(
                    text, system_prompt, source_language, target_language
                )
                translated_texts.append(translated_text)
            except openai.APIError as e:
                logger.error(f"OpenAI API error for text '{text[:50]}...': {e}")
                translated_texts.append(text)
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during OpenAI translation for text '{text[:50]}...': {e}"
                )
                translated_texts.append(text)

        return translated_texts
