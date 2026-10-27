"""Regression checks for the SAARTHI chat composer event wiring.

Run: python -m unittest discover -s tests -p 'test_chat_send_wiring.py'
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ChatSendWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.app = (ROOT / "scripts" / "app.js").read_text(encoding="utf-8")

    def test_one_authoritative_send_controller(self):
        self.assertNotIn("__SAARTHI_DIRECT_SEND__", self.html)
        self.assertNotIn("stopImmediatePropagation()", self.html)
        self.assertIn('scripts/app.js', self.html)

    def test_send_button_is_submittable(self):
        self.assertRegex(
            self.html,
            r'<button[^>]*id="sendCommand"[^>]*type="submit"',
        )

    def test_main_controller_handles_touch_and_form_submit(self):
        self.assertIn("sendButton?.addEventListener('click',event=>", self.app)
        self.assertIn("composerForm?.addEventListener('submit',event=>", self.app)
        self.assertIn("submit();", self.app)

    def test_main_controller_has_recovery_path(self):
        self.assertIn("const resetComposerState=", self.app)
        self.assertIn("resetComposerState(sendButton);", self.app)
        self.assertIn("submitWatchdog=window.setTimeout", self.app)


if __name__ == "__main__":
    unittest.main()
