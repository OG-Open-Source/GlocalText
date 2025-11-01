# GlocalText

GlocalText is a powerful command-line tool that automates text translation using a highly intuitive, **firewall-style `rules` system**. It processes text by evaluating a list of rules from top to bottom, giving you precise, predictable control over your localization workflow.

---

## Table of Contents

-   [Introduction](#introduction)
-   [Key Features](#key-features)
-   [Installation](#installation)
-   [Configuration (`glocaltext_config.yaml`)](#configuration-glocaltext_configyaml)
-   [Usage](#usage)
-   [Contributors](#contributors)
-   [Contributing](#contributing)
-   [License](#license)

---

## Introduction

GlocalText is a powerful command-line tool that automates text translation using a highly intuitive, **firewall-style `rules` system**. It processes text by evaluating a list of rules from top to bottom, giving you precise, predictable control over your localization workflow.

At its core, the logic is simple: **for most actions, the first rule that matches wins**. When GlocalText extracts a piece of text, it checks your `rules` one by one. For terminating actions like `skip`, it executes the first matching rule and immediately stops processing for that text.

However, actions like `protect` and `replace` behave differently, allowing for **chainable pre-processing**. These rules will alter the text and then pass the _modified_ text back into the rules engine. This allows subsequent rules (including other `protect` or `replace` rules) to act on the text before it is finally sent for translation, enabling powerful, step-by-step text manipulation.

This design offers several key advantages:

1.  **Predictable Control**: You know exactly which rule will apply. There's no complex logic to manage—just a straightforward, top-down priority list.
2.  **Powerful Matching**: All matching is done via **regular expressions (Regex)**, giving you maximum power and flexibility to define patterns. A `match` condition can be a **single string** or a **list of strings**, allowing for flexible `OR` logic.
3.  **Default Action**: If no rules match a piece of text, it is sent to the configured translation provider for automated translation.

This unified, firewall-inspired `rules` engine provides a clear and powerful way to manage your entire translation workflow, from protecting brand names to providing authoritative manual translations.

## Key Features

-   **Unified Regex `rules` Engine**: A single, powerful system where all matching is done via regular expressions.
-   **Top-Down Priority**: Rules are evaluated from top to bottom—the first rule that matches wins for terminating actions, providing predictable and precise control.
-   **Chainable Pre-processing**: `protect` and `replace` rules act as pre-processors, allowing you to modify text in multiple stages before it's sent to the translator.
-   **Clear Actions**: Define clear actions:
    -   `skip`: A **terminating** action that prevents an entire text block from being translated. Ideal for code blocks or content that should never be altered.
    -   `replace`: A **pre-processing** action that performs a Regex substitution on the text. It supports backreferences (e.g., `\1`) and is ideal for complex text manipulation or providing authoritative translations.
    -   `protect`: A **pre-processing** action that protects a specific segment (like a brand name or variable) _within_ a larger text block, allowing the rest of the text to be translated.
-   **Multiple Provider Support**: Configure and use different translation providers like Google Translate, Gemini, and Gemma.
-   **Task-Based Configuration**: Define multiple, independent translation tasks in a single configuration file.
-   **Configuration Reusability**: Use `shortcuts` and `rulesets` to define reusable configuration snippets, making your setup clean and DRY.
-   **Glob Pattern Matching**: Precisely include or exclude files for translation using `glob` patterns.
-   **Flexible Output Control**: Choose to either modify original files directly (`in_place: true`) or create new, translated versions in a specified path (`in_place: false`).
-   **Incremental Translation**: Save time and cost by only translating new or modified content.

## Installation

```bash
pip install GlocalText
```

## Configuration (`glocaltext_config.yaml`)

This file is the control center for GlocalText. It is structured into several key sections:

-   `shortcuts`: Reusable configuration blocks that can be inherited by tasks.
-   `rulesets`: Reusable sets of rules that can be included in tasks.
-   `providers`: Configuration for translation providers (e.g., API keys, rate limits).
-   `tasks`: The list of translation jobs to be executed.
-   `debug_options`: Settings for enabling and configuring debug logging.
-   `report_options`: Settings for controlling summary report generation.

### Task Configuration

Each item in the `tasks` list defines a self-contained translation job. Tasks can also inherit settings from `shortcuts` to avoid repetition. Key settings include:

-   **`name`**: A unique name for the task.
-   **`source_lang`** & **`target_lang`**: The source and target language codes (e.g., "en", "zh-TW").
-   **`source`**: Defines which files to process.
    -   **`include`**: A list of `glob` patterns for files to translate.
    -   **`exclude`**: A list of `glob` patterns for files to skip.
-   **`extraction_rules`**: A list of regex patterns to extract translatable text.
-   **`incremental`**: A boolean (`true` or `false`) to enable or disable incremental translation. When enabled, only new or modified text is translated. This can also be overridden globally via the `--incremental` command-line flag.
-   **`cache_path`**: (Optional) A path to a directory where the task's cache file (`.glocaltext_cache.json`) will be stored.
-   **`output`**: Defines how translated files are written.
    -   **`in_place`**: If `true`, modifies original files. If `false`, writes to a new directory.
    -   **`path`**: The output directory. Required if `in_place` is `false`.
    -   **`filename`**: (Optional) A string template to define the output filename.
        -   Available placeholders: `{stem}`, `{source_lang}`, `{target_lang}`.
        -   Example: `filename: "{stem}.{target_lang}.md"` results in `mydoc.zh-TW.md`.
        -   If `filename` is provided, `filename_suffix` is ignored.
    -   **`filename_suffix`**: (Legacy) A suffix to add to the output filenames (e.g., `_translated`).
-   **`rules`**: The Regex-based rules for text processing (see `skip`, `replace`, `protect`).

### Configuration Inheritance with `shortcuts` and `rulesets`

To keep your configuration DRY (Don't Repeat Yourself), GlocalText supports `shortcuts` and `rulesets`.

-   **`shortcuts`**: Define reusable blocks of configuration. A special shortcut named `.defaults` is automatically inherited by all tasks. You can create other named shortcuts and apply them to tasks using the `<<: *shortcut_name` YAML anchor syntax.
-   **`rulesets`**: Define reusable lists of rules. You can include a ruleset in a task's `rules` list with `- ruleset: your_ruleset_name`.

```yaml
shortcuts:
    .defaults: &defaults
        translator: "gemini"
        incremental: true

    .markdown_docs: &markdown_docs
        <<: *defaults
        source:
            include: ["docs/**/*.md"]
        extraction_rules: ["`([^`]+)`"]

rulesets:
    brand-names:
        - "protect: GlocalText"

tasks:
    - name: "Translate Docs to French"
      <<: *markdown_docs
      target_lang: "fr"
      rules:
          - ruleset: brand-names
          - '"^Hello$" -> "Bonjour"' # Use regex anchors for an exact match
```

### Provider Settings

You can configure provider-specific settings under the `providers` key. For instance, for providers like `gemini` and `gemma`, you can specify the model and other API-specific parameters.

These settings offer fine-grained control over API interactions:

-   `model`: Specifies the model to use (e.g., `"gemini-1.5-flash"` for Gemini, or `"gemma-3-27b-it"` for Gemma).
-   `retry_attempts`: The number of times to retry a failed API call.
-   `retry_delay`: The delay in seconds between retries.
-   `retry_backoff_factor`: A multiplier to increase the delay between subsequent retries (e.g., a factor of `2` results in delays of 1s, 2s, 4s, ...).

In addition to retry logic, GlocalText includes a powerful **intelligent scheduling and batching system** to maximize throughput while respecting API rate limits. You can control this system using these optional parameters:

-   `rpm` (requests per minute): Max API requests per minute.
-   `tpm` (tokens per minute): Max tokens processed per minute.
-   `rpd` (requests per day): Max API requests per day.
-   `batch_size`: The number of texts to group into a single API call.

GlocalText uses these values to automatically manage API calls, batching texts and spacing out requests to avoid exceeding provider limits. This is highly effective for large translation jobs.

**Importantly**, all provider parameters are **optional**. GlocalText provides sensible defaults. For example, `gemma` defaults to a conservative `rpm` of 30, while other providers may have different defaults. If you only provide an `api_key`, the system will use default settings for everything else.

### API Key Configuration

API keys are configured under the `providers` section. GlocalText follows a clear priority for API key resolution:

1.  **Environment Variable**: It first checks for a dedicated environment variable (e.g., `GEMINI_API_KEY`).
2.  **Configuration File**: If the environment variable is not set, it uses the `api_key` from `glocaltext_config.yaml`.

This allows for flexibility in development (config file) and security in production (environment variables).

### System-Wide Settings

You can also define global `debug_options` and `report_options`:

```yaml
debug_options:
    enabled: true
    log_path: "logs/debug.log" # Custom path for the debug log

report_options:
    enabled: true
    export_csv: true
    export_dir: "reports" # Directory to save the CSV report
```

## Usage

### Command-Line Options

-   `-c <path>`, `--config <path>`: Specifies the path to your `glocaltext_config.yaml` file. Defaults to `glocaltext_config.yaml` in the current directory.
-   `--verbose`: Enables verbose (DEBUG level) logging to the console and creates a `glocaltext_debug.log` file in the current directory.
-   `--incremental`: Overrides all task-level settings to run in incremental mode, translating only new or modified content.
-   `--dry-run`: Performs a full run without making any actual changes or API calls. This is useful for testing your configuration and seeing what text will be translated.

## Contributors

<a href="https://github.com/OG-Open-Source/GlocalText/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=OG-Open-Source/GlocalText" />
</a>

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

## License

### Primary Project License

The main source code and documentation in this repository are licensed under the [MIT License](https://opensource.org/license/MIT).

### Third-Party Components and Attributions

This project utilizes external components or code whose copyright and licensing requirements must be separately adhered to:

| Component Name                    | Source / Author | License Type | Location of License Document     | Hash Values                      |
| :-------------------------------- | :-------------- | :----------- | :------------------------------- | -------------------------------- |
| OG-Open-Source README.md Template | OG-Open-Source  | MIT          | /licenses/OG-Open-Source/LICENSE | 120aee1912f4c2c51937f4ea3c449954 |

---

© 2025 [OG-Open-Source](https://github.com/OG-Open-Source). All rights reserved.
