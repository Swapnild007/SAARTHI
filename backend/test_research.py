from backend import research as research_module
from backend.engine import SaarthiEngine


def test_source_evaluation_prefers_authoritative_domain():
    source = {
        "url": "https://www.who.int/example",
        "title": "Health research",
        "text": "Research evidence about health outcomes and public health policy.",
    }
    result = research_module.evaluate_source(source, "health outcomes")
    assert result["quality"]["authority"] == 1.0
    assert result["quality"]["score"] > 0.5


def test_evidence_extraction_returns_source_attribution():
    source = {
        "url": "https://example.org/report",
        "title": "Example report",
        "text": "This sentence contains useful evidence about workforce productivity and service outcomes. "
                "Another sentence is unrelated to the question.",
    }
    evidence = research_module.extract_evidence(source, "workforce productivity")
    assert evidence
    assert evidence[0]["source_url"] == source["url"]
    assert "workforce productivity" in evidence[0]["text"].lower()


def test_private_urls_are_rejected():
    assert research_module._public_url("http://127.0.0.1:8000/test") is False
    assert research_module._public_url("http://localhost/test") is False


def test_research_brief_contains_sources_and_evidence():
    sources = [{
        "url": "https://example.org/report",
        "title": "Report",
        "text": "The report describes evidence about supply chain delivery performance and lead time.",
    }]
    brief = research_module.build_research_brief("supply chain delivery performance", sources)
    assert brief["source_count"] == 1
    assert brief["sources"][0]["quality"]["score"] > 0
    assert brief["evidence"]


def test_research_agent_runs_evidence_pass_before_model(monkeypatch):
    expected = {
        "question": "compare renewable energy costs",
        "source_count": 1,
        "sources": [{"url": "https://example.org/source", "title": "Source", "text": "Evidence"}],
        "evidence": [{"source_url": "https://example.org/source", "text": "Evidence"}],
        "limitations": [],
    }

    monkeypatch.setattr("backend.engine.research", lambda *args, **kwargs: expected)
    engine = SaarthiEngine()

    captured = {}
    def fake_generate(**kwargs):
        captured.update(kwargs)
        return "Synthesis based on the supplied evidence.", None

    engine.cloud.generate = fake_generate
    result = engine.run(
        message="compare renewable energy costs",
        assistant="research",
        context={"research_web_search": False},
    )

    assert result["execution"] == "completed"
    assert result["tool_results"]["research.brief"] == expected
    assert captured["context"]["execution_results"]["research.brief"] == expected
