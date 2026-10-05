from __future__ import annotations

import ast
import json
import math
import operator
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .attachments import inspect_attachments, provider_content_parts
from .agent_capabilities import agent_capability, build_runtime_context, INDUSTRY_PACKS
from .data_analysis import analyze_dataset, build_chart, recommend_visuals
from .analysis_engine import analyze_text
from .research import research
from .work_product import build_work_product
from urllib.request import Request, urlopen


def _requested_chart_type(message: str) -> str | None:
    text = str(message or "").lower()
    if not re.search(r"\b(chart|graph|plot|visuali[sz]ation|heat ?map)\b", text):
        return None
    if re.search(r"\bheat ?map\b", text):
        return "heatmap"
    for name in ("waterfall", "funnel", "gauge", "radar", "histogram", "box", "bubble", "stacked bar", "stacked-bar", "area"):
        if re.search(r"\b" + re.escape(name) + r"\b", text):
            return name.replace("-", "_").replace(" ", "_")
    if re.search(r"\bdonut\b", text):
        return "donut"
    if re.search(r"\bpie\b", text):
        return "pie"
    if re.search(r"\bscatter\b", text):
        return "scatter"
    if re.search(r"\bline\b", text):
        return "line"
    if re.search(r"\bbar\b", text):
        return "bar"
    return "bar"


def _sample_chart_spec(chart_type: str) -> dict[str, Any]:
    if chart_type == "pie":
        return {
            "chartType": "pie",
            "meta": {"title": "Sample distribution"},
            "nameKey": "category",
            "valueKey": "value",
            "data": [
                {"category": "Product A", "value": 35},
                {"category": "Product B", "value": 25},
                {"category": "Product C", "value": 20},
                {"category": "Product D", "value": 12},
                {"category": "Product E", "value": 8},
            ],
        }
    if chart_type == "heatmap":
        return {
            "chartType": "heatmap",
            "meta": {"title": "Sample heat map"},
            "rowLabels": ["North", "South", "East", "West"],
            "colLabels": ["Q1", "Q2", "Q3", "Q4"],
            "data": [
                {"row": "North", "values": [72, 81, 68, 90]},
                {"row": "South", "values": [64, 76, 73, 84]},
                {"row": "East", "values": [88, 79, 91, 86]},
                {"row": "West", "values": [59, 71, 67, 78]},
            ],
        }
    labels = ["A", "B", "C", "D", "E"]
    values = [35, 25, 20, 12, 8]
    if chart_type == "line":
        return {
            "chartType": "line",
            "meta": {"title": "Sample trend"},
            "xKey": "category",
            "series": [{"dataKey": "value", "label": "Value"}],
            "data": [{"category": label, "value": value} for label, value in zip(labels, values)],
        }
    if chart_type == "scatter":
        return {
            "chartType": "scatter",
            "meta": {"title": "Sample relationship"},
            "xKey": "x",
            "series": [{"dataKey": "y", "label": "Y"}],
            "data": [{"x": x, "y": y} for x, y in [(1, 35), (2, 25), (3, 20), (4, 12), (5, 8)]],
        }
    return {
        "chartType": "bar",
        "meta": {"title": "Sample values"},
        "xKey": "category",
        "series": [{"dataKey": "value", "label": "Value"}],
        "data": [{"category": label, "value": value} for label, value in zip(labels, values)],
    }


def _sample_kpi_dashboard() -> list[dict[str, Any]]:
    return [
        {
            "chartType": "bar",
            "meta": {"title": "Sales by product"},
            "xKey": "product",
            "series": [{"dataKey": "sales", "label": "Sales"}],
            "data": [
                {"product": "Product A", "sales": 310},
                {"product": "Product B", "sales": 260},
                {"product": "Product C", "sales": 220},
                {"product": "Product D", "sales": 180},
                {"product": "Product E", "sales": 150},
            ],
        },
        {
            "chartType": "line",
            "meta": {"title": "Monthly revenue trend"},
            "xKey": "month",
            "series": [{"dataKey": "revenue", "label": "Revenue"}],
            "data": [
                {"month": "Jan", "revenue": 420},
                {"month": "Feb", "revenue": 510},
                {"month": "Mar", "revenue": 470},
                {"month": "Apr", "revenue": 590},
                {"month": "May", "revenue": 560},
            ],
        },
        {
            "chartType": "pie",
            "meta": {"title": "Market share distribution"},
            "nameKey": "channel",
            "valueKey": "share",
            "data": [
                {"channel": "Online", "share": 45},
                {"channel": "Retail", "share": 30},
                {"channel": "Wholesale", "share": 15},
                {"channel": "Direct", "share": 10},
            ],
        },
        {
            "chartType": "heatmap",
            "meta": {"title": "Regional performance vs target"},
            "rowLabels": ["North", "South", "East", "West"],
            "colLabels": ["Q1", "Q2", "Q3", "Q4"],
            "data": [
                {"row": "North", "values": [78, 82, 85, 79]},
                {"row": "South", "values": [65, 70, 72, 68]},
                {"row": "East", "values": [90, 92, 88, 85]},
                {"row": "West", "values": [55, 60, 62, 58]},
            ],
        },
    ]


@dataclass(frozen=True)
class Intent:
    name: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class PlanStep:
    id: str
    label: str
    status: str = "ready"


class ToolRegistry:
    """Small, explicit tool boundary. Add tools here; never execute arbitrary code."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "system.time": self._time,
            "system.date": self._date,
            "system.calculate": self._calculate,
            "system.convert": self._convert,
            "system.status": self._status,
        }

    def names(self) -> list[str]:
        return sorted(self._tools)

    def execute(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool not registered: {name}")
        return tool(args or {})

    @staticmethod
    def _time(args: dict[str, Any]) -> dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        tz_name = str((args or {}).get("timezone") or "UTC")
        try:
            from zoneinfo import ZoneInfo
            local = now_utc.astimezone(ZoneInfo(tz_name))
            return {
                "utc": now_utc.isoformat(),
                "local": local.isoformat(),
                "timezone": tz_name,
                "time": local.strftime("%H:%M:%S"),
                "date": local.strftime("%Y-%m-%d"),
            }
        except Exception:
            return {
                "utc": now_utc.isoformat(),
                "local": now_utc.isoformat(),
                "timezone": "UTC",
                "time": now_utc.strftime("%H:%M:%S"),
                "date": now_utc.strftime("%Y-%m-%d"),
            }

    @staticmethod
    def _date(args: dict[str, Any]) -> dict[str, Any]:
        result = ToolRegistry._time(args)
        return {"date": result["date"], "timezone": result["timezone"], "local": result["local"]}

    @staticmethod
    def _calculate(args: dict[str, Any]) -> dict[str, Any]:
        expression = str((args or {}).get("expression") or "").strip()
        if not expression or len(expression) > 200:
            raise ValueError("invalid calculation expression")
        allowed = {
            ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
            ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
            ast.USub: operator.neg, ast.UAdd: operator.pos,
        }
        def evaluate(node: ast.AST) -> float:
            if isinstance(node, ast.Expression):
                return evaluate(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and math.isfinite(float(node.value)):
                return float(node.value)
            if isinstance(node, ast.UnaryOp) and type(node.op) in allowed:
                return allowed[type(node.op)](evaluate(node.operand))
            if isinstance(node, ast.BinOp) and type(node.op) in allowed:
                return allowed[type(node.op)](evaluate(node.left), evaluate(node.right))
            raise ValueError("unsupported calculation")
        value = evaluate(ast.parse(expression, mode="eval"))
        return {"expression": expression, "value": value}

    @staticmethod
    def _convert(args: dict[str, Any]) -> dict[str, Any]:
        value = float((args or {}).get("value"))
        source = str((args or {}).get("from") or "").lower().strip()
        target = str((args or {}).get("to") or "").lower().strip()
        length = {"km": 1.0, "kilometer": 1.0, "kilometers": 1.0, "mi": 1.609344, "mile": 1.609344, "miles": 1.609344}
        mass = {"kg": 1.0, "kilogram": 1.0, "kilograms": 1.0, "lb": 0.45359237, "lbs": 0.45359237, "pound": 0.45359237, "pounds": 0.45359237}
        if source in length and target in length:
            result = value * length[source] / length[target]
        elif source in mass and target in mass:
            result = value * mass[source] / mass[target]
        elif source in {"c", "celsius"} and target in {"f", "fahrenheit"}:
            result = value * 9 / 5 + 32
        elif source in {"f", "fahrenheit"} and target in {"c", "celsius"}:
            result = (value - 32) * 5 / 9
        else:
            raise ValueError("unsupported unit conversion")
        return {"value": value, "from": source, "to": target, "result": result}

    @staticmethod
    def _status(_: dict[str, Any]) -> dict[str, Any]:
        return {"service": "saarthi-engine", "state": "ready"}


ASSISTANT_PROFILES: dict[str, dict[str, str]] = {
    "saarthi": {
        "name": "Saarthi",
        "role": "personal AI assistant",
        "instruction": (
            "Be the user's primary personal assistant and general thinking partner. This is the broadest environment. "
            "Handle everyday questions, voice-assistant style requests, personal organization, learning, planning, decisions, writing, problem-solving and practical tasks. "
            "Use the current Saarthi conversation as the only conversational working memory for this turn. Do not assume context from another assistant or another thread. "
            "For decisions, separate facts, assumptions, constraints, trade-offs and options and leave decision authority with the user. "
            "For planning, convert outcomes into ordered actions, dependencies and checkpoints. For problems, diagnose before prescribing. "
            "When a specialist task clearly belongs to Coding, Research, Create, Analyze or Plan, route it internally to that capability while keeping the user in the Saarthi workspace; do not force a manual assistant switch. "
            "This environment may still answer ordinary coding, research, writing, analysis or planning questions when they are part of a broader personal-assistant request, because Saarthi is the general assistant. "
            "Stay calm, practical and conversational. Do not fabricate facts, citations, access, memory, tool results or completed actions."
        ),
        "boundary": "general personal assistance; broad requests are allowed, with specialist handoff for clearly specialized work",
    },
    "coding": {
        "name": "AI Coding",
        "role": "software engineering assistant",
        "instruction": (
            "Act only as a software engineering specialist. Design, implement, debug, refactor, test, review and explain software. "
            "Treat the Coding conversation as a separate workspace. Never use or reveal messages, memories or conclusions from Saarthi or another assistant. "
            "If the user asks a general personal, life, shopping, casual, relationship or other non-software question, do not answer it as Coding. "
            "Briefly state that AI Coding is restricted to software work and direct the user to Saarthi for general assistance. "
            "For coding requests, work directly from supplied code, errors, repository context or requirements. If source code is not supplied and the task is clearly to build something, produce a complete runnable solution instead of asking for a snippet. "
            "Prefer production-ready code, explicit file boundaries, tests and concrete debugging steps. Never claim to have inspected a repository, file, build or test unless that evidence is present."
        ),
        "boundary": "software engineering only",
    },
    "research": {
        "name": "Research",
        "role": "research and evidence synthesis assistant",
        "instruction": (
            "Act only as a research specialist. Investigate questions, gather and compare evidence, explain source quality, identify uncertainty and synthesize findings. "
            "Treat the Research conversation as a separate workspace. Never use or reveal messages, memories or conclusions from another assistant. "
            "If the user asks for coding, personal assistance, creative drafting, data analysis or execution planning rather than research, do not answer that task as Research. "
            "Briefly state the scope boundary and direct the user to the appropriate specialist or Saarthi. Never invent sources or citations."
        ),
        "boundary": "research, evidence and synthesis only",
    },
    "create": {
        "name": "Create",
        "role": "creative and writing assistant",
        "instruction": (
            "Act only as a creative production specialist. Create, draft, rewrite, edit, brainstorm and shape writing, concepts, prompts and creative assets. "
            "Treat the Create conversation as a separate workspace. Never use or reveal messages, memories or conclusions from another assistant. "
            "If the user asks for coding, research, data analysis, personal assistance or detailed execution planning rather than a creative output, do not answer that task as Create. "
            "Briefly state the scope boundary and direct the user to the appropriate specialist or Saarthi. Match the requested format, audience and tone."
        ),
        "boundary": "creative production and writing only",
    },
    "data_analyst": {
        "name": "Data Analyst",
        "role": "quantitative data analysis and visualization specialist",
        "instruction": (
            "Act only as a quantitative data analysis specialist. Work with spreadsheets, CSV/JSON datasets, metrics, statistics, trends, anomalies, forecasting, SQL/Python reasoning and dashboards. "
            "Treat the Data Analyst conversation as a separate workspace. Never use or reveal messages, memories or conclusions from another assistant. "
            "When data is attached, use the supplied data rather than inventing values. State data quality issues, assumptions and limitations. "
            "When a chart materially improves the answer or the user asks for one, produce the visualization directly using a <saarthi-chart>{JSON}</saarthi-chart> block. Supported chartType values are bar, line, pie, donut, scatter, bubble, area, stacked_bar, histogram, box, radar, funnel, gauge, waterfall and heatmap. For a heatmap, use chartType \"heatmap\" and data as rows with a \"values\" array; include rowLabels and colLabels when available. The JSON must be valid. Never return Python/matplotlib/seaborn code instead of the visualization block. If the user requests sample data, generate clearly labeled synthetic sample values and render the chart directly. Every plotted value must come from supplied data or an explicitly labeled calculation. "
            "When the user asks for a process, relationship or flow diagram rather than a quantitative chart, produce a <saarthi-diagram>{JSON}</saarthi-diagram> block with title, nodes and edges. "
            "Do not fabricate measurements. Do not answer unrelated creative writing, general personal assistance or software implementation requests as Data Analyst."
        ),
        "boundary": "quantitative data, statistics, datasets and visualization only",
    },
    "analyze": {
        "name": "Analyze",
        "role": "data, document and visual analysis assistant",
        "instruction": (
            "Act only as an analysis specialist. Analyze data, documents, images, systems and situations by separating evidence, patterns, assumptions, risks, trade-offs and conclusions. "
            "Treat the Analyze conversation as a separate workspace. Never use or reveal messages, memories or conclusions from another assistant. "
            "If the user asks for general personal assistance, creative writing, software implementation, source research or a step-by-step execution plan rather than analysis, do not answer that task as Analyze. "
            "Briefly state the scope boundary and direct the user to the appropriate specialist or Saarthi. Do not invent missing data."
        ),
        "boundary": "analysis of data, documents, visuals and situations only",
    },
    "plan": {
        "name": "Plan",
        "role": "planning and execution strategy assistant",
        "instruction": (
            "Act only as a planning specialist. Turn goals into ordered actions, dependencies, constraints, checkpoints, contingencies and next steps. "
            "Treat the Plan conversation as a separate workspace. Never use or reveal messages, memories or conclusions from another assistant. "
            "If the user asks for general conversation, coding implementation, research evidence, creative drafting or analytical interpretation rather than planning, do not answer that task as Plan. "
            "Briefly state the scope boundary and direct the user to the appropriate specialist or Saarthi. Do not silently make decisions on the user's behalf."
        ),
        "boundary": "planning and execution strategy only",
    },
}

def assistant_profile(assistant: str | None) -> dict[str, str]:
    return ASSISTANT_PROFILES.get(str(assistant or "").lower(), ASSISTANT_PROFILES["saarthi"])

SPECIALIST_BY_INTENT = {
    "research": "research",
    "search": "research",
    "analyze": "analyze",
    "plan": "plan",
    "calculate": "data_analyst",
    "convert": "data_analyst",
}

def infer_internal_specialist(assistant: str, intent: Intent, message: str) -> str | None:
    """Choose one hidden execution capability only when the objective is clearly specialized."""
    if assistant != "saarthi":
        return assistant
    if intent.name in SPECIALIST_BY_INTENT:
        return SPECIALIST_BY_INTENT[intent.name]
    text = str(message or "").lower()
    candidates = [
        ("coding", r"\b(code|coding|debug|refactor|repository|repo|api|sdk|python|javascript|typescript|github|vercel|deploy|bug)\b"),
        ("data_analyst", r"\b(dataset|csv|excel|spreadsheet|kpi|metrics|statistics|chart|graph|dashboard|heatmap|visualization|forecast)\b"),
        ("research", r"\b(research|deep dive|investigate|sources?|evidence|literature)\b"),
        ("analyze", r"\b(analy[sz]e|compare|break down|trade[- ]?offs?|evaluate|assess|diagnose)\b"),
        ("plan", r"\b(plan|roadmap|schedule|prioriti[sz]e|timeline|dependencies|strategy)\b"),
        ("create", r"\b(write|draft|rewrite|story|copy|prompt|presentation|compose)\b"),
    ]
    ranked = sorted(
        ((name, len(re.findall(pattern, text, re.IGNORECASE))) for name, pattern in candidates),
        key=lambda item: item[1],
        reverse=True,
    )
    if ranked and ranked[0][1] > 0 and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]):
        return ranked[0][0]
    return None

def infer_industry(message: str, context: dict[str, Any] | None = None) -> str | None:
    """Infer an operating industry from explicit context or strong domain signals in the objective."""
    if isinstance(context, dict):
        explicit = str(context.get("industry") or "").strip().lower()
        if explicit in INDUSTRY_PACKS:
            return explicit
    text = str(message or "").lower()
    signals = {
        "travel": r"\b(flight|hotel|visa|itinerary|destination|tourism|trip|travell?ing|airline|luggage)\b",
        "financial_services": r"\b(bank|banking|portfolio|transaction|cash flow|investment|loan|credit|compliance|financial|revenue|margin)\b",
        "healthcare": r"\b(patient|hospital|clinic|clinical|care pathway|appointment|healthcare|medical|diagnosis|outcome)\b",
        "retail": r"\b(retail|e-?commerce|product|inventory|order|conversion|basket|promotion|customer|shopping)\b",
        "logistics": r"\b(shipment|warehouse|route|delivery|supply chain|lead time|fleet|dispatch|fulfillment)\b",
        "manufacturing": r"\b(manufacturing|production line|downtime|oee|yield|defect|maintenance|throughput|machine capacity)\b",
    }
    scores = {industry: len(re.findall(pattern, text, re.IGNORECASE)) for industry, pattern in signals.items()}
    winner = max(scores, key=scores.get) if scores else None
    return winner if winner and scores[winner] > 0 else None


def build_orchestration(assistant: str, intent: Intent, message: str, context: dict[str, Any]) -> dict[str, Any]:
    resolved_industry = infer_industry(message, context)
    internal = infer_internal_specialist(assistant, intent, message)
    execution_agent = internal or assistant
    runtime = build_runtime_context(execution_agent, resolved_industry)
    route_name = assistant_profile(execution_agent)["name"]
    return {
        "mode": "orchestrated",
        "entry": assistant_profile(assistant)["name"],
        "active_capability": route_name,
        "internal_specialist": internal,
        "industry": runtime["industry"],
        "workflow": runtime["industry_agent_mapping"] or runtime["workflows"],
        "decision_frameworks": runtime["industry_decision_frameworks"],
        "constraints": runtime["industry_constraints"],
        "artifacts": runtime["industry_artifacts"],
        "industry_coverage": runtime.get("industry_coverage", {}),
        "agent_playbook": runtime.get("agent_playbook", {}),
        "stages": ["understand", "contextualize", "reason", "execute", "verify", "deliver"],
        "handoff": "internal" if internal and assistant == "saarthi" else "direct",
    }

def specialist_boundary_response(assistant: str, message: str) -> str | None:
    """Deterministic scope guard for specialist agents before any model call."""
    text = message.strip().lower()
    if assistant == "saarthi":
        return None

    outside_patterns = {
        "coding": r"\b(weather|recipe|restaurant|dating|relationship|movie|travel|personal advice|what should i eat)\b",
        "research": r"\b(write code|debug|fix this code|implement|refactor|deploy|build this app)\b",
        "create": r"\b(debug|implement|refactor|sql query|python script|analyze this dataset|calculate|research this)\b",
        "analyze": r"\b(write a|draft an email|write an email|write a story|write a poem|code this|implement)\b",
        "data_analyst": r"\b(write a story|write a poem|draft an email|relationship advice|casual chat)\b",
        "plan": r"\b(debug|write code|implement|research and cite|write a poem|casual chat|what is the weather)\b",
    }
    pattern = outside_patterns.get(assistant)
    if pattern and re.search(pattern, text, re.IGNORECASE):
        target = {
            "coding": "Saarthi", "research": "Research", "create": "Create",
            "analyze": "Analyze", "data_analyst": "Data Analyst", "plan": "Plan"
        }.get(assistant, "Saarthi")
        if assistant == "coding":
            target = "Saarthi"
        return f"{ASSISTANT_PROFILES[assistant]['name']} is restricted to {ASSISTANT_PROFILES[assistant]['boundary']}. Please use {target} for this request."
    return None




class LLMProvider:
    name = "deterministic"

    def generate(self, *, message: str, intent: Intent, context: dict[str, Any], assistant: str = "saarthi") -> tuple[str, dict[str, Any] | None]:
        raise NotImplementedError


def _parse_tabular_attachment(item: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    tab = item.get("tabular") if isinstance(item, dict) else None
    if isinstance(tab, dict) and isinstance(tab.get("columns"), list):
        cols = [str(c) for c in tab["columns"]]
        raw_rows = tab.get("analysis_rows") or tab.get("preview") or []
        rows = [{cols[i]: row[i] if i < len(row) else None for i in range(len(cols))} for row in raw_rows if isinstance(row, list)]
        return cols, rows
    return [], []


def _numeric_profile(columns: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    profile = []
    for col in columns:
        vals = []
        missing = 0
        for row in rows:
            v = row.get(col)
            if v is None or str(v).strip() == "":
                missing += 1
                continue
            try:
                vals.append(float(str(v).replace(",", "").replace("%", "")))
            except (TypeError, ValueError):
                pass
        if vals:
            profile.append({"column": col, "numeric_values": len(vals), "missing": missing, "min": min(vals), "max": max(vals), "mean": sum(vals) / len(vals)})
    return {"rows_profiled": len(rows), "numeric_columns": profile}


def analyze_attachments_for_data(attachments: list[dict[str, Any]]) -> dict[str, Any]:
    datasets = []
    for item in attachments:
        cols, rows = _parse_tabular_attachment(item)
        if cols:
            datasets.append({
                "name": item.get("name", "dataset"),
                "columns": cols,
                "rows": rows,
                "row_count": int((item.get("tabular") or {}).get("rows", len(rows))),
                "profile": _numeric_profile(cols, rows),
            })
    return {"datasets": datasets, "dataset_count": len(datasets)}


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible gateway with ordered routes and automatic failover.

    Configure SAARTHI_LLM_ROUTES_JSON as a JSON array of:
    {"name":"primary","url":"https://.../v1","key":"...","model":"..."}.
    If unset, the legacy SAARTHI_LLM_API_URL/KEY/MODEL variables remain supported.
    """
    name = "ai-gateway"

    def __init__(self) -> None:
        raw = os.getenv("SAARTHI_LLM_ROUTES_JSON", "").strip()
        routes: list[dict[str, str]] = []
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    routes = [r for r in parsed if isinstance(r, dict) and r.get("key") and r.get("url") and r.get("model")]
            except json.JSONDecodeError:
                routes = []
        if not routes:
            routes = [{
                "name": os.getenv("SAARTHI_LLM_PROVIDER_NAME", "OpenRouter"),
                "url": os.getenv("SAARTHI_LLM_API_URL", "https://openrouter.ai/api/v1"),
                "key": os.getenv("SAARTHI_LLM_API_KEY", ""),
                "model": os.getenv("SAARTHI_LLM_MODEL", "openrouter/free"),
            }]
        self.routes = routes
        self.last_route = routes[0].get("name", "unknown") if routes else "unavailable"
        self.last_failures: list[dict[str, str]] = []

    @property
    def configured(self) -> bool:
        return bool(self.routes and any(r.get("url") and r.get("key") and r.get("model") for r in self.routes))

    def _request(self, route: dict[str, str], *, message: str, system: str, context: dict[str, Any], assistant: str) -> tuple[str, dict[str, Any] | None]:
        inspected = inspect_attachments(context.get("attachments") if isinstance(context, dict) else [])
        _, content_parts = provider_content_parts(message, inspected)
        conversation = context.get("conversation", []) if isinstance(context, dict) else []
        messages = [{"role": "system", "content": system}]
        if isinstance(conversation, list):
            # The frontend stores the current user turn before calling the API.
            # Exclude that duplicate turn; attachments belong to the current user message below.
            prior = conversation[:-1] if conversation and isinstance(conversation[-1], dict) and conversation[-1].get("role") == "user" else conversation
            for item in prior[-12:]:
                if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
                    continue
                text_content = str(item.get("content") or "").strip()
                if text_content:
                    messages.append({"role": item["role"], "content": text_content})
        messages.append({"role": "user", "content": content_parts if len(content_parts) > 1 else content_parts[0]["text"]})
        payload = {
            "model": route["model"],
            "messages": messages,
            "temperature": 0.3,
            "usage": {"include": True},
        }
        request = Request(
            route["url"].rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {route['key']}",
                "HTTP-Referer": "https://swapnild007.github.io/SAARTHI/",
                "X-Title": "SAARTHI",
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
        usage = body.get("usage") if isinstance(body, dict) else None
        reply = str(body["choices"][0]["message"]["content"]).strip()
        self.last_route = route.get("name", route.get("model", "unknown"))
        return reply, usage if isinstance(usage, dict) else None

    def generate(self, *, message: str, intent: Intent, context: dict[str, Any], assistant: str = "saarthi") -> tuple[str, dict[str, Any] | None]:
        if not self.configured:
            raise RuntimeError("no AI gateway route is configured")
        orchestration = context.get("orchestration", {}) if isinstance(context, dict) else {}
        internal_specialist = orchestration.get("internal_specialist") if isinstance(orchestration, dict) else None
        active_assistant = str(internal_specialist or assistant)
        # Internal capability routing must never change Saarthi's user-facing identity.
        # When the user enters through Saarthi, the model always speaks as Saarthi;
        # the specialist is used only as hidden execution/knowledge context.
        profile = assistant_profile(assistant if assistant == "saarthi" else active_assistant)
        runtime_capabilities = build_runtime_context(active_assistant, context.get("industry") if isinstance(context, dict) else None)
        agent_knowledge = runtime_capabilities.get("agent_knowledge", {})
        coding_context = ""
        if profile["name"] == "AI Coding":
            has_code = bool(re.search(r"\b(def|class|function|const|let|var|import|from|SELECT|<\\/?[A-Za-z])\b", message, re.IGNORECASE))
            generation_request = bool(re.search(r"\b(write|create|build|generate|implement|make|develop|scaffold|code)\b", message, re.IGNORECASE))
            coding_context = (
                " Code or code-like material is present. Review and transform the supplied material directly."
                if has_code else
                " This is a generative coding request without supplied source. Produce the requested runnable code."
                if generation_request else
                " No source code is present. Answer normally unless a missing snippet is essential."
            )
        attachment_hint = ""
        if context.get("attachments"):
            attachment_hint = (
                " Attachments are available in the request context. Use their extracted contents and images. "
                "For Data Analyst, never invent values that are not in the supplied dataset."
            )
        chart_hint = ""
        research_hint = ""
        analyst_knowledge_hint = ""
        if active_assistant == "data_analyst":
            analyst_methods = agent_knowledge.get("methods", {}) if isinstance(agent_knowledge, dict) else {}
            analyst_failures = agent_knowledge.get("failure_modes", []) if isinstance(agent_knowledge, dict) else []
            analyst_knowledge_hint = (
                " Data Analyst specialist rules: deterministic engine owns numerical work. "
                f"Method families: {json.dumps(analyst_methods, separators=(',', ':'))}. "
                f"Check these failure modes: {', '.join(str(x) for x in analyst_failures[:10])}. "
                "Use weighted numerator/denominator rates when available. "
                "Treat forecasts as estimates and state model selection and limitations."
            )
        if assistant == "research":
            brief = context.get("execution_results", {}).get("research.brief", {}) if isinstance(context, dict) else {}
            research_hint = (
                " A deterministic research brief is available in execution_results.research.brief. "
                "Use only its retrieved sources and evidence for factual source-backed claims. "
                "Cite source URLs exactly as supplied. Distinguish retrieved evidence from inference, "
                "state uncertainty and do not invent sources, quotes, dates or findings."
            )
        if active_assistant == "data_analyst":
            chart_hint = (
                " For charts and heat maps use <saarthi-chart>{JSON}</saarthi-chart>. Supported chartType values are bar, line, pie, donut, scatter, bubble, area, stacked_bar, histogram, box, radar, funnel, gauge, waterfall and heatmap. A heatmap must use data rows shaped as {row:<label>,values:[numbers]}; include rowLabels and colLabels when available. For diagrams use <saarthi-diagram>{JSON}</saarthi-diagram>. Never emit Python/matplotlib/seaborn code when a visualization was requested. "
                "Keep JSON valid and concise. Do not put prose inside these blocks."
            )
        system = (
            f"You are {profile['name']}, the {profile['role']} inside SAARTHI, a calm personal AI assistant. "
            f"{profile['instruction']} {coding_context}{attachment_hint}{chart_hint}{research_hint} "
            "Treat the selected assistant as the user's current working environment, not as a superficial label. "
            "Answer the user's actual request first. Do not reveal hidden chain-of-thought. "
            "Never output internal safety classifications, moderation labels, policy checks, routing metadata or phrases such as 'User Safety: safe' unless the user explicitly asks about safety classification. "
            "Never claim a tool ran unless its result is present. Do not invent access to tools, files, browsing, memory or external services. "
            f"The user-facing assistant boundary is: {profile.get('boundary', 'general assistance')}. Enforce that boundary explicitly. "
            f"Runtime capability focus: {runtime_capabilities['focus']}. "
            + ("Internal capability routing is enabled. The internal specialist is invisible to the user; never identify it, describe it as a separate assistant, claim the request is outside its scope, or ask the user to switch modes. Use its knowledge and workflow silently, then answer as Saarthi."
               if assistant == "saarthi" else "")
            + f" Supported capabilities: {', '.join(runtime_capabilities['capabilities'])}. "
            f"Preferred workflows: {', '.join(runtime_capabilities['workflows'])}. Expected output forms: {', '.join(runtime_capabilities['outputs'])}. "
            f"Active industry context: {runtime_capabilities['industry'] or 'none'}. "
            f"Industry vocabulary: {', '.join(runtime_capabilities['industry_vocabulary']) or 'none'}. "
            f"Industry workflows: {', '.join(runtime_capabilities['industry_workflows']) or 'none'}. "
            f"Industry KPIs: {', '.join(runtime_capabilities['industry_kpis']) or 'none'}. "
            f"Industry-specific workflows for this assistant: {', '.join(runtime_capabilities['industry_agent_mapping']) or 'none'}. "
            f"Industry constraints: {', '.join(runtime_capabilities['industry_constraints']) or 'none'}. "
            f"Industry decision frameworks: {', '.join(runtime_capabilities['industry_decision_frameworks']) or 'none'}. "
            f"Industry work products: {', '.join(runtime_capabilities['industry_artifacts']) or 'none'}. "
            f"Industry journey coverage: {', '.join(runtime_capabilities.get('industry_coverage', {}).get('coverage', [])) or 'none'}. "
            f"Industry artifact bundle: {', '.join(runtime_capabilities.get('industry_coverage', {}).get('artifact_bundle', [])) or 'none'}. "
            f"Agent playbook sequence: {', '.join(runtime_capabilities.get('agent_playbook', {}).get('sequence', [])) or 'none'}. "
            f"Agent knowledge principles: {' | '.join(agent_knowledge.get('principles', [])) or 'none'}. "
            f"Agent quality gates: {', '.join(agent_knowledge.get('quality_gates', [])) or 'none'}. "
            f"{analyst_knowledge_hint} "
            "Treat these principles as execution guidance, not as a source of factual claims. "
            "When an industry is active, make the answer materially domain-aware: use the industry's terminology, relevant workflow, constraints, KPIs and decision framework where applicable. "
            "Prefer a decision-ready work product over generic advice. Do not merely mention the industry name. "
            "Format answers for human reading: avoid long wall-of-text paragraphs. For explanations, use a short opening answer followed by compact headings, bullets or numbered steps when there are multiple ideas. Keep paragraphs to roughly 2-4 sentences. Use Markdown headings, bullets, numbered lists, tables and bold emphasis when they improve scanability. Do not output Markdown emphasis markers in a malformed way such as '* **text**'. For simple factual questions, answer directly in 1-3 short paragraphs or a concise list. "
            "For broad or end-to-end requests, cover the important journey without producing an unnecessarily long wall of prose: lead with a concise executive answer, then use compact headings, bullets or tables, and put secondary diagnostics in structured sections. "
            "Do not repeat the user's request, internal routing, or capability names. The user should experience one coherent Saarthi intelligence system, not a chain of bots. "
            "SAARTHI is an intelligence operating system, not a collection of personas: orchestrate the selected capability internally, preserve conversation continuity, and move from understanding to a verified deliverable. "
            "If the request contains enough information to act, act first and state only material assumptions; ask questions only when missing information would materially change the result."
        )
        failures: list[dict[str, str]] = []
        for route in self.routes[:2]:
            try:
                reply, usage = self._request(route, message=message, system=system, context=context, assistant=assistant)
                chart_type = _requested_chart_type(message) if active_assistant == "data_analyst" else None
                sample_requested = bool(re.search(r"\b(sample|synthetic|example|demo)\b", message, re.IGNORECASE))
                dashboard_requested = bool(re.search(r"\b(kpi|dashboard)\b", message, re.IGNORECASE))
                if active_assistant == "data_analyst" and sample_requested and dashboard_requested and not context.get("attachments"):
                    specs = _sample_kpi_dashboard()
                    kpi_table = (
                        "| KPI | Value | Target | Variance |\n"
                        "| --- | ---: | ---: | ---: |\n"
                        "| Total Sales | $1,250,000 | $1,200,000 | +4.2% |\n"
                        "| Gross Margin | $375,000 | $360,000 | +4.2% |\n"
                        "| Units Sold | 125,000 | 120,000 | +4.2% |\n"
                        "| Customer Satisfaction | 87% | 85% | +2 p.p. |\n"
                        "| Employee Turnover | 12% | 15% | -3 p.p. |"
                    )
                    reply = (
                        "### KPI dashboard\n\n"
                        "Sample synthetic data for demonstration.\n\n"
                        + kpi_table
                        + "".join("\n\n<saarthi-chart>" + json.dumps(spec, separators=(",", ":")) + "</saarthi-chart>" for spec in specs)
                    )
                elif chart_type and sample_requested and not context.get("attachments"):
                    spec = _sample_chart_spec(chart_type)
                    intro = {
                        "pie": "Here is a sample distribution using synthetic data.",
                        "bar": "Here is a sample comparison using synthetic data.",
                        "line": "Here is a sample trend using synthetic data.",
                        "scatter": "Here is a sample relationship using synthetic data.",
                        "heatmap": "Here is a sample heatmap using synthetic data."
                    }.get(chart_type, "Here is a sample visualization using synthetic data.")
                    reply = intro + "\n\n<saarthi-chart>" + json.dumps(spec, separators=(",", ":")) + "</saarthi-chart>"
                self.last_failures = failures
                return reply, usage
            except Exception as exc:
                failures.append({"route": route.get("name", route.get("model", "unknown")), "error": str(exc)[:240]})
        self.last_failures = failures
        detail = "; ".join(
            f"{item.get('route', 'unknown')}: {item.get('error', 'failed')}"
            for item in failures[-3:]
        )
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"all configured AI gateway routes failed{suffix}")


def classify(message: str, requested_mode: str = "chat") -> Intent:
    """Autonomous intent router.

    The user-facing entry point is always Saarthi. UI mode is not allowed to
    select a specialist. Explicit system commands remain available, while
    ordinary language is scored across capabilities so mixed requests can be
    handled without manual agent selection.
    """
    text = str(message or "").strip().lower()
    explicit = {
        "/research": ("research", 1.0, "explicit command"),
        "/search": ("search", 1.0, "explicit command"),
        "/analyze": ("analyze", 1.0, "explicit command"),
        "/remember": ("remember", 1.0, "explicit command"),
        "/recall": ("recall", 1.0, "explicit command"),
        "/tasks": ("task", 1.0, "explicit command"),
        "/remind": ("remind", 1.0, "explicit command"),
        "/workflows": ("workflow", 1.0, "explicit command"),
        "/briefing": ("briefing", 1.0, "explicit command"),
        "/system": ("system", 1.0, "explicit command"),
        "/settings": ("settings", 1.0, "explicit command"),
        "/voice": ("voice", 1.0, "explicit command"),
        "/help": ("help", 1.0, "explicit command"),
    }
    token = text.split(maxsplit=1)[0] if text else ""
    if token in explicit:
        name, confidence, reason = explicit[token]
        return Intent(name, confidence, reason)

    # Never treat a UI-selected mode as specialist selection for Saarthi.
    # The capability router decides from the actual objective.
    signals = [
        ("research", 3, r"\b(research|deep dive|investigate|sources?|evidence|literature review)\b"),
        ("search", 2, r"\b(search|find|look up|lookup|latest|current)\b"),
        ("analyze", 3, r"\b(analy[sz]e|compare|break down|trade[- ]?offs?|evaluate|assess|diagnose)\b"),
        ("plan", 3, r"\b(plan|roadmap|schedule|prioriti[sz]e|timeline|dependencies|strategy)\b"),
        ("coding", 4, r"\b(code|coding|debug|refactor|repository|repo|api|sdk|python|javascript|typescript|html|css|github|vercel|deploy|function|bug)\b"),
        ("create", 2, r"\b(write|draft|rewrite|story|copy|prompt|presentation|design|create|compose)\b"),
        ("data_analyst", 4, r"\b(dataset|csv|excel|spreadsheet|kpi|metrics|statistics|chart|charts|graph|graphs|dashboard|heatmap|visualization|visualisation|forecast|regression)\b"),
        ("calculate", 5, r"\b(calculate|calculator|compute|percentage|percent|how much remains|what is .*\d+%|\d+(?:\.\d+)?\s*[+\-*/x×]\s*\d+(?:\.\d+)?)\b"),
        ("convert", 4, r"\b(convert|how many)\b.*\b(km|kilometer|kilometers|mile|miles|mi|kg|kilogram|kilograms|lb|lbs|pound|pounds|celsius|fahrenheit|°c|°f)\b"),
        ("remember", 4, r"\b(remember|save this|store this)\b"),
        ("recall", 4, r"\b(recall|what did i|remember when|previously)\b"),
        ("task", 3, r"\b(task|todo|to-do)\b"),
        ("remind", 4, r"\b(remind|reminder)\b"),
        ("workflow", 3, r"\b(workflow|automate|automation)\b"),
        ("briefing", 3, r"\b(briefing|brief me|what matters today)\b"),
        ("date", 5, r"\b(what(?:'s| is)?\s+(?:today(?:'s)?\s+)?date|what date is it|what day is today)\b"),
        ("time", 5, r"\b(what(?:'s| is)?\s+(?:the\s+)?(?:current\s+)?time|time now|what time is it|tell me the time)\b"),
        ("system", 5, r"\b(system status|health check|diagnostics)\b"),
        ("help", 3, r"\b(help|what can you do|commands)\b"),
    ]
    scores: dict[str, int] = {}
    for name, weight, pattern in signals:
        hits = len(re.findall(pattern, text, re.IGNORECASE))
        if hits:
            scores[name] = hits * weight

    if not scores:
        return Intent("chat", 0.74, "general conversation")

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    winner, score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0

    # Broad mixed requests stay with Saarthi and are handled as a composed
    # objective rather than forcing one specialist to own the conversation.
    if len(ranked) >= 3 and score <= second + 2:
        return Intent("chat", 0.86, "multi-capability objective")
    confidence = min(0.98, 0.70 + (score / max(1, score + second)) * 0.25)
    return Intent(winner, confidence, "autonomous capability routing")


def build_plan(intent: Intent) -> list[PlanStep]:
    common = [
        PlanStep("understand", "Understand request"),
        PlanStep("context", "Load available context"),
    ]
    tail = {
        "research": [PlanStep("retrieve", "Collect sources"), PlanStep("synthesize", "Synthesize findings")],
        "search": [PlanStep("retrieve", "Search available sources")],
        "analyze": [PlanStep("reason", "Analyze facts and trade-offs")],
        "plan": [PlanStep("plan", "Build an actionable plan")],
        "remember": [PlanStep("memory", "Prepare memory update")],
        "recall": [PlanStep("memory", "Retrieve relevant memory")],
        "task": [PlanStep("task", "Prepare task action")],
        "remind": [PlanStep("schedule", "Prepare reminder")],
        "workflow": [PlanStep("workflow", "Prepare workflow")],
        "briefing": [PlanStep("briefing", "Assemble briefing")],
        "date": [PlanStep("execute", "Get current date")],
        "time": [PlanStep("execute", "Get current time")],
        "calculate": [PlanStep("execute", "Calculate expression")],
        "convert": [PlanStep("execute", "Convert units")],
        "system": [PlanStep("diagnose", "Check engine status")],
        "settings": [PlanStep("settings", "Prepare settings action")],
        "voice": [PlanStep("voice", "Prepare voice pipeline")],
        "help": [PlanStep("catalog", "Load command capabilities")],
        "chat": [PlanStep("reason", "Reason over the request")],
    }
    return common + tail.get(intent.name, tail["chat"]) + [PlanStep("respond", "Form response")]


def fallback_response(message: str, intent: Intent, tool_results: dict[str, Any], assistant: str = "saarthi") -> str:
    profile = assistant_profile(assistant)
    if intent.name == "help":
        return (
            f"{profile['name']} is active. "
            "I can chat, research, search, analyze, plan, remember, recall, manage tasks and reminders, "
            "run workflows, brief you, and report system status."
        )
    if intent.name == "date":
        result = tool_results.get("system.date", {})
        return f"Today's date is {result.get('date', 'unavailable')} ({result.get('timezone', 'UTC')})."
    if intent.name == "time":
        result = tool_results.get("system.time", {})
        return f"The current time is {result.get('time', 'unavailable')} ({result.get('timezone', 'UTC')})."
    if intent.name == "calculate":
        result = tool_results.get("system.calculate", {})
        return f"The result is {result.get('value', 'unavailable')}."
    if intent.name == "convert":
        result = tool_results.get("system.convert", {})
        return f"{result.get('value')} {result.get('from')} = {result.get('result')} {result.get('to')}."
    if intent.name == "system":
        return "SAARTHI engine is online. The command router, plan builder and tool boundary are ready."
    if intent.name == "remember":
        return "I can prepare this as a memory item. Persistent cloud memory will activate when the memory provider is connected."
    if intent.name == "recall":
        return "I can recall from persistent cloud memory once the memory provider is connected."
    if intent.name in {"task", "remind", "workflow"}:
        return f"I understood this as a {intent.name} request. The action boundary is ready; execution requires the connected cloud tool."
    if intent.name == "briefing":
        return "Briefing mode is ready. Connect calendar, tasks, weather and news providers to assemble your live briefing."
    if intent.name == "search":
        return "Search mode is ready. Connect a web-search provider to retrieve live sources."
    if intent.name == "research":
        return "Research mode is ready. Connect web retrieval and I will collect, compare and synthesize sources."
    if intent.name == "analyze":
        return "Analysis mode is ready. Give me the facts, document or situation and I will separate facts, assumptions, trade-offs and actions."
    if intent.name == "plan":
        return "Planning mode is ready. Give me the outcome you want and I will turn it into ordered steps."
    return f"I've understood the request as a general conversation: “{message[:180]}”."


class SaarthiEngine:
    def __init__(self) -> None:
        self.tools = ToolRegistry()
        self.cloud = OpenAICompatibleProvider()

    def run(
        self,
        *,
        message: str,
        mode: str = "chat",
        assistant: str = "saarthi",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_id = "run_" + uuid.uuid4().hex[:12]
        ctx = context or {}
        assistant_id = str(assistant or "saarthi").lower()
        if assistant_id not in ASSISTANT_PROFILES:
            assistant_id = "saarthi"
        intent = classify(message, mode)
        plan = build_plan(intent)
        orchestration = build_orchestration(assistant_id, intent, message, ctx)
        if assistant_id == "data_analyst":
            plan = [PlanStep("profile", "Profile supplied data"), PlanStep("validate", "Validate data quality"), PlanStep("analyze", "Calculate and analyze"), PlanStep("visualize", "Create requested visualization"), PlanStep("respond", "Explain findings")]
        tool_results: dict[str, Any] = {}
        if assistant_id == "data_analyst":
            inspected = inspect_attachments(ctx.get("attachments") if isinstance(ctx, dict) else [])
            tool_results["data.profile"] = analyze_attachments_for_data(inspected)
            datasets = tool_results["data.profile"].get("datasets", [])
            if datasets:
                dataset = datasets[0]
                tool_results["data.analysis"] = analyze_dataset(dataset["columns"], dataset["rows"])
                # Build deterministic visuals from the supplied dataset, not from model-generated values.
                chart_match = re.search(r"\b(bar|line|pie|donut|scatter|bubble|area|stacked[ -]?bar|histogram|box|radar|funnel|gauge|waterfall|heat ?map)\b.*?\b(?:chart|graph|plot|visuali[sz]ation)\b", message, re.IGNORECASE)
                if chart_match and len(dataset["columns"]) >= 2:
                    requested_type = chart_match.group(1).lower().replace(" ", "_").replace("-", "_")
                    if requested_type == "heat_map":
                        requested_type = "heatmap"
                    if requested_type == "heatmap":
                        heatmaps = [spec for spec in recommend_visuals(dataset["columns"], dataset["rows"], limit=10) if spec.get("chartType") == "heatmap"]
                        if heatmaps:
                            tool_results["data.chart"] = heatmaps[0]
                        else:
                            tool_results["data.chart_error"] = "A heatmap requires two categorical dimensions and one numeric measure."
                    else:
                        x_key, series_key = dataset["columns"][0], dataset["columns"][1]
                        tool_results["data.chart"] = build_chart(
                            dataset["rows"], requested_type, x_key, series_key,
                            f"{series_key} by {x_key}",
                        )
                elif re.search(r"\b(dashboard|visuali[sz]e|visualization|visualisation|show me|plot|graph|chart)\b", message, re.IGNORECASE):
                    tool_results["data.charts"] = recommend_visuals(dataset["columns"], dataset["rows"])

        if assistant_id == "analyze":
            inspected = inspect_attachments(ctx.get("attachments") if isinstance(ctx, dict) else [])
            texts = []
            for item in inspected:
                if isinstance(item, dict) and item.get("text"):
                    texts.append(str(item["text"]))
            supplied = "\\n".join(texts) if texts else str(ctx.get("analysis_text", "")) if isinstance(ctx, dict) else ""
            if supplied:
                tool_results["analysis.brief"] = analyze_text(supplied, message)
            else:
                tool_results["analysis.brief"] = analyze_text(message, message)

        # Evidence-first research pass before model generation.
        if assistant_id == "research":
            research_urls = ctx.get("research_urls", []) if isinstance(ctx, dict) else []
            if isinstance(research_urls, str):
                research_urls = [research_urls]
            if not isinstance(research_urls, list):
                research_urls = []
            try:
                tool_results["research.brief"] = research(
                    message,
                    urls=[str(url) for url in research_urls[:10]],
                    search=bool(ctx.get("research_web_search", True)) if isinstance(ctx, dict) else True,
                    max_sources=5,
                )
            except Exception as exc:
                tool_results["research.brief"] = {
                    "question": message,
                    "source_count": 0,
                    "sources": [],
                    "evidence": [],
                    "limitations": [f"Research retrieval failed: {str(exc)[:240]}"],
                }

        boundary_reply = specialist_boundary_response(assistant_id, message)
        if boundary_reply:
            return {
                "ok": True,
                "run_id": run_id,
                "assistant": {
                    "id": assistant_id,
                    "name": ASSISTANT_PROFILES[assistant_id]["name"],
                    "role": ASSISTANT_PROFILES[assistant_id]["role"],
                    "boundary": ASSISTANT_PROFILES[assistant_id].get("boundary", "general assistance"),
                    "capabilities": agent_capability(assistant_id),
                    "industry": build_runtime_context(assistant_id, ctx.get("industry") if isinstance(ctx, dict) else None).get("industry"),
                },
                "intent": {"name": intent.name, "confidence": intent.confidence, "reason": intent.reason},
                "plan": [step.__dict__ for step in plan],
                "orchestration": orchestration,
                "reply": boundary_reply,
                "provider": "boundary-guard",
                "usage": None,
                "execution": "blocked-by-scope",
                "tool_results": {},
                "verification": {"verified": True, "claims": "specialist scope boundary enforced before model execution"},
                "work_product": build_work_product(
                    objective=message,
                    intent=intent.name,
                    reply=boundary_reply,
                    orchestration=orchestration,
                    tool_results={},
                    verification={"claims": "specialist scope boundary enforced before model execution"},
                ),
            }

        if intent.name == "system":
            tool_results["system.status"] = self.tools.execute("system.status")
        timezone_name = ctx.get("timezone") if isinstance(ctx, dict) else None
        if intent.name in {"date", "time"}:
            tool_name = "system.date" if intent.name == "date" else "system.time"
            tool_results[tool_name] = self.tools.execute(tool_name, {"timezone": timezone_name or "Asia/Kolkata"})
        elif intent.name == "calculate":
            expression = message.strip()
            expression = re.sub(r"^.*?\b(?:calculate|compute|calculator)\b", "", expression, flags=re.IGNORECASE).strip(" :")
            match = re.search(r"-?\d+(?:\.\d+)?(?:\s*[+\-*/x×]\s*-?\d+(?:\.\d+)?)+", expression, re.IGNORECASE)
            if not match:
                raise ValueError("could not parse calculation expression")
            expression = match.group(0).replace("×", "*").replace("x", "*").replace("X", "*")
            tool_results["system.calculate"] = self.tools.execute("system.calculate", {"expression": expression})
        elif intent.name == "convert":
            match = re.search(r"(-?\d+(?:\.\d+)?)\s*(km|kilometers?|mi|miles?|kg|kilograms?|lbs?|pounds?|c|°c|celsius|f|°f|fahrenheit)\s+(?:to|in|into)\s*(km|kilometers?|mi|miles?|kg|kilograms?|lbs?|pounds?|c|°c|celsius|f|°f|fahrenheit)", message, re.IGNORECASE)
            if not match:
                raise ValueError("could not parse unit conversion")
            tool_results["system.convert"] = self.tools.execute("system.convert", {"value": match.group(1), "from": match.group(2).replace("°", ""), "to": match.group(3).replace("°", "")})
        if intent.name in {"date", "time", "calculate", "convert"}:
            reply = fallback_response(message, intent, tool_results, assistant_id)
            return {
                "ok": True,
                "run_id": run_id,
                "assistant": {
                    "id": assistant_id,
                    "name": ASSISTANT_PROFILES[assistant_id]["name"],
                    "role": ASSISTANT_PROFILES[assistant_id]["role"],
                    "boundary": ASSISTANT_PROFILES[assistant_id].get("boundary", "general assistance"),
                    "capabilities": agent_capability(assistant_id),
                    "industry": build_runtime_context(assistant_id, ctx.get("industry") if isinstance(ctx, dict) else None).get("industry"),
                },
                "intent": {"name": intent.name, "confidence": intent.confidence, "reason": intent.reason},
                "plan": [step.__dict__ for step in plan],
                "orchestration": orchestration,
                "reply": reply,
                "provider": f"system.{intent.name}",
                "route": None,
                "failover": [],
                "usage": None,
                "execution": "completed",
                "tool_results": tool_results,
                "verification": {"verified": True, "claims": f"deterministic {intent.name} tool result returned before model execution"},
                "work_product": build_work_product(
                    objective=message,
                    intent=intent.name,
                    reply=reply,
                    orchestration=orchestration,
                    tool_results=tool_results,
                    verification={"claims": f"deterministic {intent.name} tool result returned before model execution"},
                ),
            }

        provider = self.cloud if self.cloud.configured else None
        provider_name = provider.name if provider else "deterministic-fallback"
        usage: dict[str, Any] | None = None
        try:
            if provider:
                reply, usage = provider.generate(
                    message=message,
                    intent=intent,
                    context={**ctx, "execution_results": tool_results, "orchestration": orchestration},
                    assistant=assistant_id,
                )
            else:
                reply = fallback_response(message, intent, tool_results, assistant_id)
        except Exception as exc:
            provider_name = "deterministic-fallback"
            reply = fallback_response(message, intent, tool_results, assistant_id)
            if intent.name == "chat":
                reply = (
                    "I received your message, but the cloud AI gateway is temporarily unavailable. "
                    "The request did not complete through the model provider. Please try again shortly."
                )

        return {
            "ok": True,
            "run_id": run_id,
            "assistant": {
                "id": assistant_id,
                "name": ASSISTANT_PROFILES[assistant_id]["name"],
                "role": ASSISTANT_PROFILES[assistant_id]["role"],
                "boundary": ASSISTANT_PROFILES[assistant_id].get("boundary", "general assistance"),
                "capabilities": agent_capability(assistant_id),
                "industry": build_runtime_context(assistant_id, ctx.get("industry") if isinstance(ctx, dict) else None).get("industry"),
            },
            "intent": {
                "name": intent.name,
                "confidence": intent.confidence,
                "reason": intent.reason,
            },
            "plan": [step.__dict__ for step in plan],
            "orchestration": orchestration,
            "reply": reply,
            "provider": provider_name,
            "route": self.cloud.last_route if self.cloud.configured else None,
            "failover": self.cloud.last_failures if self.cloud.configured else [],
            "usage": usage,
            "execution": "completed",
            "tool_results": tool_results,
            "verification": {"verified": True, "claims": "response generated from available execution context", "data_analysis": assistant_id == "data_analyst", "calculation_source": "server-side attachment profile" if assistant_id == "data_analyst" else None},
            "work_product": build_work_product(
                objective=message,
                intent=intent.name,
                reply=reply,
                orchestration=orchestration,
                tool_results=tool_results,
                verification={"claims": "response generated from available execution context"},
            ),
        }
    