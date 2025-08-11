import logging
from pathlib import Path
import typer
import yaml

from glocaltext.utils.logger import setup_logger
from glocaltext.utils.debug_logger import DebugLogger
from glocaltext.core.config import I18nConfig, L10nConfig
from glocaltext.core.cache import TranslationCache
from glocaltext.core.i18n import I18nProcessor
from glocaltext.core.l10n import L10nProcessor
from glocaltext.core.compiler import Compiler
from glocaltext.core.sync import SyncProcessor

app = typer.Typer(
    help="GlocalText: A command-line tool for seamless software localization.",
    add_completion=False,
)


@app.command()
def init(
    directory_path: str = typer.Argument(
        ".", help="The path to the directory to initialize."
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug mode with verbose logging."
    ),
):
    """
    Initialize GlocalText configuration files (i18n-rules.yaml and l10n-rules.yaml).
    """
    setup_logger(level=logging.DEBUG if debug else logging.INFO, debug=debug)

    logger = logging.getLogger("glocaltext")

    base_path = Path(directory_path)
    ogos_path = base_path / ".ogos"
    ogos_path.mkdir(exist_ok=True)

    i18n_config_path = ogos_path / "i18n-rules.yaml"
    l10n_config_path = ogos_path / "l10n-rules.yaml"

    if i18n_config_path.exists() or l10n_config_path.exists():
        logger.warning(
            f"Configuration files already exist in {ogos_path}. Aborting initialization."
        )
        raise typer.Abort()

    # Create default i18n-rules.yaml using a dictionary and yaml.dump
    i18n_data = {
        "source": {
            "include": ["**/*.*"],
            "exclude": ["tests/*", "docs/*", ".ogos/*", "localized/*"],
        },
        "capture_rules": [{"pattern": '"(.*?)"', "capture_group": 1}],
        "ignore_rules": [{"pattern": r"^(?:\s*[\$\%\{].*|.*[\}\%]\s*)$"}],
        "protection_rules": [
            {"pattern": r"\$\{\w+\}"},
            {"pattern": r"\$\w+"},
            {"pattern": r"\%[\w~]+\%"},
            {"pattern": r"\%~\d"},
            {"pattern": r"\$\(.*?\)"},
        ],
    }
    with open(i18n_config_path, "w", encoding="utf-8") as f:
        yaml.dump(i18n_data, f, sort_keys=False, allow_unicode=True)
    logger.info(f"Created default i18n configuration at: {i18n_config_path}")

    # Create default l10n-rules.yaml
    l10n_data = {
        "translation_settings": {
            "source_lang": "en",
            "target_lang": ["ja", "zh-TW"],
            "provider": "google",
        },
        "provider_configs": {
            "gemini": {"model": "GEMINI_MODEL_NAME", "api_key": "GEMINI_API_KEY"},
            "openai": {
                "model": "OPENAI_MODEL_NAME",
                "base_url": "https://api.openai.com/v1",
                "api_key": "OPENAI_API_KEY",
                "prompts": {
                    "system": "You are a professional translator.",
                    "contxt": "Translate the following text from {source_lang} to {target_lang}, preserving all original formatting, placeholders, and variables like `{{0}}` or `$var`:",
                },
            },
            "ollama": {"model": "llama3", "base_url": "http://localhost:11434"},
        },
        "glossary": {"GlocalText": "GlocalText"},
        "glossary_file": None,
    }
    with open(l10n_config_path, "w", encoding="utf-8") as f:
        yaml.dump(l10n_data, f, sort_keys=False, allow_unicode=True)
    logger.info(f"Created default l10n configuration at: {l10n_config_path}")


@app.command()
def i18n(
    project_path: Path = typer.Option(
        Path("."),
        "--project-path",
        "-p",
        help="The root path of the project to scan.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    config: Path = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to the i18n-rules.yaml configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug mode with verbose logging."
    ),
):
    """
    Scans source files, extracts strings based on configured rules.
    """
    ogos_path = project_path / ".ogos"
    artifacts_path = ogos_path / "artifacts"
    logger = setup_logger(
        level=logging.DEBUG if debug else logging.INFO,
        debug=debug,
        artifacts_path=artifacts_path,
    )

    try:
        if config is None:
            config = ogos_path / "i18n-rules.yaml"

        i18n_config = I18nConfig.from_yaml(config)
        debug_logger = DebugLogger(project_path, enabled=debug)

        try:
            logger.info("Scanning source files and extracting strings...")
            i18n_processor = I18nProcessor(i18n_config, project_path, debug_logger)
            i18n_processor.run()
            logger.info(
                f"Found {len(i18n_processor.extracted_strings)} total unique strings in source code."
            )
            logger.info("Extraction complete. Intermediate artifacts saved.")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during i18n processing: {e}",
                exc_info=debug,
            )
            raise typer.Abort()
        finally:
            if debug:
                report = debug_logger.finalize()
                if report:
                    logger.debug(f"\n{report}")

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        raise typer.Abort()
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during i18n processing: {e}", exc_info=debug
        )
        raise typer.Abort()


@app.command()
def l10n(
    project_path: Path = typer.Option(
        Path("."),
        "--project-path",
        "-p",
        help="The root path of the project to scan.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    i18n_config_path: Path = typer.Option(
        None,
        "--i18n-config",
        help="Path to the i18n-rules.yaml file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    l10n_config_path: Path = typer.Option(
        None,
        "--l10n-config",
        help="Path to the l10n-rules.yaml file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force re-translation of all strings, ignoring the cache.",
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug mode with verbose logging."
    ),
):
    """
    Translates extracted strings and compiles them into localized files.
    """
    ogos_path = project_path / ".ogos"
    artifacts_path = ogos_path / "artifacts"
    logger = setup_logger(
        level=logging.DEBUG if debug else logging.INFO,
        debug=debug,
        artifacts_path=artifacts_path,
    )

    try:
        if i18n_config_path is None:
            i18n_config_path = ogos_path / "i18n-rules.yaml"
        if l10n_config_path is None:
            l10n_config_path = ogos_path / "l10n-rules.yaml"

        i18n_config = I18nConfig.from_yaml(i18n_config_path)
        l10n_config = L10nConfig.from_yaml(l10n_config_path)

        debug_logger = DebugLogger(project_path, enabled=debug)

        try:
            cache = TranslationCache(artifacts_path, debug_logger)
            # We need to run i18n processor to populate the strings to be translated
            i18n_processor = I18nProcessor(i18n_config, project_path, debug_logger)
            i18n_processor.run()
            current_strings = i18n_processor.extracted_strings

            l10n_processor = L10nProcessor(
                l10n_config, cache, i18n_processor, debug_logger
            )
            compiler = Compiler(l10n_config, cache, i18n_processor, debug_logger)

            # This logic is adapted from the old `run_localization` function
            if force:
                logger.info("Force option detected. All strings will be re-translated.")
                strings_to_translate = current_strings
            else:
                logger.info(
                    "Performing differential check against translation cache..."
                )
                strings_to_translate = {
                    h: s for h, s in current_strings.items() if not cache.get(h)
                }

            logger.info(
                f"Found {len(strings_to_translate)} new or modified strings to translate."
            )

            dangling_hashes = cache.get_all_cached_hashes() - set(
                current_strings.keys()
            )
            if dangling_hashes:
                logger.info(
                    f"Found {len(dangling_hashes)} dangling strings to prune from cache."
                )
                cache.remove_entries_by_hash(dangling_hashes)

            if strings_to_translate:
                logger.info("Starting l10n translation process...")
                l10n_processor.process_and_translate(strings_to_translate, force=force)
                logger.info("Translation process completed.")
            else:
                logger.info("No new or modified strings to translate.")

            logger.info("Starting compilation of localized files...")
            compiler.run(project_path)
            logger.info("Compilation completed.")

            cache.save()
            logger.info("Translation cache saved.")

        except Exception as e:
            logger.error(
                f"An unexpected error occurred during l10n processing: {e}",
                exc_info=debug,
            )
            raise typer.Abort()
        finally:
            if debug:
                report = debug_logger.finalize()
                if report:
                    logger.debug(f"\n{report}")

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        raise typer.Abort()
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during l10n processing: {e}", exc_info=debug
        )
        raise typer.Abort()


@app.command()
def sync(
    project_path: Path = typer.Option(
        Path("."),
        "--project-path",
        "-p",
        help="The root path of the project to sync.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    i18n_config_path: Path = typer.Option(
        None,
        "--i18n-config",
        help="Path to the i18n-rules.yaml file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    l10n_config_path: Path = typer.Option(
        None,
        "--l10n-config",
        help="Path to the l10n-rules.yaml file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug mode with verbose logging."
    ),
):
    """
    Sync manual changes from the 'localized' directory back to the translation cache.
    """
    ogos_path = project_path / ".ogos"
    artifacts_path = ogos_path / "artifacts"
    logger = setup_logger(
        level=logging.DEBUG if debug else logging.INFO,
        debug=debug,
        artifacts_path=artifacts_path,
    )

    try:
        if i18n_config_path is None:
            i18n_config_path = ogos_path / "i18n-rules.yaml"
        if l10n_config_path is None:
            l10n_config_path = ogos_path / "l10n-rules.yaml"

        # Load configs
        i18n_config = I18nConfig.from_yaml(i18n_config_path)
        l10n_config = L10nConfig.from_yaml(l10n_config_path)

        # Initialize components
        debug_logger = DebugLogger(project_path, enabled=debug)
        try:
            cache = TranslationCache(artifacts_path, debug_logger)
            i18n_processor = I18nProcessor(i18n_config, project_path, debug_logger)
            sync_processor = SyncProcessor(
                l10n_config, cache, i18n_processor, project_path, debug_logger
            )

            # Run sync workflow
            sync_processor.run()

            cache.save()
            logger.info("Translation cache updated from sync.")
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            raise typer.Abort()
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during sync: {e}", exc_info=debug
            )
            raise typer.Abort()
        finally:
            if debug:
                report = debug_logger.finalize()
                if report:
                    logger.debug(f"\n{report}")

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        raise typer.Abort()
    except Exception as e:
        logger.error(f"An unexpected error occurred during sync: {e}", exc_info=debug)
        raise typer.Abort()


# The `run` command is now an alias for `l10n`
app.command(name="run")(l10n)


if __name__ == "__main__":
    app()
