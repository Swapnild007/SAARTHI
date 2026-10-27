"""Regression tests for bounded cloud execution and truthful timeout reporting."""
import asyncio
import importlib
import unittest
from unittest.mock import patch

app_module = importlib.import_module("backend.app")
from backend.engine import OpenAICompatibleProvider


class RuntimeDeadlineTests(unittest.TestCase):
    def test_timeout_is_not_reported_as_success(self):
        async def raise_timeout(*args, **kwargs):
            raise asyncio.TimeoutError()

        request = app_module.CommandRequest(message="Plan a Goa trip", mode="chat")
        with patch.object(app_module.asyncio, "wait_for", side_effect=raise_timeout):
            result = asyncio.run(app_module._execute_command_bounded(request))
        self.assertFalse(result["ok"])
        self.assertEqual(result["provider"], "runtime-timeout")
        self.assertFalse(result["verification"]["verified"])
        self.assertIn("routing", result["reply"])

    def test_provider_timeout_leaves_headroom_for_failover(self):
        with patch.dict("os.environ", {"SAARTHI_LLM_REQUEST_TIMEOUT_SECONDS": "12"}):
            gateway = OpenAICompatibleProvider()
        self.assertLessEqual(gateway.request_timeout, 7.0)


if __name__ == "__main__":
    unittest.main()
