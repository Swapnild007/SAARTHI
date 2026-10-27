"""Regression contract: chat history must not be truncated to the model context window."""
from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / "scripts" / "app.js").read_text(encoding="utf-8")


class ChatHistoryRetentionTests(unittest.TestCase):
    def test_saved_thread_keeps_all_messages(self):
        self.assertIn("thread.messages=(conversations[assistant]||[]).slice();", SOURCE)
        self.assertNotIn("thread.messages=(conversations[assistant]||[]).slice(-MAX_CONTEXT_MESSAGES)", SOURCE)

    def test_new_message_preserves_visible_history(self):
        self.assertIn("conversations[currentAssistant]=messages;", SOURCE)
        self.assertNotIn("conversations[currentAssistant]=messages.slice(-MAX_CONTEXT_MESSAGES)", SOURCE)

    def test_reopening_thread_keeps_full_history(self):
        self.assertIn("conversations[currentAssistant]=thread.messages;", SOURCE)

    def test_model_context_remains_bounded(self):
        self.assertIn("conversation:currentConversation().slice(-MAX_CONTEXT_MESSAGES).map(", SOURCE)

    def test_error_recovery_preserves_other_messages(self):
        self.assertIn("conversations[currentAssistant]=filtered;", SOURCE)


if __name__ == "__main__":
    unittest.main()
