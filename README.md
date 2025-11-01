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

`GlocalText` is controlled by a central YAML configuration file, typically named `glocaltext_config.yaml`. This file acts as the command center for all translation tasks, defining everything from provider credentials to the specific jobs to be executed.

Here is a breakdown of the configuration structure, based on the `glocaltext_config.example.yaml`.

### Top-Level Keys

-   `project_root` (Optional): Sets the root directory for the project. All relative paths within the configuration (e.g., in `source` or `output`) will be resolved from this location. If not specified, it defaults to the directory where you run the `glocaltext` command.

### 1. `providers`

This section is where you configure the settings for different translation providers. You only need to configure the ones you plan to use.

-   **`gemini`**: Settings for Google's Gemini models.
    -   `api_key`: Your Gemini API key.
    -   `model`: The specific model to use (e.g., `gemini-2.5-flash-lite`).
    -   `rpm`, `tpm`: Rate and token limits.
    -   `batch_size`: Number of concurrent requests.
-   **`gemma`**: Settings for Google's Gemma models.
-   **`google`**: Settings for the Google Translate API.
-   **`mock`**: A mock translator for testing, which simulates translation by prefixing strings (e.g., `en-US: Hello` -> `mock-ja: Hello`).

**Example:**

```yaml
providers:
    gemini:
        api_key: "YOUR_GEMINI_API_KEY"
        model: "gemini-2.5-flash-lite"
        rpm: 60 # Requests per minute
        tpm: 1000000 # Tokens per minute
        batch_size: 20
```

### 2. `shortcuts`

Shortcuts are reusable configuration blocks defined using YAML anchors (`&`). They help keep your tasks DRY (Don't Repeat Yourself). You can define a default set of options and extend it in other shortcuts or tasks.

-   Use `&<name>` to define a shortcut.
-   Use `*<name>` to reference a shortcut.
-   Use `<<: *<name>` to inherit and merge a shortcut's key-value pairs.

**Example:**

```yaml
shortcuts:
    # A default set of options
    .defaults: &defaults
        translator: "gemini"
        source_lang: "en"
        incremental: true
        cache_path: "path/to/cache_file"

    # A shortcut for shell scripts that inherits from .defaults
    .scripts: &scripts
        <<: *defaults # Inherit all keys from &defaults
        source:
            include: ["**/*.sh", "**/*.ps1"]
        extraction_rules:
            - 'echo "([^"]*)"'
```

### 3. `tasks`

This is the core section where you define the list of translation jobs. Each item in the list is a task object.

#### Common Task Keys:

-   `name`: A descriptive name for the task.
-   `enabled`: Set to `true` or `false` to enable or disable the task.
-   `<<: *shortcut_name`: Inherit settings from a defined shortcut.
-   `target_lang`: The language to translate to (e.g., `"zh-TW"`, `"ja"`).
-   `source`: Specifies which files to include or exclude.
    -   `include`: A list of glob patterns for files to process.
    -   `exclude`: A list of glob patterns for files to ignore.
-   `extraction_rules`: A list of regular expressions used to extract translatable strings from files that are not structured (like shell scripts or markdown). The first capture group (`(...)`) should contain the text to be translated.
-   `output`: Defines how and where to write the translated files.
    -   `in_place`: If `true`, overwrites the source files. Defaults to `false`.
    -   `path`: The directory to save translated files.
    -   `filename`: A pattern for the output filename. Supports placeholders:
        -   `{stem}`: The original filename without the extension.
        -   `{ext}`: The original file extension.
        -   `{target_lang}`: The target language code.
-   `prompts`: (For AI-based translators like Gemini) Custom prompts to guide the translation.
    -   `system`: A system prompt to set the context for the AI (e.g., "You are a professional translator...").

#### The `rules` Dictionary

The `rules` key allows for fine-grained control over the translation of extracted strings. It is a dictionary containing `protect`, `skip`, and `replace` rules. Rules from shortcuts are deep-merged with task-specific rules.

-   `protect`: A list of regex patterns. Any text matching these patterns (e.g., variables like `$VAR` or `${VAR}`) will be protected from being sent to the translator.
-   `skip`: A list of regex patterns. If an entire string matches one of these patterns, it will be skipped and not translated.
-   `replace`: A dictionary of find-and-replace pairs where the key is the pattern to find and the value is the replacement string. This is a powerful **pre-processing** action that performs a substitution on the text _before_ it is evaluated by other rules or sent to the translator. It fully supports Regex capture groups and backreferences (e.g., `\\1`, `\\2`), making it ideal for complex text manipulation or providing authoritative translations for specific patterns.

    **Example**: To automatically format a user tag before translation, you can add a `replace` rule. The example below finds "User: " followed by any characters, captures those characters, and replaces the string with a formatted Chinese version while keeping the original user identifier.

    ```yaml
    # In a task within the config file:
    rules:
        replace:
            # Replaces "User: <name>" with "使用者: <name>" before translation.
            # The \\1 is a backreference to the first capture group (.*).
            "User: (.*)": "使用者: \\1"
    ```

### 4. System-Wide Settings

-   `debug_options`: Configure logging for debugging purposes.
-   `report_options`: Configure translation run reports.

### Comprehensive Task Example

This example defines a task to translate Markdown documentation into Japanese. It inherits from the `.defaults` shortcut, specifies source and output paths, and provides a custom system prompt for the AI translator.

```yaml
# ==============================================================================
# GlocalText Configuration File
# ==============================================================================

project_root: "."

# ------------------------------------------------------------------------------
#  1. Provider Settings
# ------------------------------------------------------------------------------
providers:
    gemini:
        api_key: "YOUR_GEMINI_API_KEY"
        model: "gemini-2.5-flash-lite"

# ------------------------------------------------------------------------------
#  2. Shortcuts: For reusable configuration
# ------------------------------------------------------------------------------
shortcuts:
    .defaults: &defaults
        translator: "gemini"
        source_lang: "en"
        incremental: true
        cache_path: ".glocaltext_cache"

# ------------------------------------------------------------------------------
#  3. Tasks: The core translation jobs
# ------------------------------------------------------------------------------
tasks:
    - name: "Translate Markdown Docs to Japanese"
      enabled: true
      <<: *defaults # Inherit from the defaults shortcut
      target_lang: "ja"
      source:
          include: ["docs/**/*.md"]
          exclude: ["docs/internal/**"]
      extraction_rules:
          # Extract text from within backticks
          - "`([^`]+)`"
      rules:
          protect:
              # Protect code blocks and variables
              - "`[^`]+`"
              - '\w+\.\w+'
          skip:
              # Don't translate version numbers
              - '^v\d+\.\d+\.\d+$'
      output:
          in_place: false
          path: "output/ja" # Place translated files in output/ja/
          filename: "{stem}.{target_lang}.md" # e.g., my_doc.ja.md
      prompts:
          system: "You are a professional translator specializing in technical documentation for a software project. Translate with a formal and clear tone."

# ------------------------------------------------------------------------------
#  4. System-Wide Settings
# ------------------------------------------------------------------------------
debug_options:
    enabled: false
    log_path: "logs/glocaltext_debug.log"

report_options:
    enabled: true
    export_dir: "reports"
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
