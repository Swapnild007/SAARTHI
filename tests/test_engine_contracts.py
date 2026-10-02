from __future__ import annotations

import unittest

from backend.work_product import build_work_product, infer_deliverable_type
from backend.engine import (
    ASSISTANT_PROFILES,
    ToolRegistry,
    build_orchestration,
    classify,
    infer_internal_specialist,
)


class EngineContractTests(unittest.TestCase):
    def test_deterministic_calculation(self):
        result = ToolRegistry().execute("system.calculate", {"expression": "30 + 45 * 2"})
        self.assertEqual(result["value"], 120.0)

    def test_unit_conversion(self):
        result = ToolRegistry().execute("system.convert", {"value": 1, "from": "km", "to": "mi"})
        self.assertAlmostEqual(result["result"], 0.621371, places=5)

    def test_time_uses_requested_timezone(self):
        result = ToolRegistry().execute("system.time", {"timezone": "Asia/Kolkata"})
        self.assertEqual(result["timezone"], "Asia/Kolkata")
        self.assertIn(":", result["time"])

    def test_plan_intent_is_classified(self):
        intent = classify("I have three hours and need a schedule")
        self.assertEqual(intent.name, "plan")

    def test_saarthi_routes_plan_internally(self):
        intent = classify("I need a roadmap for launching this project")
        specialist = infer_internal_specialist("saarthi", intent, "I need a roadmap for launching this project")
        self.assertEqual(specialist, "plan")

    def test_saarthi_orchestration_exposes_pipeline(self):
        intent = classify("We have production capacity constraints and increasing downtime. Create an improvement plan.")
        result = build_orchestration(
            "saarthi",
            intent,
            "We have production capacity constraints and increasing downtime. Create an improvement plan.",
            {"industry": "manufacturing"},
        )
        self.assertEqual(result["internal_specialist"], "plan")
        self.assertEqual(result["industry"], "Manufacturing")
        self.assertEqual(
            result["stages"],
            ["understand", "contextualize", "reason", "execute", "verify", "deliver"],
        )
        self.assertTrue(result["decision_frameworks"])
        self.assertTrue(result["artifacts"])

    def test_work_product_contract_is_structured(self):
        result = build_work_product(
            objective="Create a manufacturing improvement plan",
            intent="plan",
            reply="Prioritize downtime reduction.",
            orchestration={
                "industry": "Manufacturing",
                "active_capability": "Plan",
                "internal_specialist": "plan",
                "workflow": ["capacity_planning"],
                "artifacts": ["capacity_plan"],
            },
            tool_results={"system.status": {"service": "saarthi-engine", "state": "ready"}},
            verification={"claims": "runtime path completed"},
        )
        self.assertEqual(result["version"], "1.0")
        self.assertEqual(result["industry"], "Manufacturing")
        self.assertEqual(result["deliverable_type"], "capacity_plan")
        self.assertTrue(result["actions_taken"])
        self.assertTrue(result["evidence"])
        self.assertEqual(result["verification"]["status"], "runtime_verified")

    def test_deliverable_type_defaults_to_intent(self):
        self.assertEqual(infer_deliverable_type("plan", {}), "execution_plan")
        self.assertEqual(infer_deliverable_type("research", {}), "research_brief")

    def test_specialist_profiles_remain_available(self):
        self.assertEqual(
            set(ASSISTANT_PROFILES),
            {"saarthi", "coding", "research", "create", "data_analyst", "analyze", "plan"},
        )


if __name__ == "__main__":
    unittest.main()
