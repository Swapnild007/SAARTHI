from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import rag


class LocalKnowledgeTests(unittest.TestCase):
    def test_offline_ingest_and_retrieval(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {
                "SAARTHI_LOCAL_KNOWLEDGE_DB": str(Path(directory) / "knowledge.sqlite3"),
                "SAARTHI_SUPABASE_URL": "",
                "SAARTHI_SUPABASE_SERVICE_ROLE_KEY": "",
                "SAARTHI_EMBEDDING_API_URL": "",
                "SAARTHI_EMBEDDING_API_KEY": "",
                "SAARTHI_EMBEDDING_MODEL": "",
            }
            with patch.dict(os.environ, env, clear=True):
                saved = rag.ingest_text(
                    "SAARTHI uses local retrieval to search private project notes without an embedding API.",
                    title="Offline retrieval", source="test-note.md", collection="tests",
                )
                results = rag.search("private project notes retrieval", collection="tests")
                state = rag.status()
        self.assertEqual(saved["provider"], "sqlite-local")
        self.assertEqual(saved["indexed"], 1)
        self.assertTrue(state["configured"])
        self.assertEqual(state["mode"], "local-offline")
        self.assertEqual(results[0]["title"], "Offline retrieval")
        self.assertGreater(results[0]["similarity"], 0)

    def test_collection_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {
                "SAARTHI_LOCAL_KNOWLEDGE_DB": str(Path(directory) / "knowledge.sqlite3"),
                "SAARTHI_SUPABASE_URL": "",
                "SAARTHI_SUPABASE_SERVICE_ROLE_KEY": "",
                "SAARTHI_EMBEDDING_API_URL": "",
                "SAARTHI_EMBEDDING_API_KEY": "",
                "SAARTHI_EMBEDDING_MODEL": "",
            }
            with patch.dict(os.environ, env, clear=True):
                rag.ingest_text("Confidential payroll planning", title="Payroll", collection="private")
                results = rag.search("payroll planning", collection="public")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
