"""The CLI kill timer: off by default, POWERSPAWN_TIMEOUT, and 0 = no limit."""
import asyncio
import json
import sys

import pytest

from PowerSpawn.config import DEFAULT_SPAWN_TIMEOUT, default_spawn_timeout
from PowerSpawn.proc import run_captured


def test_default_is_no_limit(monkeypatch):
    monkeypatch.delenv("POWERSPAWN_TIMEOUT", raising=False)
    assert DEFAULT_SPAWN_TIMEOUT == 0
    assert default_spawn_timeout() == 0


@pytest.mark.parametrize("raw, expected", [
    ("7200", 7200), ("0", 0), ("off", 0), ("None", 0), (" 90 ", 90), ("1.5e3", 1500),
    ("soon", 0), ("-5", 0),
])
def test_env_override(monkeypatch, raw, expected):
    monkeypatch.setenv("POWERSPAWN_TIMEOUT", raw)
    assert default_spawn_timeout() == expected


def test_run_captured_without_limit():
    code, out, _, timed_out = run_captured([sys.executable, "-c", "print('ok')"], timeout=0, shell=False)
    assert (code, out, timed_out) == (0, "ok", False)


def _spawned_timeout(args, agent_type="claude"):
    """The timeout handle_spawn hands the provider."""
    from PowerSpawn import mcp_server
    seen = {}

    def fake_spawn(prompt, *, model=None, timeout=DEFAULT_SPAWN_TIMEOUT):
        from PowerSpawn.providers.types import AgentResult
        seen["timeout"] = timeout
        return AgentResult(success=True, text="done")

    async def run():
        out = await mcp_server.handle_spawn({"prompt": "x", **args}, agent_type, fake_spawn)
        json.loads(out[0].text)
        await asyncio.to_thread(mcp_server.agent_manager.wait_for_all, 10)

    asyncio.run(run())
    return seen["timeout"]


def test_handle_spawn_timeout_resolution(monkeypatch):
    monkeypatch.delenv("POWERSPAWN_TIMEOUT", raising=False)
    assert _spawned_timeout({}) == 0                      # default: no limit
    assert _spawned_timeout({"timeout": None}) == 0
    assert _spawned_timeout({"timeout": 120}) == 120
    monkeypatch.setenv("POWERSPAWN_TIMEOUT", "7200")
    assert _spawned_timeout({}) == 7200
    assert _spawned_timeout({"timeout": 300}) == 300      # explicit wins over the env
    assert _spawned_timeout({"timeout": 0}) == 0          # explicit 0: no limit


def test_no_limit_worker_waits_twelve_hours():
    from PowerSpawn.channel import Worker
    w = Worker(name="c", cli="claude", channel="x", timeout=None)
    assert w.answer_budget == 43200 and w.max_wait == 43200
    assert "Your run is stopped" not in w.brief()


def test_cli_timeout_schema_documents_no_limit():
    from PowerSpawn import mcp_server
    tools = {t.name: t.inputSchema["properties"] for t in asyncio.run(mcp_server.list_tools())}
    for name in ("spawn_claude", "spawn_codex", "spawn_copilot", "spawn_cursor",
                 "spawn_gemini_cli", "spawn_opencode", "spawn_grok"):
        t = tools[name]["timeout"]
        assert t["default"] == 0 and t["minimum"] == 0 and "0 = no limit" in t["description"], name
