import unittest

from scripts.normalize_rea_evidence import SCHEMA_VERSION, normalize


class ReaEvidenceNormalizerTests(unittest.TestCase):
    def test_projects_provenance_coverage_and_static_only_policy(self):
        raw = {
            "evidence_id": "ev_test",
            "subject": {"name": "SAARTHI", "digest": {"sha256": "a" * 64}},
            "provider": {"id": "rea-javascript-application", "version": "1"},
            "operation": "analyze-javascript-application",
            "confidence": "derived",
            "authority": "shipped-artifact",
            "normalized_result": {
                "statistics": {
                    "relevant_files": 3,
                    "parsed_javascript_files": 2,
                    "parse_failures": 1,
                    "findings": 4,
                },
                "graph": {
                    "coverage": {"status": "partial", "truncated": False},
                    "nodes": [{
                        "node_id": "node-1",
                        "kind": "storage",
                        "identity": {"namespace": "local-storage", "key": "project"},
                        "observations": [{
                            "observation_id": "obs-1",
                            "label": "local-storage",
                            "properties": {"storage_kind": "local-storage", "unsafe_nested": {"secret": "drop"}},
                            "evidence": {
                                "state": "observed",
                                "confidence": "exact",
                                "location": {"available": True, "value": {
                                    "kind": "source-range",
                                    "source": "appforge/app.js",
                                    "start": {"line": 12, "column": 3},
                                    "end": {"line": 12, "column": 20},
                                }},
                            },
                        }],
                    }],
                    "edges": [{
                        "source_node_id": "node-1",
                        "target_node_id": "node-2",
                        "edge_id": "edge-1",
                        "relation": "persists_to",
                        "properties": {"mechanism": "localStorage"},
                        "evidence": {"state": "inferred", "confidence": "high"},
                    }],
                    "limitations": ["Static syntax does not prove runtime execution."],
                },
                "semantic_graph": {
                    "coverage": {"status": "partial", "truncated": False},
                    "nodes": [{"id": "s1"}],
                    "relations": [{"id": "r1"}],
                    "unknowns": [{"id": "u1"}],
                },
                "summary": {"browser_windows": 0, "ipc": {"operations": 0}},
                "integrity_contradictions": [],
                "limitations": ["Coverage is incomplete."],
            },
        }

        result = normalize(raw)

        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["subject"]["scope"], "appforge/")
        self.assertEqual(result["coverage"]["parse_failures"], 1)
        self.assertEqual(result["coverage"]["semantic_unknowns"], 1)
        self.assertEqual(result["summary"]["local_storage_observations"], 1)
        self.assertEqual(result["observations"][0]["location"]["source"], "appforge/app.js")
        self.assertNotIn("unsafe_nested", result["observations"][0]["properties"])
        self.assertFalse(result["policy"]["runtime_behavior_proven"])
        self.assertFalse(result["policy"]["safe_for_model_instructions"])
        self.assertTrue(result["policy"]["requires_human_review"])
        self.assertIn("Static syntax does not prove runtime execution.", result["limitations"])

    def test_rejects_missing_subject_digest(self):
        with self.assertRaisesRegex(ValueError, "subject digest"):
            normalize({
                "evidence_id": "ev_test",
                "subject": {"name": "SAARTHI", "digest": {}},
                "normalized_result": {"graph": {"nodes": [], "edges": []}},
            })


if __name__ == "__main__":
    unittest.main()
