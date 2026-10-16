"""spawn_opencode: JSON events, transient retries, and the PowerBoard board bookends."""

import json

from PowerSpawn.providers import opencode, powerboard


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
    monkeypatch.setattr(powerboard, "start_card",
                        lambda *a, **kw: (card, None if card else "no board"))
    monkeypatch.setattr(powerboard, "finish_card",
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
    card = powerboard.BoardCard("oc-seo-1", "p-1", "Dashboard", 7)
    calls = _setup(monkeypatch, [_events(TEXT)], card=card)
    result = opencode.spawn_opencode("Fix the sitemap", agent_name="oc-seo-1")
    run = calls["runs"][0]
    assert run["env"]["POWERBOARD_AGENT_NAME"] == "oc-seo-1"
    assert run["env"]["POWERNOTE_AGENT_NAME"] == "oc-seo-1"
    mcp = json.loads(run["env"]["OPENCODE_CONFIG_CONTENT"])["mcp"]["powerboard"]
    assert mcp["environment"] == {"POWERBOARD_AGENT_NAME": "oc-seo-1", "POWERNOTE_AGENT_NAME": "oc-seo-1"}
    assert 'me="oc-seo-1", boardId="p-1", card=7' in run["prompt"]
    assert run["prompt"].endswith("Fix the sitemap")
    assert calls["finish"] == [(True, "42")]
    assert result.usage["board_card"] == "#7"


def test_failure_moves_card_with_the_error(monkeypatch):
    card = powerboard.BoardCard("oc-x", "p-1", "Dashboard", 3)
    calls = _setup(monkeypatch, [_events(DROPPED)] * 3, card=card)
    result = opencode.spawn_opencode("task")
    assert not result.success and len(calls["runs"]) == 3
    assert calls["finish"][0][0] is False and "socket connection" in calls["finish"][0][1]


def test_agent_name_is_always_valid():
    assert powerboard.agent_name("OC Seo #1") == "oc-seo-1"
    assert powerboard.NAME_RE.match(powerboard.agent_name("__"))
    assert len(powerboard.agent_name("x" * 80)) == 40


def test_pick_board_by_id_title_or_first():
    boards = [{"id": "a", "title": "Dashboard"}, {"id": "b", "title": "Agents"}]
    assert powerboard._pick_board(boards, "")["id"] == "a"
    assert powerboard._pick_board(boards, "b")["id"] == "b"
    assert powerboard._pick_board(boards, "agents")["id"] == "b"
    assert powerboard._pick_board(boards, "nope") is None


def test_agent_env_sets_both_names():
    env = powerboard.agent_env("oc-seo-1")
    assert env["POWERBOARD_AGENT_NAME"] == "oc-seo-1"
    assert env["POWERNOTE_AGENT_NAME"] == "oc-seo-1"


def test_server_command_parsing(monkeypatch):
    monkeypatch.setenv("POWERBOARD_MCP_COMMAND", '["node", "C:/x/server.js"]')
    assert powerboard.server_command() == ["node", "C:/x/server.js"]
    monkeypatch.setenv("POWERBOARD_MCP_COMMAND", "node C:/x/server.js")
    assert powerboard.server_command() == ["node", "C:/x/server.js"]
    monkeypatch.delenv("POWERBOARD_MCP_COMMAND")
    # Legacy name still read, and POWERBOARD_* wins when both are set.
    monkeypatch.setenv("POWERSCROLL_MCP_COMMAND", "node C:/legacy.js")
    assert powerboard.server_command() == ["node", "C:/legacy.js"]
    monkeypatch.setenv("POWERBOARD_MCP_COMMAND", "node C:/new.js")
    assert powerboard.server_command() == ["node", "C:/new.js"]
    monkeypatch.delenv("POWERBOARD_MCP_COMMAND")
    monkeypatch.delenv("POWERSCROLL_MCP_COMMAND")
    assert powerboard.server_command() == ["npx", "-y", "powerboard-mcp"]


def test_board_env_precedence(monkeypatch):
    boards = {"boards": [{"id": "new", "title": "New"}, {"id": "old", "title": "Old"}]}

    def fake_call(me, calls):
        if calls[0] == ("board_list", {}):
            return [boards]
        return [{"card": {"number": 5}} for _ in calls]

    monkeypatch.setattr(powerboard, "_call", fake_call)
    monkeypatch.setenv("POWERBOARD_BOARD", "new")
    monkeypatch.setenv("POWERSCROLL_BOARD", "old")
    card, warn = powerboard.start_card("me", "t", "d", [])
    assert warn is None and card.board_id == "new"
    monkeypatch.delenv("POWERBOARD_BOARD")
    card, warn = powerboard.start_card("me", "t", "d", [])
    assert warn is None and card.board_id == "old"


def test_mcp_schema_exposes_working_dir():
    import asyncio
    from PowerSpawn.mcp_server import list_tools
    tool = next(t for t in asyncio.run(list_tools()) if t.name == "spawn_opencode")
    assert "working_dir" in tool.inputSchema["properties"]


def test_unavailable_endpoint_is_retried(monkeypatch):
    down = {"type": "error", "error": {"message": "Upstream request failed: Endpoint is unavailable."}}
    calls = _setup(monkeypatch, [_events(down), _events(TEXT)])
    result = opencode.spawn_opencode("task", model="glm")
    assert result.success and len(calls["runs"]) == 2


def test_rate_limit_backs_off_for_minutes(monkeypatch):
    limited = {"type": "error", "error": {"message": "Rate limit exceeded. Please try again later."}}
    calls = _setup(monkeypatch, [_events(limited), _events(limited), _events(TEXT)])
    slept = []
    monkeypatch.setattr(opencode.time, "sleep", slept.append)
    result = opencode.spawn_opencode("task")
    assert result.success and len(calls["runs"]) == 3
    assert slept == [60, 120]
