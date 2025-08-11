import unittest
from unittest.mock import MagicMock

from glocaltext.core.config import L10nConfig, ProtectionRule
from glocaltext.core.postprocessor import PostProcessor


class TestPostProcessor(unittest.TestCase):
    def setUp(self):
        """Set up a mock config for testing."""
        self.mock_config = MagicMock(spec=L10nConfig)
        self.mock_config.protection_rules = [
            ProtectionRule(pattern=r"\{[a-zA-Z_]+\}"),  # e.g., {name}
            ProtectionRule(pattern=r"%[sd]"),  # e.g., %s, %d
        ]
        self.postprocessor = PostProcessor(self.mock_config)

    def test_restore_simple_placeholder(self):
        """Test restoring a single, simple placeholder."""
        original = "Hello, {name}!"
        translated = "Bonjour, {nom}!"
        expected = "Bonjour, {name}!"
        result = self.postprocessor.restore_protected_patterns(original, translated)
        self.assertEqual(result, expected)

    def test_restore_multiple_placeholders(self):
        """Test restoring multiple placeholders in order."""
        original = "File {filename} has {count} lines."
        translated = "Le fichier {fichier} contient {nombre} lignes."
        expected = "Le fichier {filename} contient {count} lignes."
        result = self.postprocessor.restore_protected_patterns(original, translated)
        self.assertEqual(result, expected)

    def test_restore_different_placeholder_types(self):
        """Test restoring different types of placeholders (e.g., {} and %s)."""
        original = "Welcome, %s! You have {count} messages."
        translated = "Bienvenue, %s ! Vous avez {nombre} messages."
        expected = "Bienvenue, %s ! Vous avez {count} messages."
        result = self.postprocessor.restore_protected_patterns(original, translated)
        self.assertEqual(result, expected)

    def test_no_placeholders_to_restore(self):
        """Test behavior when the original string has no placeholders."""
        original = "Hello, world!"
        translated = "Bonjour, le monde!"
        expected = "Bonjour, le monde!"
        result = self.postprocessor.restore_protected_patterns(original, translated)
        self.assertEqual(result, expected)

    def test_mismatched_placeholder_counts(self):
        """Test that the original translation is returned if placeholder counts differ."""
        original = "User {user} has {count} items."
        translated = "L'utilisateur {utilisateur} a des objets."  # Placeholder missing
        expected = "L'utilisateur {utilisateur} a des objets."  # Should not change
        result = self.postprocessor.restore_protected_patterns(original, translated)
        self.assertEqual(result, expected)

    def test_placeholder_with_special_chars(self):
        """Test placeholder with characters that might be tricky for regex."""
        original = "User_{user_id}"
        translated = "Utilisateur_{id_utilisateur}"
        # Assuming the rule is simple, e.g., \{[a-zA-Z_]+\}
        # Let's adjust the mock for this test case
        self.mock_config.protection_rules = [ProtectionRule(pattern=r"\{[a-zA-Z_]+\}")]
        self.postprocessor = PostProcessor(self.mock_config)
        original = "Hello, {user_id}"
        translated = "Bonjour, {id_utilisateur}"
        expected = "Bonjour, {user_id}"
        result = self.postprocessor.restore_protected_patterns(original, translated)
        self.assertEqual(result, expected)

    def test_placeholders_at_start_and_end(self):
        """Test placeholders at the beginning and end of the string."""
        original = "{greeting}, world, {farewell}"
        translated = "{salutation}, monde, {adieu}"
        expected = "{greeting}, monde, {farewell}"
        result = self.postprocessor.restore_protected_patterns(original, translated)
        self.assertEqual(result, expected)

    def test_restore_dollar_variables(self):
        """Test restoring variables prefixed with a dollar sign."""
        self.mock_config.protection_rules.append(
            ProtectionRule(pattern=r"\$[a-zA-Z_]+")
        )
        self.postprocessor = PostProcessor(self.mock_config)
        original = "The price is $price and the total is $total_price."
        translated = "El precio es $precio y el total es $precio_total."
        expected = "El precio es $price y el total es $total_price."
        result = self.postprocessor.restore_protected_patterns(original, translated)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
