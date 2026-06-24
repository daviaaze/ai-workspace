"""Tests for IdentifierMasker — PII detection and reversible masking."""

import sys; sys.path.insert(0, "src")
import unittest
from unittest import TestCase
from ai_workspace.agents.safety import IdentifierMasker


class TestIdentifierMasker(TestCase):
    def setUp(self):
        self.masker = IdentifierMasker()

    # ── IP Addresses ───────────────────────────────────────────────────

    def test_masks_ipv4(self):
        masked, mapping = self.masker.mask("Server at 192.168.1.1 is down")
        self.assertNotIn("192.168.1.1", masked)
        self.assertIn("__IP_0__", masked)

    def test_masks_ipv4_placeholder(self):
        masked, _ = self.masker.mask("Connect to 10.0.0.5")
        self.assertNotIn("10.0.0.5", masked)

    def test_masks_multiple_ips(self):
        masked, mapping = self.masker.mask("Hosts: 192.168.1.1, 10.0.0.1")
        self.assertNotIn("192.168.1.1", masked)
        self.assertNotIn("10.0.0.1", masked)
        # Should have placeholders
        placeholders = [k for k in mapping if k.startswith("__IP")]
        self.assertGreaterEqual(len(placeholders), 1)

    def test_restores_ip(self):
        original = "Server at 10.0.0.1"
        masked, mapping = self.masker.mask(original)
        restored = self.masker.restore(masked, mapping)
        self.assertEqual(restored, original)

    # ── Hostnames ──────────────────────────────────────────────────────

    def test_masks_hostname(self):
        masked, mapping = self.masker.mask("Deploy to prod-server-01.example.com")
        self.assertNotIn("prod-server-01.example.com", masked)

    def test_restores_hostname(self):
        original = "Deploy to staging-3.internal.net"
        masked, mapping = self.masker.mask(original)
        restored = self.masker.restore(masked, mapping)
        self.assertEqual(restored, original)

    # ── API Keys / Secrets ─────────────────────────────────────────────

    def test_masks_api_key(self):
        masked, mapping = self.masker.mask("API key: sk-abc123def4567890")
        self.assertNotIn("sk-abc123def4567890", masked)

    def test_masks_bearer_token(self):
        masked, _ = self.masker.mask(
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz1234567890token"
        )
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz1234567890token", masked)

    def test_restores_api_key(self):
        original = "Key: sk-abc123def4567890"
        masked, mapping = self.masker.mask(original)
        restored = self.masker.restore(masked, mapping)
        self.assertEqual(restored, original)

    # ── Email Addresses ────────────────────────────────────────────────

    def test_masks_email(self):
        masked, _ = self.masker.mask("Contact admin@example.com")
        self.assertNotIn("admin@example.com", masked)

    def test_restores_email(self):
        original = "Email user@company.org for support"
        masked, mapping = self.masker.mask(original)
        restored = self.masker.restore(masked, mapping)
        self.assertEqual(restored, original)

    # ── Account IDs / Numbers ──────────────────────────────────────────

    def test_masks_account_id(self):
        masked, _ = self.masker.mask("Account: acc-12345-abcde")
        self.assertNotIn("acc-12345-abcde", masked)

    def test_restores_account_id(self):
        original = "User A-123456789"
        masked, mapping = self.masker.mask(original)
        restored = self.masker.restore(masked, mapping)
        self.assertEqual(restored, original)

    # ── Safe Text (no false positives) ─────────────────────────────────

    def test_leaves_safe_text_unchanged(self):
        text = "Hello, how can I help you today?"
        masked, mapping = self.masker.mask(text)
        self.assertEqual(masked, text)
        self.assertEqual(mapping, {})

    def test_leaves_code_snippets(self):
        code = "def hello(): print('world')"
        masked, _ = self.masker.mask(code)
        self.assertIn("hello", masked)

    # ── Multiple PII Types ─────────────────────────────────────────────

    def test_masks_multiple_types(self):
        text = (
            "Server db-1.internal at 10.0.0.1 has API key sk-abcdefgh123456. "
            "Contact admin@example.com."
        )
        masked, mapping = self.masker.mask(text)
        self.assertNotIn("10.0.0.1", masked)
        self.assertNotIn("db-1.internal", masked)
        self.assertNotIn("sk-abcdefgh123456", masked)
        self.assertNotIn("admin@example.com", masked)
        self.assertGreaterEqual(len(mapping), 3)

    def test_restores_multiple_types(self):
        original = (
            "Host web-01.example.com (10.0.0.1) uses key sk-xyz-secret-key-999. "
            "Notify dev@team.org."
        )
        masked, mapping = self.masker.mask(original)
        restored = self.masker.restore(masked, mapping)
        self.assertEqual(restored, original)

    # ── Provider Gating ────────────────────────────────────────────────

    def test_skip_local_provider(self):
        result = self.masker.mask_if_external(
            "IP: 10.0.0.1", provider="ollama"
        )
        self.assertEqual(result, "IP: 10.0.0.1")  # unchanged

    def test_mask_external_provider(self):
        result = self.masker.mask_if_external(
            "IP: 10.0.0.1", provider="openai"
        )
        self.assertNotIn("10.0.0.1", result)

    # ── Combined Pipeline ──────────────────────────────────────────────

    def test_mask_and_restore_roundtrip(self):
        messages = [
            "Deploy to prod-01 at 192.168.1.1",
            "API key: sk-test-key-1234567890",
            "Normal question about Python",
        ]
        combined = "\n".join(messages)
        masked, mapping = self.masker.mask(combined)
        restored = self.masker.restore(masked, mapping)
        self.assertEqual(restored, combined)

    def test_empty_input(self):
        masked, mapping = self.masker.mask("")
        self.assertEqual(masked, "")
        self.assertEqual(mapping, {})

    def test_no_pii(self):
        masked, mapping = self.masker.mask("What is the weather in London?")
        self.assertEqual(masked, "What is the weather in London?")
        self.assertEqual(mapping, {})


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
