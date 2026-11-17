import asyncio
import sys
from urllib.error import HTTPError

import pytest

from backend import execution, hermes_bridge
from backend.engine import SaarthiEngine
from backend.private_session import Scope


def test_worker_runs_existing_engine():
    result = asyncio.run(execution.run_turn({"message": "calculate 12 + 3"}, 5))
    assert result["provider"] == "system.calculate"
    assert "15" in result["reply"]
    assert 0 <= result["timings_ms"]["routing"] <= result["timings_ms"]["engine"]


def test_worker_deadline_kills_and_reaps_process(monkeypatch):
    processes = []
    spawn = asyncio.create_subprocess_exec

    async def sleeper(*args, **kwargs):
        process = await spawn(sys.executable, "-c", "import time; time.sleep(20)", **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", sleeper)
    with pytest.raises(TimeoutError):
        asyncio.run(execution.run_turn({"message": "Slow fixture"}, 0.1))
    assert len(processes) == 1 and processes[0].returncode != 0
    assert processes[0].returncode is not None


@pytest.mark.parametrize("exc,code", [
    (HTTPError("https://fixture.invalid", 429, "limited", {}, None), "provider_rate_limited"),
    (OSError("private provider details"), "provider_unavailable"),
    (TimeoutError(), "provider_timeout"),
])
def test_terminal_provider_errors_are_typed_and_redacted(monkeypatch, exc, code):
    monkeypatch.setenv("SAARTHI_LLM_ROUTES_JSON",
                       '[{"name":"one","url":"https://fixture.invalid","key":"fixture","model":"fixture"}]')
    token = execution.timings.set({})
    try:
        engine = SaarthiEngine()

        def fail(*args, **kwargs):
            raise exc

        monkeypatch.setattr(engine.cloud, "_request", fail)
        result = engine.run(message="Write me a short story.")
        assert result["error_code"] == code
        assert result["ok"] is False and result["verification"]["verified"] is False
        assert "private provider details" not in str(result)
    finally:
        execution.timings.reset(token)


def test_successful_provider_failover_keeps_timing_and_route(monkeypatch):
    monkeypatch.setenv("SAARTHI_LLM_ROUTES_JSON", """[
        {"name":"one","url":"https://one.invalid","key":"fixture","model":"fixture"},
        {"name":"two","url":"https://two.invalid","key":"fixture","model":"fixture"}
    ]""")
    observed = {}
    token = execution.timings.set(observed)
    try:
        engine = SaarthiEngine()

        def provider(route, **kwargs):
            if route["name"] == "one":
                raise OSError("private")
            engine.cloud.last_route = route["name"]
            return "Second route answered.", None

        monkeypatch.setattr(engine.cloud, "_request", provider)
        result = engine.run(message="Write me a short story.")
        assert result["ok"] and result["route"] == "two"
        assert result["failover"] == [{"route": "one", "error": "unavailable"}]
        assert {"routing", "provider_attempt_1", "provider_attempt_2"} <= observed.keys()
    finally:
        execution.timings.reset(token)


def test_hermes_uses_scoped_session_and_existing_history(monkeypatch):
    import httpx

    scope = Scope("preview", "https://preview.invalid", "a" * 40, "owner-a", "fixture", "fixture", 10)
    monkeypatch.setenv("SAARTHI_HERMES_ENABLED", "true")
    monkeypatch.setenv("SAARTHI_HERMES_VALIDATED_SCOPE", "preview")
    monkeypatch.setenv("SAARTHI_HERMES_URL", "https://hermes.invalid")
    monkeypatch.setenv("SAARTHI_HERMES_API_KEY", "gateway-fixture")
    calls = []

    class Client:
        def __init__(self, **kwargs):
            assert not kwargs["follow_redirects"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return httpx.Response(200, json={"choices": [{"message": {"content": "I recall that."}}]})

    monkeypatch.setattr(hermes_bridge.httpx, "AsyncClient", Client)
    previous = [{"role": "user", "content": "Previous message"}]
    result = asyncio.run(hermes_bridge.generate(scope, "thread", "Continue", previous))
    assert result["ok"] and result["provider"] == "hermes-agent"
    assert calls[0][1]["json"]["messages"][0] == previous[0]
    first = calls[0][1]["headers"]["X-Hermes-Session-Key"]
    assert len(first) == 64 and first != "thread"
    other = Scope("preview", scope.origin, scope.commit, "owner-b", "fixture", "fixture", 10)
    asyncio.run(hermes_bridge.generate(other, "thread", "Continue", previous))
    assert calls[1][1]["headers"]["X-Hermes-Session-Key"] != first
    monkeypatch.setenv("SAARTHI_HERMES_VALIDATED_SCOPE", "production")
    assert asyncio.run(hermes_bridge.generate(scope, "thread", "Continue", previous))["error_code"] == "hermes_disabled"
