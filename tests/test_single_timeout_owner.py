"""Guard against duplicate assistant responses from competing timeout mechanisms."""
from pathlib import Path
import unittest

APP = (Path(__file__).resolve().parents[1] / "scripts" / "app.js").read_text(encoding="utf-8")


class SingleTimeoutOwnerTests(unittest.TestCase):
    def test_submit_does_not_install_competing_watchdog(self):
        start = APP.index("const submit=")
        end = APP.index("window.SaarthiApp.voiceTurn=false;", start)
        submit = APP[start:end]
        self.assertNotIn("submitWatchdog=window.setTimeout", submit)
        self.assertIn("Promise.race([", submit)
        self.assertIn("showResponse(", submit)

    def test_user_message_is_persisted_before_request(self):
        start = APP.index("const submit=")
        end = APP.index("window.SaarthiApp.voiceTurn=false;", start)
        submit = APP[start:end]
        self.assertLess(submit.index("appendConversation('user',value)"), submit.index("runCommand(value,mode)"))


if __name__ == "__main__":
    unittest.main()
