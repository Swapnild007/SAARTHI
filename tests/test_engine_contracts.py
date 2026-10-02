from __future__ import annotations

import unittest

from backend.agent_capabilities import build_runtime_context
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


    def test_all_specialists_have_runnable_capability_contracts(self):
        cases = [
            ("saarthi", "Help me decide how to organize this objective.", "saarthi"),
            ("coding", "Build a Python API endpoint and add tests.", "coding"),
            ("research", "Compare two approaches and identify the evidence needed.", "research"),
            ("create", "Draft a product launch concept and refine the messaging.", "create"),
            ("data_analyst", "Analyze this KPI dataset and identify trends.", "data_analyst"),
            ("analyze", "Analyze the situation, assumptions, risks and root causes.", "analyze"),
            ("plan", "Create a roadmap with dependencies and checkpoints.", "plan"),
        ]
        for assistant, message, expected in cases:
            intent = classify(message)
            orchestration = build_orchestration(assistant, intent, message, {"industry": "manufacturing"})
            self.assertEqual(orchestration["active_capability"], ASSISTANT_PROFILES[expected]["name"])
            expected_internal = None if assistant == "saarthi" and expected == "saarthi" else (expected if assistant == "saarthi" else assistant)
            self.assertEqual(orchestration["internal_specialist"], expected_internal)
            self.assertEqual(orchestration["industry"], "Manufacturing")
            self.assertEqual(len(orchestration["stages"]), 6)
            self.assertTrue(orchestration["workflow"])
            self.assertTrue(orchestration["artifacts"])

    def test_saarthi_internal_route_uses_specialist_industry_mapping(self):
        message = "We have production downtime and capacity pressure. Build a capacity improvement plan."
        intent = classify(message)
        orchestration = build_orchestration("saarthi", intent, message, {"industry": "manufacturing"})
        self.assertEqual(orchestration["active_capability"], "Plan")
        self.assertEqual(orchestration["internal_specialist"], "plan")
        self.assertIn("capacity_plan", orchestration["workflow"])


    def test_all_industries_have_end_to_end_coverage(self):
        expected = {
            "travel": ["flight_options", "train_options", "bike_or_motorbike", "hotel", "airbnb_or_vacation_rental", "lodge"],
            "financial_services": ["cash_flow", "risk", "scenario_analysis"],
            "healthcare": ["care_pathway", "appointment_preparation", "follow_up"],
            "retail": ["product_discovery", "availability", "fulfillment", "returns"],
            "logistics": ["shipment", "route", "warehouse", "delivery_window", "exceptions"],
            "manufacturing": ["production_plan", "machine_capacity", "maintenance", "downtime", "quality", "safety"],
        }
        for industry, required in expected.items():
            runtime = build_runtime_context("saarthi", industry)
            coverage = runtime["industry_coverage"]
            for item in required:
                self.assertIn(item, coverage["coverage"])
            self.assertTrue(coverage["artifact_bundle"])

    def test_all_agents_have_quality_playbooks(self):
        for agent in ("saarthi", "coding", "research", "create", "data_analyst", "analyze", "plan"):
            runtime = build_runtime_context(agent, "manufacturing")
            playbook = runtime["agent_playbook"]
            self.assertTrue(playbook["sequence"])
            self.assertTrue(playbook["quality_gates"])

    def test_specialist_profiles_remain_available(self):
        self.assertEqual(
            set(ASSISTANT_PROFILES),
            {"saarthi", "coding", "research", "create", "data_analyst", "analyze", "plan"},
        )


if __name__ == "__main__":
    unittest.main()
