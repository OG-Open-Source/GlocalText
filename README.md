# GlocalText

GlocalText is a powerful command-line tool that automates text translation using a highly intuitive, **firewall-style `rules` system**. It processes text by evaluating a list of rules from top to bottom, giving you precise, predictable control over your localization workflow.

---

## Table of Contents

-   [Introduction](#introduction)
-   [Key Features](#key-features)
-   [Prerequisites](#prerequisites)
-   [Installation](#installation)
-   [Quick Start](#quick-start)
-   [Configuration (`.ogos/glocaltext/configs/main.yaml`)](#configuration-ogosglocaltextconfigsmainyaml)
-   [Usage](#usage)
-   [Examples](#examples)
-   [Troubleshooting](#troubleshooting)
-   [FAQ](#faq)
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

## Prerequisites

Before installing GlocalText, ensure your system meets the following requirements:

-   **Python**: Version 3.10 or higher
-   **Operating System**: Windows, macOS, or Linux
-   **API Keys**: You'll need an API key for your chosen translation provider:

    -   **Gemini**: Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
    -   **Google Translate**: Requires a Google Cloud API key with the Translation API enabled

-   **Configuration Reusability**: Use `shortcuts` and `rulesets` to define reusable configuration snippets, making your setup clean and DRY.
-   **Glob Pattern Matching**: Precisely include or exclude files for translation using `glob` patterns.
-   **Flexible Output Control**: Choose to either modify original files directly (`in_place: true`) or create new, translated versions in a specified path (`in_place: false`).
-   **Incremental Translation**: Save time and cost by only translating new or modified content.

## Installation

Install GlocalText using pip:

```bash
pip install GlocalText
```

To verify the installation, check the version:

```bash
glocaltext --version
# Output: glocaltext 4.0.0b2
```

## Quick Start

Here's the fastest way to get started with GlocalText:

### 1. Create Your Project Structure

```bash
# Navigate to your project root
cd your-project

# Create the required directory structure
mkdir -p .ogos/glocaltext/configs
```

### 2. Create a Minimal Configuration

Create a file at `.ogos/glocaltext/configs/main.yaml`:

```yaml
providers:
    gemini:
        api_key: 'YOUR_GEMINI_API_KEY_HERE'

shortcuts:
    .defaults:
        translator: 'gemini'
        source_lang: 'en'

tasks:
    - name: 'Translate to Japanese'
      enabled: true
      extends: '.defaults'
      target_lang: 'ja'
      source:
          include: ['**/*.md']
      output:
          in_place: false
          path: 'translated/ja'
```

### 3. Run Your First Translation

```bash
# From anywhere inside your project directory
glocaltext

# Or use dry-run mode to preview what will be translated
glocaltext --dry-run
```

That's it! GlocalText will translate all Markdown files in your project to Japanese and save them in the `translated/ja` directory.

## Configuration (`.ogos/glocaltext/configs/main.yaml`)

`GlocalText` is controlled by a central YAML configuration file, which must be named **`main.yaml`** or **`main.yml`**. This file acts as the command center for all translation tasks.

GlocalText discovers the project's root directory by searching for an **`.ogos`** folder. Your configuration file must be located at: `<PROJECT_ROOT>/.ogos/glocaltext/configs/main.yaml`. All paths within the configuration file (e.g., `source` or `output` paths) are relative to the project root.

Here is a breakdown of the configuration structure.

### 1. `providers`

This section is where you configure the settings for different translation providers. You only need to configure the ones you plan to use.

-   **`gemini`**: Settings for Google's Gemini models.
    -   `api_key`: Your Gemini API key.
    -   `model`: The specific model to use (e.g., `gemini-1.5-flash-latest`).
    -   `rpm`, `tpm`: Rate and token limits.
    -   `batch_size`: Number of concurrent requests.
-   **`gemma`**: Settings for Google's Gemma models.
-   **`google`**: Settings for the Google Translate API.
-   **`mock`**: A mock translator for testing, which simulates translation by prefixing strings (e.g., `Hello` -> `[MOCK] Hello`).

**Example:**

```yaml
providers:
    gemini:
        api_key: 'YOUR_GEMINI_API_KEY'
        model: 'gemini-1.5-flash-latest'
        rpm: 60 # Requests per minute
        tpm: 1000000 # Tokens per minute
        batch_size: 20
```

### 2. `shortcuts`

Shortcuts are reusable configuration blocks that help keep your tasks DRY (Don't Repeat Yourself). You can define a block of settings and then inherit from it in other shortcuts or tasks using the `extends` key.

-   **`.defaults`**: A special shortcut that is automatically inherited by **all** tasks.
-   **Custom Shortcuts**: You can define any other shortcut (e.g., `.scripts`) and inherit from it explicitly.
-   **`extends`**: Use this key to specify which shortcut to inherit from.

**Example:**

```yaml
shortcuts:
    # 1. A default set of options automatically applied to all tasks.
    .defaults:
        translator: 'gemini'
        source_lang: 'en'
        incremental: true

    # 2. A reusable ruleset for protecting variables.
    .script_rules:
        rules:
            protect:
                - '\$\w+' # Protects $VAR

    # 3. A shortcut for shell scripts that inherits from .defaults.
    .scripts:
        extends: '.defaults'
        source:
            include: ['**/*.sh', '**/*.ps1']
```

### 3. `tasks`

This is the core section where you define the list of translation jobs. Each item in the list is a task object.

#### Common Task Keys:

-   `name`: A descriptive name for the task.
-   `enabled`: Set to `true` or `false` to enable or disable the task.
-   `extends`: Inherit settings from a defined shortcut (e.g., `extends: .scripts`). This can also be used inside a `rules` block to inherit from a ruleset.
-   `target_lang`: The language to translate to (e.g., `"zh-TW"`, `"ja"`).
-   `source`: Specifies which files to include or exclude.
    -   `include`: A list of glob patterns for files to process.
    -   `exclude`: A list of glob patterns for files to ignore.
-   `extraction_rules`: A list of regular expressions used to extract translatable strings from files that are not structured (like shell scripts or markdown). The first capture group (`(...)`) should contain the text to be translated.
-   `task_id`: (Optional) A unique identifier for this task. If not provided, GlocalText will automatically generate a stable UUID based on the task's key configuration (source language, target language, source files, and extraction rules). This ensures that cache files remain consistent even if you rename the task. You can also manually specify a custom `task_id` to have full control over cache file naming.
-   `incremental`: Set to `true` to enable caching, which allows GlocalText to skip re-translating content that hasn't changed since the last run. Defaults to `false`.
-   `cache_path`: (Optional) Specifies a custom directory path (relative to the project root) for storing translation cache files. If not specified, defaults to `.ogos/glocaltext/caches/`. The cache file for each task will be automatically named based on the task's UUID (`task_id`), ensuring stability across task renames (e.g., `<task_id>.json`). **Note:** This is a directory path, not a file path. For example, setting `cache_path: "my_cache"` will create cache files at `<project_root>/my_cache/<task_id>.json`.
-   `output`: Defines how and where to write the translated files.
    -   `in_place`: If `true`, overwrites the source files. Defaults to `false`.
    -   `path`: (Required when `in_place` is `false`) The directory path (relative to the project root) where translated files will be saved. **Important:** This is a directory path, not a file path. For example, `path: "output/ja"` will create translated files in `<project_root>/output/ja/`. Even if you specify `path: ".cache.json"`, GlocalText will create a directory named `.cache.json` and place files inside it.
    -   `filename`: A pattern for the output filename. Supports placeholders:
        -   `{stem}`: The original filename without the extension.
        -   `{source_lang}`: The source language code.
        -   `{target_lang}`: The target language code.
        -   `{extension}`: The original file extension without the dot.
-   `prompts`: (For AI-based translators like Gemini) Custom prompts to guide the translation. Supports template variables for dynamic content.

    -   `user`: A custom user prompt template. Supports the following variables:
        -   `{source_lang}`: The source language code
        -   `{target_lang}`: The target language code
        -   `{texts_json_array}`: The JSON array of texts to translate (automatically injected)
    -   **Example**:

        ```yaml
        prompts:
            user: |
                You are a professional technical translator specializing in software documentation.
                Translate the following texts from {source_lang} to {target_lang}.
                Maintain technical accuracy and use appropriate terminology.

                Texts to translate:
                {texts_json_array}
        ```

#### Default Prompts for AI Translators

GlocalText provides default prompts for AI-based translators. You can override these by specifying custom prompts in the `prompts` configuration as shown above.

**Gemini Default Prompt:**

```
You are a professional translation engine. Your task is to translate a list of texts from {source_lang} to {target_lang}.

You MUST return a JSON object with a single key "translations" that contains a list of the translated strings.
The list of translated strings must have the same number of items as the input list.
If a translation is not possible, return the original text for that item. Do not add explanations.

Translate the following texts:
{texts_json_array}
```

**Gemma Default Prompt:**

```
<start_of_turn>user
You are a professional translation engine. Your task is to translate a list of texts from {source_lang} to {target_lang}.

You MUST return a JSON object with a single key "translations" that contains a list of the translated strings.
The list of translated strings must have the same number of items as the input list.
If a translation is not possible, return the original text for that item. Do not add explanations.

Translate the following texts:
{texts_json_array}<end_of_turn>
<start_of_turn>model
```

**Note**: The prompts support the following template variables:

-   `{source_lang}`: The source language code
-   `{target_lang}`: The target language code
-   `{texts_json_array}`: The JSON array of texts to translate (automatically injected)

#### The `rules` Dictionary

The `rules` key allows for fine-grained control over the translation of extracted strings. It is a dictionary containing `protect`, `skip`, and `replace` rules. Rules from shortcuts are deep-merged with task-specific rules.

-   `protect`: A list of regex patterns. Any text matching these patterns (e.g., variables like `$VAR` or `${VAR}`) will be protected from being sent to the translator.
-   `skip`: A list of regex patterns. If an entire string matches one of these patterns, it will be skipped and not translated.
-   `replace`: A dictionary of regex patterns to replacement strings. This action supports capture groups and backreferences (e.g., `\1`, `\2`), making it ideal for complex text manipulation or providing authoritative translations for specific patterns.

        **Example**: To automatically format a user tag before translation, you can add a `replace` rule. The example below finds "User: " followed by any characters, captures those characters, and replaces the string with a formatted Chinese version while keeping the original user identifier.

        ```yaml
        # In a task within the config file:
        rules:
            replace:
                # Replaces 'User: <name>' with '使用者: <name>' before translation.
                # The \1 is a backreference to the first capture group (.*).
                # Note the use of single quotes to avoid issues with YAML escape sequences.
                'User: (.*)': '使用者: \1'
        ```

        **Inheriting Rulesets**: You can also inherit a complete set of rules from a shortcut. This is useful for applying a standard set of rules (like protecting variables) across multiple tasks.

        ```yaml
        shortcuts:
            .script_rules:
                rules:
                    protect:
                        - '\$\w+' # Protects $VAR

        tasks:
            - name: 'Translate Scripts'
              extends: '.defaults'
              # ... other task settings
              rules:
                  extends: '.script_rules' # Inherit all rules from .script_rules
                  skip:
                      - 'Do not translate this line' # Add a task-specific rule
        ```

### Comprehensive Task Example

This example defines a task to translate Markdown documentation into Japanese. It inherits from `.defaults`, specifies source and output paths, and provides a custom system prompt for the AI translator.

File: `.ogos/glocaltext/configs/main.yaml`

```yaml
# ==============================================================================
# GlocalText Configuration File
# ==============================================================================

# ------------------------------------------------------------------------------
#  1. Provider Settings
# ------------------------------------------------------------------------------
providers:
    gemini:
        api_key: 'YOUR_GEMINI_API_KEY'
        model: 'gemini-1.5-flash-latest'

# ------------------------------------------------------------------------------
#  2. Shortcuts: For reusable configuration
# ------------------------------------------------------------------------------
shortcuts:
    .defaults:
        translator: 'gemini'
        source_lang: 'en'
        incremental: true

# ------------------------------------------------------------------------------
#  3. Tasks: The core translation jobs
# ------------------------------------------------------------------------------
tasks:
    - name: 'Translate Markdown Docs to Japanese'
      enabled: true
      extends: '.defaults' # Inherit from the defaults shortcut
      target_lang: 'ja'
      source:
          include: ['docs/**/*.md']
          exclude: ['docs/internal/**']
      extraction_rules:
          # Extract text from within backticks
          - '`([^`]+)`'
      rules:
          protect:
              # Protect code blocks and variables
              - '`[^`]+`'
              - '\w+\.\w+'
          skip:
              # Don't translate version numbers
              - '^v\d+\.\d+\.\d+$'
      output:
          in_place: false
          path: 'output/ja' # Place translated files in output/ja/
          filename: '{stem}.{target_lang}.md' # e.g., my_doc.ja.md
      prompts:
          system: 'You are a professional translator specializing in technical documentation for a software project. Translate with a formal and clear tone.'
```

## Usage

To run `GlocalText`, simply execute the command from anywhere inside your project directory (i.e., any directory that is a child of the folder containing `.ogos`).

### Basic Command

```bash
glocaltext
```

GlocalText will:

1. Search for the `.ogos` folder to locate your project root
2. Load the configuration from `.ogos/glocaltext/configs/main.yaml`
3. Process all enabled tasks defined in the configuration
4. Display a summary report of the translation results

### Command-Line Options

-   `--debug`: Enables debug level logging for troubleshooting.

    ```bash
    glocaltext --debug
    ```

-   `--incremental`: Overrides all task-level settings to run in incremental mode, translating only new or modified content. This saves time and API costs by skipping previously translated content.

    ```bash
    glocaltext --incremental
    ```

-   `--dry-run`: Performs a full run without making any actual changes or API calls. This is extremely useful for:

    -   Testing your configuration
    -   Previewing what text will be translated
    -   Verifying file paths and glob patterns
    -   Checking rules without consuming API quota

    ```bash
    glocaltext --dry-run
    ```

-   `-v`, `--version`: Show the version number and exit.
    ```bash
    glocaltext --version
    ```

### Combining Options

You can combine multiple options for more control:

```bash
# Dry run with debug logging
glocaltext --dry-run --debug

# Incremental translation with debug logging
glocaltext --incremental --debug
```

## Examples

### Example 1: Translating Documentation to Multiple Languages

```yaml
providers:
    gemini:
        api_key: 'YOUR_API_KEY'
        model: 'gemini-1.5-flash-latest'

shortcuts:
    .defaults:
        translator: 'gemini'
        source_lang: 'en'
        incremental: true
        source:
            include: ['docs/**/*.md']
            exclude: ['docs/internal/**', '**/node_modules/**']

tasks:
    - name: 'Translate docs to Japanese'
      enabled: true
      extends: '.defaults'
      target_lang: 'ja'
      output:
          in_place: false
          path: 'docs/ja'

    - name: 'Translate docs to Traditional Chinese'
      enabled: true
      extends: '.defaults'
      target_lang: 'zh-TW'
      output:
          in_place: false
          path: 'docs/zh-tw'
```

### Example 2: Translating Shell Scripts with Variable Protection

```yaml
providers:
    gemini:
        api_key: 'YOUR_API_KEY'

shortcuts:
    .script_rules:
        rules:
            protect:
                # Protect shell variables
                - '\$\w+'              # $VAR
                - '\$\{[^}]+\}'        # ${VAR}
                # Protect command substitutions
                - '\$\([^)]+\)'        # $(command)
                # Protect file paths
                - '\/[\w\/\.-]+'       # /path/to/file

tasks:
    - name: 'Translate Shell Scripts'
      enabled: true
      translator: 'gemini'
      source_lang: 'en'
      target_lang: 'zh-TW'
      source:
          include: ['scripts/**/*.sh']
      extraction_rules:
          # Extract comments
          - '(?:^|\s)#\s+(.+)$'
          # Extract echo statements
          - 'echo\s+["\']([^"\']+)["\']'
      rules:
          extends: '.script_rules'
          skip:
              # Skip shebang lines
              - '^#!/.*$'
      output:
          in_place: false
          path: 'scripts/translated'
          filename: '{stem}.{target_lang}{extension}'
```

### Example 3: In-Place Translation with Custom Prompts

```yaml
providers:
    gemini:
        api_key: 'YOUR_API_KEY'

tasks:
    - name: 'Update README to Chinese'
      enabled: true
      translator: 'gemini'
      source_lang: 'en'
      target_lang: 'zh-TW'
      source:
          include: ['README.md']
      output:
          in_place: true # Overwrites the original file
      prompts:
          user: |
              You are translating a README file for a technical project.
              Use formal technical terminology appropriate for {target_lang}.
              Keep code examples, URLs, and command-line syntax unchanged.

              Translate these texts from {source_lang} to {target_lang}:
              {texts_json_array}
```

### Example 4: Using Replace Rules for Authoritative Translations

```yaml
providers:
    gemini:
        api_key: 'YOUR_API_KEY'

tasks:
    - name: 'Translate with Fixed Terms'
      enabled: true
      translator: 'gemini'
      source_lang: 'en'
      target_lang: 'zh-TW'
      source:
          include: ['content/**/*.md']
      rules:
          replace:
              # Replace specific terms before translation
              'User: (.*)': '使用者: \1'
              'Admin: (.*)': '管理員: \1'
              'Error: (.*)': '錯誤: \1'
          protect:
              # Protect brand names and technical terms
              - 'GlocalText'
              - 'GitHub'
              - 'API'
      output:
          in_place: false
          path: 'content/zh-tw'
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: "Could not find .ogos directory"

**Cause**: GlocalText cannot locate the project root.

**Solution**:

1. Ensure you have an `.ogos` directory in your project root
2. Verify you're running the command from within your project directory
3. Check directory permissions

```bash
# Create the directory structure if missing
mkdir -p .ogos/glocaltext/configs
```

#### Issue: "API key is missing"

**Cause**: The API key for your chosen provider is not configured.

**Solution**:

1. Add your API key to the configuration file:
    ```yaml
    providers:
        gemini:
            api_key: 'YOUR_ACTUAL_API_KEY_HERE'
    ```
2. Never commit API keys to version control. Consider using environment variables or a `.env` file (excluded from git)

#### Issue: "No files matched the source patterns"

**Cause**: The `include` patterns in your task configuration don't match any files.

**Solution**:

1. Use `--dry-run` to verify which files are being matched
2. Check your glob patterns are correct:
    ```yaml
    source:
        include: ['**/*.md'] # Matches all .md files recursively
        exclude: ['node_modules/**'] # Exclude node_modules
    ```
3. Ensure paths are relative to the project root

#### Issue: "Rate limit exceeded"

**Cause**: You've exceeded the API rate limits for your provider.

**Solution**:

1. Reduce the `batch_size` in your provider settings:
    ```yaml
    providers:
        gemini:
            batch_size: 10 # Lower value = slower but safer
    ```
2. Adjust `rpm` (requests per minute) and `tpm` (tokens per minute) limits
3. Use `--incremental` to translate only new content

#### Issue: "Translation quality is poor"

**Cause**: Default prompts may not suit your specific needs.

**Solution**:

1. Customize the `prompts.user` field with specific instructions:
    ```yaml
    prompts:
        user: |
            You are a technical translator specializing in [YOUR DOMAIN].
            Maintain consistency with these terms: [LIST KEY TERMS].
            Translate from {source_lang} to {target_lang}:
            {texts_json_array}
    ```
2. Use `protect` rules to preserve technical terms
3. Use `replace` rules for authoritative translations of specific phrases

#### Issue: "Protected text is still being translated"

**Cause**: The regex pattern in your `protect` rule may be incorrect.

**Solution**:

1. Test your regex patterns at [regex101.com](https://regex101.com/)
2. Remember to escape special characters: `\.`, `\$`, `\(`, etc.
3. Use the `--debug` flag to see what's being sent to the translator

## FAQ

### Q: Can I use multiple translation providers in one configuration?

**A**: Yes! You can specify different `translator` values for different tasks:

```yaml
tasks:
    - name: 'Translate docs with Gemini'
      translator: 'gemini'
      # ... task config

    - name: 'Translate UI with Google Translate'
      translator: 'google'
      # ... task config
```

### Q: How does incremental translation work?

**A**: When `incremental: true` is set, GlocalText:

1. Calculates a hash of each source text
2. Stores translations in a cache file (`.ogos/glocaltext/caches/<task_id>.json`)
3. On subsequent runs, only translates texts whose hash has changed
4. Reuses cached translations for unchanged texts

This dramatically reduces API costs and translation time for large projects.

### Q: What's the difference between `protect` and `skip` rules?

**A**:

-   **`protect`**: Prevents specific patterns **within** a text from being translated, but the rest of the text is still translated. Example: Protecting `$VAR` in "Please set $VAR before running" → "請在運行前設置 $VAR"
-   **`skip`**: Prevents the **entire** text from being translated if it matches the pattern. Example: Skipping version numbers like "v1.2.3" entirely.

### Q: Can I translate binary files or databases?

**A**: No, GlocalText is designed for text-based files only. It works best with:

-   Markdown (`.md`)
-   Code files with extractable strings (`.js`, `.py`, `.sh`, etc.)
-   Configuration files (`.yaml`, `.json`, `.xml`)
-   Plain text files

### Q: How do I handle file encodings?

**A**: GlocalText automatically handles UTF-8 encoded files. If you have files in other encodings:

1. Convert them to UTF-8 first
2. Process them with GlocalText
3. Convert back if necessary

### Q: Can I preview translations before saving?

**A**: Yes! Use the `--dry-run` flag:

```bash
glocaltext --dry-run
```

This shows you exactly what will be translated without making any changes or consuming API quota.

### Q: How do I translate only specific sections of a file?

**A**: Use `extraction_rules` to define regex patterns that capture only the text you want:

```yaml
extraction_rules:
    - '(?:^|\s)#\s+(.+)$' # Only comments in shell scripts
    - '"([^"]+)"' # Only quoted strings
```

The first capture group `(...)` defines what will be translated.

### Q: What happens if translation fails mid-task?

**A**: If `incremental: true` is enabled, GlocalText:

1. Saves all successfully translated texts to the cache
2. On the next run, skips the already-translated texts
3. Resumes from where it left off

This makes it safe to interrupt and restart translations.

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
