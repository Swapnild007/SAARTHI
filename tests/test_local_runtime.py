from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from backend.engine import OpenAICompatibleProvider


class LocalRuntimeRoutingTests(unittest.TestCase):
    def test_local_route_needs_no_api_key_and_is_preferred(self):
        env = {
            "SAARTHI_LOCAL_LLM_API_URL": "http://127.0.0.1:11434/v1",
            "SAARTHI_LOCAL_LLM_MODEL": "qwen2.5:7b",
            "SAARTHI_PREFER_LOCAL": "true",
            "SAARTHI_LOCAL_ONLY": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            provider = OpenAICompatibleProvider()
        self.assertTrue(provider.configured)
        self.assertEqual(provider.routes[0]["name"], "local-runtime")
        self.assertTrue(provider.routes[0]["local"])
        self.assertEqual(provider.routes[0]["model"], "qwen2.5:7b")
        self.assertNotIn("key", provider.routes[0])

    def test_local_first_keeps_cloud_fallback_when_configured(self):
        env = {
            "SAARTHI_LOCAL_LLM_API_URL": "http://127.0.0.1:11434/v1",
            "SAARTHI_LOCAL_LLM_MODEL": "qwen2.5:7b",
            "SAARTHI_LLM_API_URL": "https://openrouter.ai/api/v1",
            "SAARTHI_LLM_API_KEY": "test-key",
            "SAARTHI_LLM_MODEL": "openrouter/free",
            "SAARTHI_PREFER_LOCAL": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            provider = OpenAICompatibleProvider()
        self.assertEqual([route["local"] for route in provider.routes], [True, False])
        self.assertEqual(provider.routes[1]["key"], "test-key")

    def test_local_only_never_keeps_cloud_route(self):
        env = {
            "SAARTHI_LOCAL_LLM_API_URL": "http://127.0.0.1:11434/v1",
            "SAARTHI_LOCAL_LLM_MODEL": "qwen2.5:7b",
            "SAARTHI_LLM_API_URL": "https://openrouter.ai/api/v1",
            "SAARTHI_LLM_API_KEY": "test-key",
            "SAARTHI_LLM_MODEL": "openrouter/free",
            "SAARTHI_LOCAL_ONLY": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            provider = OpenAICompatibleProvider()
        self.assertTrue(provider.configured)
        self.assertEqual(len(provider.routes), 1)
        self.assertTrue(provider.routes[0]["local"])

    def test_local_only_without_local_runtime_is_unconfigured(self):
        env = {
            "SAARTHI_LLM_API_URL": "https://openrouter.ai/api/v1",
            "SAARTHI_LLM_API_KEY": "test-key",
            "SAARTHI_LLM_MODEL": "openrouter/free",
            "SAARTHI_LOCAL_ONLY": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            provider = OpenAICompatibleProvider()
        self.assertFalse(provider.configured)


if __name__ == "__main__":
    unittest.main()
