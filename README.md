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

At its core, the logic is simple: **for most actions, the first rule that matches wins**. When GlocalText extracts a piece of text, it checks your `rules` one by one. For terminating actions like `skip` or `replace`, it executes the first matching rule and immediately stops processing for that text.

However, actions like `protect` and `modify` behave differently, allowing for **chainable pre-processing**. These rules will alter the text and then pass the _modified_ text back into the rules engine. This allows subsequent rules (including other `protect` or `modify` rules) to act on the text before it is finally sent for translation, enabling powerful, step-by-step text manipulation.

This design offers several key advantages:

1.  **Predictable Control**: You know exactly which rule will apply. There's no complex logic to manage—just a straightforward, top-down priority list.
2.  **Flexible Matching**: Define how a rule identifies text. You can use `exact` for a perfect match or `contains` to find a substring. A `match` condition can be a **single string** or a **list of strings**, allowing for flexible `OR` logic.
3.  **Default Action**: If no rules match a piece of text, it is sent to the configured translation provider for automated translation.

This unified, firewall-inspired `rules` engine provides a clear and powerful way to manage your entire translation workflow, from protecting brand names to providing authoritative manual translations.

## Key Features

-   **Unified Firewall `rules` Engine**: A single, powerful system to control your entire translation workflow.
-   **Top-Down Priority**: Rules are evaluated from top to bottom—the first rule that matches wins, providing predictable and precise control.
-   **Flexible Matching**: Match text with `exact` (full string) or `contains` (substring). The condition can be a single string or a list for flexible `OR` logic.
-   **Clear Actions**: Define clear actions:
    -   `skip`: A **terminating** action that protects the entire text block from being translated. Ideal for code blocks or content that should never be altered.
    -   `replace`: A **terminating** action that provides an authoritative, final translation for a text block, skipping the API entirely.
    -   `protect`: A **pre-processing** action that protects a specific segment (like a brand name or variable) _within_ a larger text block, allowing the rest of the text to be translated.
    -   `modify`: A **pre-processing** action that replaces a matched segment before passing the modified text back to the rules engine for further processing or translation.
-   **Multiple Provider Support**: Configure and use different translation providers like Google Translate and Google Gemini.
-   **Task-Based Configuration**: Define multiple, independent translation tasks in a single configuration file.
-   **Glob Pattern Matching**: Precisely include or exclude files for translation using `glob` patterns.
-   **Flexible Output Control**: Choose to either modify original files directly (`in_place: true`) or create new, translated versions in a specified path (`in_place: false`).
-   **Incremental Translation**: Save time and cost by only translating new or modified content.

## Installation

```bash
pip install GlocalText
```

## Configuration (`glocaltext_config.yaml`)

This file is the control center for GlocalText. It consists of global settings and a list of `tasks`.

### Task Configuration

Each item in the `tasks` list defines a self-contained translation job with the following settings:

-   **`name`**: A unique name for the task.
-   **`source_lang`** & **`target_lang`**: The source and target language codes (e.g., "en", "zh-TW").
-   **`source`**: Defines which files to process.
    -   **`include`**: A list of `glob` patterns for files to translate.
    -   **`exclude`**: A list of `glob` patterns for files to skip.
-   **`extraction_rules`**: A list of regex patterns to extract translatable text.
-   **`incremental`**: A boolean (`true` or `false`) to enable or disable incremental translation. When enabled, only new or modified text is translated. Defaults to `false`.
-   **`cache_path`**: (Optional) A path to a directory where the task's cache file (`.glocaltext_cache.json`) will be stored.
-   **`output`**: Defines how translated files are written.
    -   **`in_place`**: If `true`, modifies original files. If `false`, writes to a new directory.
    -   **`path`**: The output directory. Required if `in_place` is `false`.
    -   **`filename`**: (Optional) A string template to define the output filename.
        -   Available placeholders: `{stem}`, `{ext}`, `{source_lang}`, `{target_lang}`.
        -   Example: `filename: "{stem}_{target_lang}{ext}"` results in `mydoc_zh-TW.md`.
        -   If `filename` is provided, `filename_suffix` is ignored.
    -   **`filename_suffix`**: (Legacy) A suffix to add to the output filenames (e.g., `_translated`).
-   **`rules`**: The firewall-style rules for text processing (see `skip`, `replace`, `protect`, `modify`).

### API Key Configuration

API keys are configured under the `providers` section. GlocalText follows a clear priority for API key resolution:

1.  **Environment Variable**: It will first check for a dedicated environment variable (e.g., `GEMINI_API_KEY`).
2.  **Configuration File**: If the environment variable is not set, it will use the `api_key` specified in the `glocaltext_config.yaml` file.

This approach allows for flexibility in development (using the config file) and security in production (using environment variables).

## Usage

### Command-Line Options

-   `--config <path>` or `-c <path>`: Specifies the path to your `glocaltext_config.yaml` file. Defaults to `glocaltext_config.yaml` in the current directory.
-   `--debug [LOG_DIR_PATH]`: Enables detailed debug logging. If an optional directory path is provided, the debug log will be saved to `glocaltext_debug.log` inside that directory. Otherwise, debug information is printed to the console.

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
