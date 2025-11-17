# Integration Tests for GlocalText Translators

This directory contains integration tests that verify the functionality of GlocalText translator implementations in realistic usage scenarios.

## Overview

The integration test suite includes tests for:

-   **MockTranslator**: A mock implementation for testing (no API key required)
-   **GoogleTranslator**: Google Translate API integration
-   **GeminiTranslator**: Google Gemini API integration
-   **GemmaTranslator**: Google Gemma model integration

## Test Organization

```
tests/integration_tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Pytest fixtures and configuration
├── README.md                   # This file
├── test_mock_translator.py     # MockTranslator tests (no API key needed)
├── test_google_translator.py   # GoogleTranslator tests
├── test_gemini_translator.py   # GeminiTranslator tests
└── test_gemma_translator.py    # GemmaTranslator tests
```

## Running Tests

### Run All Integration Tests

```bash
pytest tests/integration_tests/ -v
```

### Run Only Non-Integration Tests (No API Keys Required)

These tests will run without any API keys and should always pass:

```bash
pytest tests/integration_tests/ -v -m "not integration"
```

### Run Only Integration Tests (Requires API Keys)

These tests require valid API keys and will be skipped if keys are not available:

```bash
pytest tests/integration_tests/ -v -m integration
```

### Run Tests for a Specific Translator

```bash
# Mock translator tests (always pass)
pytest tests/integration_tests/test_mock_translator.py -v

# Google translator tests
pytest tests/integration_tests/test_google_translator.py -v

# Gemini translator tests
pytest tests/integration_tests/test_gemini_translator.py -v

# Gemma translator tests
pytest tests/integration_tests/test_gemma_translator.py -v
```

## Environment Variables

The integration tests use the following environment variables for API authentication:

| Variable                   | Description                 | Used By                           |
| -------------------------- | --------------------------- | --------------------------------- |
| `GOOGLE_TRANSLATE_API_KEY` | Google Translate API key    | GoogleTranslator                  |
| `GEMINI_API_KEY`           | Google Gemini/Gemma API key | GeminiTranslator, GemmaTranslator |

### Setting Environment Variables

**Linux/macOS:**

```bash
export GEMINI_API_KEY="your-api-key-here"
export GOOGLE_TRANSLATE_API_KEY="your-api-key-here"
```

**Windows (Command Prompt):**

```cmd
set GEMINI_API_KEY=your-api-key-here
set GOOGLE_TRANSLATE_API_KEY=your-api-key-here
```

**Windows (PowerShell):**

```powershell
$env:GEMINI_API_KEY="your-api-key-here"
$env:GOOGLE_TRANSLATE_API_KEY="your-api-key-here"
```

### Using a `.env` File

You can also create a `.env` file in the project root:

```env
GEMINI_API_KEY=your-api-key-here
GOOGLE_TRANSLATE_API_KEY=your-api-key-here
```

Then load it before running tests:

```bash
# Install python-dotenv if needed
pip install python-dotenv

# Run tests with environment variables loaded
python -c "from dotenv import load_dotenv; load_dotenv()" && pytest tests/integration_tests/ -v
```

## Test Categories

Each translator test file contains tests in the following categories:

1. **Basic Functionality Tests**

    - Translator initialization
    - Simple translation
    - Batch translation
    - Empty input handling

2. **Configuration Tests**

    - Provider settings
    - Custom configuration
    - Rate limiting configuration

3. **Error Handling Tests**

    - Invalid API key handling
    - Network error handling
    - Timeout handling
    - Invalid input handling

4. **Integration Tests** (marked with `@pytest.mark.integration`)
    - Real API translation
    - Real batch translation
    - Rate limiting behavior

## Graceful Degradation

Tests are designed to gracefully handle missing API keys:

-   **Tests without API keys**: Automatically skipped with clear message
-   **Tests with API keys**: Run and verify real API functionality
-   **Mock tests**: Always run regardless of API key availability

## Troubleshooting

### All Integration Tests Are Skipped

**Cause**: API keys are not set in environment variables.

**Solution**: Set the required environment variables as described above.

### Google Translator Tests Fail

**Issue**: `GoogleTranslator` uses the `deep-translator` library which may not require explicit API keys but can be rate-limited.

**Solution**:

-   Ensure you have an active internet connection
-   Be aware of Google Translate rate limits for free tier
-   Consider using `pytest -k "not google"` to skip Google tests temporarily

### Connection Errors

**Issue**: Tests fail with connection errors.

**Solution**:

-   Check your internet connection
-   Verify API keys are valid and not expired
-   Check if your IP is blocked or rate-limited by the API provider

### Import Errors

**Issue**: Tests fail with `ImportError` or `ModuleNotFoundError`.

**Solution**:

-   Ensure all dependencies are installed: `poetry install` or `pip install -e .`
-   Verify you're running tests from the project root directory
-   Check that `PYTHONPATH` includes the `src` directory

## Test Markers

The test suite uses pytest markers to categorize tests:

-   `@pytest.mark.integration`: Tests that require real API calls and keys

You can list all markers with:

```bash
pytest --markers
```

## Coverage

To run tests with coverage reporting:

```bash
pytest tests/integration_tests/ --cov=src/glocaltext/translators --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view the coverage report.

## Contributing

When adding new integration tests:

1. Follow the existing test structure and naming conventions
2. Use appropriate pytest markers (`@pytest.mark.integration` for API-dependent tests)
3. Provide clear test descriptions in docstrings
4. Ensure tests are self-contained and don't depend on execution order
5. Handle API key absence gracefully using fixtures from `conftest.py`
6. Add appropriate error handling and assertions with meaningful messages

## Additional Resources

-   [pytest documentation](https://docs.pytest.org/)
-   [GlocalText main documentation](../../README.md)
-   [Translator API documentation](../../src/glocaltext/translators/)
