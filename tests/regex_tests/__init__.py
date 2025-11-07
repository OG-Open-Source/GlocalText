"""
Regex Library Test Suite for GlocalText.

This test suite comprehensively tests the Python `regex` library functionality
used by the GlocalText project. It covers:

- Basic matching operations (search, match, fullmatch)
- Substitution operations (sub, subn)
- Pattern matching (word boundaries, character classes, quantifiers)
- Flags (IGNORECASE, MULTILINE, DOTALL, VERBOSE)
- Unicode support (Chinese characters, mixed language text)
- Edge cases (special characters, empty strings, performance)

The suite particularly focuses on validating literal string replacement in
complex text scenarios, which is critical for GlocalText's rule processing.

Run tests with: pytest regex/ -v
"""

__version__ = "1.0.0"
