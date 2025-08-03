<!-- You cannot delete 3 items in the part of the table of contents, Introduction, Contributing, License -->

# GlocalText

GlocalText is a powerful command-line tool designed to automate and streamline the software localization process. It extracts strings from your source code, translates them using various AI and machine translation providers, and compiles a fully translated version of your project.

Its key feature is a **round-trip workflow**, allowing you to manually refine machine translations and sync your changes back into the system, ensuring your edits are preserved and reused.

---

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

---

## Introduction

GlocalText is a powerful command-line tool designed to automate and streamline the software localization process. It extracts strings from your source code, translates them using various AI and machine translation providers, and compiles a fully translated version of your project.

Its key feature is a **round-trip workflow**, allowing you to manually refine machine translations and sync your changes back into the system, ensuring your edits are preserved and reused.

## Features

- **Automated String Extraction**: Uses customizable regex rules to find user-visible strings in any type of source code.
- **Multi-Provider Support**: Integrates with modern AI providers like Gemini, OpenAI, and Ollama, as well as standard services like Google Translate.
- **Round-Trip Workflow**: Manually edit translated files and use the `sync` command to merge your changes back into the translation cache. Your refinements are never lost.
- **Differential Translation**: Intelligently translates only new or modified strings, saving time and cost.
- **State Management**: Tracks file versions to detect changes and potential conflicts between source and localized files.
- **Configuration over Convention**: Highly customizable through simple YAML files.

## Installation

Install GlocalText using pip:

```bash
pip install glocaltext
```

## Quick Start

Here's a complete workflow example.

### 1. Initialize Your Project

Navigate to your project's root directory and run:

```bash
glocaltext init
```

This creates a `.ogos` directory with two configuration files:

- `i18n-rules.yaml`: Defines rules for finding strings to translate.
- `l10n-rules.yaml`: Configures your target languages and translation provider (e.g., Gemini, OpenAI).

### 2. Configure Your Rules

- **Edit `i18n-rules.yaml`** to define the regex pattern for extracting strings from your code.
- **Edit `l10n-rules.yaml`** to set your target languages and configure your chosen translation provider, including API keys.

### 3. First Run: Machine Translation

Run the localization process:

```bash
glocaltext run .
```

GlocalText will:

1. Scan your source code for strings.
2. Send new strings to your chosen translation provider.
3. Create a translated copy of your project in `.ogos/localized/`.

### 4. Manual Refinement

Browse the files in the `.ogos/localized/` directory. You can now manually edit the translated text in these files to improve quality, fix context-specific issues, or match your brand's tone of voice.

For example, you might change a translated string from `"申請開始..."` to `"應用程式啟動中..."`.

### 5. Sync Your Changes

After making manual edits, sync them back to the GlocalText cache:

```bash
glocaltext sync .
```

This command reads your changes from the `localized` directory and updates the translation cache, storing your edits as a `manual_override`.

### 6. Subsequent Runs

Now, when you run `glocaltext run .` again (e.g., after adding new source code), the compiler will use your synced manual overrides instead of the original machine translation, ensuring your refinements are always preserved.

## Command Reference

### `glocaltext init`

Initializes the configuration files in the `.ogos` directory.

### `glocaltext run [PATH]`

Executes the main localization workflow: extract, translate, and compile.

- **`PATH`**: The path to the project directory to process (default: current directory).
- **`--force`, `-f`**: Force re-translation of all strings, ignoring the cache.
- **`--debug`, `-d`**: Enable verbose debug logging.

### `glocaltext sync [PATH]`

Syncs manual changes from the `localized` directory back to the translation cache.

- **`PATH`**: The path to the project directory to sync (default: current directory).
- **`--debug`, `-d`**: Enable verbose debug logging.

## Configuration

### `i18n-rules.yaml`

Controls how strings are found (Internationalization).

```yaml
source:
  include:
    - "**/*.py" # Glob patterns for files to include
  exclude:
    - "tests/*" # Glob patterns for files to exclude
capture_rules:
  - pattern: '_\("(.*?)"\)' # Regex to find strings
    capture_group: 1 # The regex capture group containing the text
ignore_rules:
  - pattern: "<code>.*?</code>" # Regex for entire blocks to ignore
```

### `l10n-rules.yaml`

Controls how strings are translated (Localization).

```yaml
translation_settings:
  source_lang: "en"
  target_lang: ["ja", "zh-TW"]
  provider: "gemini" # gemini, openai, ollama, or google

provider_configs:
  gemini:
    model: "gemini-1.5-flash"
    api_key: "YOUR_GEMINI_API_KEY"
  openai:
    model: "gpt-4o"
    api_key: "YOUR_OPENAI_API_KEY"
  # ... other provider configs

glossary:
  # Terms that should not be translated
  "GlocalText": "GlocalText"

protection_rules:
  # Regex patterns for substrings to protect from translation (e.g., variables)
  - "{.*?}"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

## License

This repository is licensed under the [MIT License](https://opensource.org/license/MIT).

---

© 2025 [OG-Open-Source](https://github.com/OG-Open-Source). All rights reserved.
