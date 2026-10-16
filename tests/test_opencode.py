"""spawn_opencode: JSON events, transient retries, and the PowerScroll board bookends."""

import json

from PowerSpawn.providers import opencode, powerscroll


def _events(*events):
    return "\n".join(json.dumps(e) for e in events)


TEXT = {"type": "text", "part": {"type": "text", "text": "42"}}
DROPPED = {"type": "error", "error": {"message": "Transport: The socket connection was closed unexpectedly."}}


def _setup(monkeypatch, outputs, card=None):
    calls = {"runs": [], "finish": []}

    def fake_run(cmd, cwd, timeout, stdin_text, env):
        calls["runs"].append({"cmd": cmd, "prompt": stdin_text, "env": env})
        return 0, outputs.pop(0), "", False

    monkeypatch.setattr(opencode, "run_captured", fake_run)
    monkeypatch.setattr(opencode, "log_spawn_start", lambda **kw: "id")
    monkeypatch.setattr(opencode, "log_spawn_complete", lambda *a, **kw: None)
    monkeypatch.setattr(opencode.time, "sleep", lambda s: None)
    monkeypatch.setattr(powerscroll, "start_card",
                        lambda *a, **kw: (card, None if card else "no board"))
    monkeypatch.setattr(powerscroll, "finish_card",
                        lambda c, ok, text, d: calls["finish"].append((ok, text)))
    return calls


def test_parse_events_joins_text_and_collects_errors():
    text, errors = opencode._parse_events(_events(TEXT, DROPPED) + "\nnot json")
    assert text == ["42"] and errors == [DROPPED["error"]["message"]]


def test_free_model_by_default_and_retries_a_dropped_connection(monkeypatch):
    calls = _setup(monkeypatch, [_events(DROPPED), _events(TEXT)])
    result = opencode.spawn_opencode("What is 6*7?")
    assert result.success and result.text.startswith("42")
    assert len(calls["runs"]) == 2
    cmd = calls["runs"][0]["cmd"]
    assert cmd[:6] == ["opencode", "run", "--standalone", "--auto", "--format", "json"]
    assert cmd[-1] == "opencode/deepseek-v4.1-flash-free"


def test_alias_and_no_board_still_runs(monkeypatch):
    calls = _setup(monkeypatch, [_events(TEXT)])
    result = opencode.spawn_opencode("task", model="glm")
    assert calls["runs"][0]["cmd"][-1] == "opencode/glm-5.3-flash-free"
    assert "[powerspawn] no board" in result.text


def test_board_card_brief_mcp_and_close(monkeypatch):
    card = powerscroll.BoardCard("oc-seo-1", "p-1", "Dashboard", 7)
    calls = _setup(monkeypatch, [_events(TEXT)], card=card)
    result = opencode.spawn_opencode("Fix the sitemap", agent_name="oc-seo-1")
    run = calls["runs"][0]
    assert run["env"]["POWERNOTE_AGENT_NAME"] == "oc-seo-1"
    mcp = json.loads(run["env"]["OPENCODE_CONFIG_CONTENT"])["mcp"]["powerscroll"]
    assert mcp["environment"] == {"POWERNOTE_AGENT_NAME": "oc-seo-1"}
    assert 'me="oc-seo-1", boardId="p-1", card=7' in run["prompt"]
    assert run["prompt"].endswith("Fix the sitemap")
    assert calls["finish"] == [(True, "42")]
    assert result.usage["board_card"] == "#7"


def test_failure_moves_card_with_the_error(monkeypatch):
    card = powerscroll.BoardCard("oc-x", "p-1", "Dashboard", 3)
    calls = _setup(monkeypatch, [_events(DROPPED)] * 3, card=card)
    result = opencode.spawn_opencode("task")
    assert not result.success and len(calls["runs"]) == 3
    assert calls["finish"][0][0] is False and "socket connection" in calls["finish"][0][1]


def test_agent_name_is_always_valid():
    assert powerscroll.agent_name("OC Seo #1") == "oc-seo-1"
    assert powerscroll.NAME_RE.match(powerscroll.agent_name("__"))
    assert len(powerscroll.agent_name("x" * 80)) == 40


def test_pick_board_by_id_title_or_first():
    boards = [{"id": "a", "title": "Dashboard"}, {"id": "b", "title": "Agents"}]
    assert powerscroll._pick_board(boards, "")["id"] == "a"
    assert powerscroll._pick_board(boards, "b")["id"] == "b"
    assert powerscroll._pick_board(boards, "agents")["id"] == "b"
    assert powerscroll._pick_board(boards, "nope") is None


def test_server_command_parsing(monkeypatch):
    monkeypatch.setenv("POWERSCROLL_MCP_COMMAND", '["node", "C:/x/server.js"]')
    assert powerscroll.server_command() == ["node", "C:/x/server.js"]
    monkeypatch.setenv("POWERSCROLL_MCP_COMMAND", "node C:/x/server.js")
    assert powerscroll.server_command() == ["node", "C:/x/server.js"]
    monkeypatch.delenv("POWERSCROLL_MCP_COMMAND")
    assert powerscroll.server_command() == ["npx", "-y", "powerscroll-mcp"]


def test_mcp_schema_exposes_working_dir():
    import asyncio
    from PowerSpawn.mcp_server import list_tools
    tool = next(t for t in asyncio.run(list_tools()) if t.name == "spawn_opencode")
    assert "working_dir" in tool.inputSchema["properties"]
