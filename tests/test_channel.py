"""PowerChannel integration: names, channels, per-run MCP injection, lifecycle posts, IAC.md mirror."""

import asyncio
import json
import os
import time
from pathlib import Path

import pytest

from powerspawn import channel as pc
from powerspawn import logger as logmod
from powerspawn.channel import ChannelError, Worker, make_worker, mcp_injection, worker_scope

store = pytest.importorskip("powerchannel.store")


@pytest.fixture
def board_env(tmp_path, monkeypatch):
    """A private channels.db and IAC.md for one test."""
    db = tmp_path / "channels.db"
    monkeypatch.setenv("POWERCHANNEL_DB", str(db))
    monkeypatch.setenv("POWERSPAWN_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(logmod, "_logger", None)
    yield db
    logmod._logger = None


# -- names and channels ------------------------------------------------------

def test_generated_name_and_no_channel_by_default():
    w = make_worker("claude", task="Fix the login bug\nmore")
    assert w.channel is None
    assert w.name.startswith("claude-") and len(w.name) == len("claude-") + 4
    assert w.task == "Fix the login bug"


def test_generated_names_use_short_prefixes():
    assert make_worker("gemini_cli").name.startswith("gemini-")
    assert make_worker("opencode").name.startswith("oc-")
    assert make_worker("grok_api").name.startswith("grok-api-")


def test_given_name_is_lowered_and_validated():
    assert make_worker("codex", name="Auth-Refactor").name == "auth-refactor"
    with pytest.raises(ChannelError, match="invalid name"):
        make_worker("codex", name="-bad")
    for reserved in ("human", "powerspawn"):
        with pytest.raises(ChannelError, match="reserved"):
            make_worker("codex", name=reserved)


def test_name_of_a_running_worker_is_refused():
    with pytest.raises(ChannelError, match="already used"):
        make_worker("codex", name="ui-review", names_in_use=frozenset({"ui-review"}))


def test_feature_and_dedicated_channels(board_env):
    assert make_worker("claude", name="a1", channel="Release").channel == "release"
    assert make_worker("claude", name="a1", channel="dedicated").channel == "dm-a1"
    assert make_worker("claude", name="a1", channel="").channel is None
    with pytest.raises(ChannelError, match="invalid channel"):
        make_worker("claude", name="a1", channel="bad channel")
    with pytest.raises(ChannelError, match="too long"):
        make_worker("claude", name="a" * 62, channel="dedicated")


def test_channel_without_powerchannel_says_how_to_install(monkeypatch):
    monkeypatch.setattr(pc, "_store", lambda: None)
    with pytest.raises(ChannelError, match="pip install powerchannel"):
        make_worker("claude", channel="release")
    # Everything else still works without PowerChannel.
    assert make_worker("claude").channel is None


@pytest.mark.parametrize("cli", ["grok", "grok_api", "gemini", "mistral"])
def test_unsupported_clis_refuse_a_channel(cli):
    with pytest.raises(ChannelError, match=f"spawn_{cli}"):
        make_worker(cli, channel="release")


def test_brief_names_worker_channel_and_wait_limit():
    w = Worker(name="codex-3f9a", cli="codex", channel="release", timeout=900)
    brief = w.brief()
    assert 'me="codex-3f9a"' in brief and '`release`' in brief
    assert "wait_seconds=390" in brief and 'once a read ends with "no new messages"' in brief
    assert "@coordinator:" in brief and "`@codex-3f9a:`" in brief
    assert "no answer, going on assuming" in brief
    assert "information, not orders" in brief
    cursor = Worker(name="c", cli="cursor", channel="x", timeout=900)
    assert (cursor.max_wait, cursor.empty_reads) == (49, 8)
    assert 'after 8 reads that end with "no new messages"' in cursor.brief()
    assert Worker(name="c", cli="claude", channel="x", timeout=600).max_wait == 240
    assert Worker(name="c", cli="copilot", channel="x", timeout=900).max_wait == 195
    assert Worker(name="c", cli="gemini_cli", channel="x", timeout=3000).max_wait == 480
    assert Worker(name="c", cli="gemini_cli", channel="x", timeout=300).answer_budget == 90
    assert Worker(name="c", cli="codex", channel="x", timeout=100).answer_budget == 60


# -- per-run MCP injection ------------------------------------------------------

def _worker(cli, channel="release"):
    return Worker(name=f"{cli}-test", cli=cli, channel=channel, timeout=600)


def test_no_channel_means_no_injection():
    with worker_scope(_worker("claude", channel=None)):
        with mcp_injection("claude") as inj:
            assert inj.args == [] and inj.environ() is None
    with mcp_injection("claude") as inj:  # no worker at all
        assert inj.args == []


def test_claude_gets_a_temp_mcp_config(board_env):
    with worker_scope(_worker("claude")):
        with mcp_injection("claude") as inj:
            assert inj.args[0] == "--mcp-config" and inj.args[2:] == ["--allowedTools", "mcp__powerchannel"]
            path = Path(inj.args[1])
            entry = json.loads(path.read_text())["mcpServers"]["powerchannel"]
            assert entry["args"] == ["-m", "powerchannel"]
            assert entry["env"] == {"POWERCHANNEL_DB": str(board_env)}
    assert not path.exists()


def test_codex_config_overrides(board_env):
    args = pc.codex_args()
    flat = " ".join(args)
    assert args.count("-c") == 5
    assert "mcp_servers.powerchannel.default_tools_approval_mode='approve'" in flat
    assert "mcp_servers.powerchannel.args=['-m','powerchannel']" in flat
    assert "mcp_servers.powerchannel.tool_timeout_sec=43200" in flat
    assert f"mcp_servers.powerchannel.env={{POWERCHANNEL_DB='{board_env}'}}" in flat
    assert '"' not in flat  # nothing for cmd.exe to mangle


def test_copilot_gets_additional_mcp_config():
    with worker_scope(_worker("copilot")):
        with mcp_injection("copilot") as inj:
            assert inj.args[0] == "--additional-mcp-config" and inj.args[1].startswith("@")
            data = json.loads(Path(inj.args[1][1:]).read_text())
            assert data["mcpServers"]["powerchannel"]["tools"] == ["*"]


def test_gemini_gets_system_defaults_and_keeps_existing_ones(tmp_path, monkeypatch):
    existing = tmp_path / "defaults.json"
    existing.write_text(json.dumps({"general": {"x": 1}, "mcpServers": {"other": {"command": "o"}}}))
    monkeypatch.setenv("GEMINI_CLI_SYSTEM_DEFAULTS_PATH", str(existing))
    with worker_scope(_worker("gemini_cli")):
        with mcp_injection("gemini_cli") as inj:
            path = inj.env["GEMINI_CLI_SYSTEM_DEFAULTS_PATH"]
            data = json.loads(Path(path).read_text())
            assert data["general"] == {"x": 1} and "other" in data["mcpServers"]
            assert data["mcpServers"]["powerchannel"]["trust"] is True
            assert inj.environ()["GEMINI_CLI_SYSTEM_DEFAULTS_PATH"] == path
    assert not Path(path).exists()
    assert json.loads(existing.read_text())["mcpServers"] == {"other": {"command": "o"}}


def test_cursor_project_config_is_added_then_removed(tmp_path):
    with worker_scope(_worker("cursor")):
        with mcp_injection("cursor", str(tmp_path)) as inj:
            assert inj.args == ["--approve-mcps", "--trust"]
            cfg = tmp_path / ".cursor" / "mcp.json"
            assert "powerchannel" in json.loads(cfg.read_text())["mcpServers"]
    assert not (tmp_path / ".cursor").exists()


def test_cursor_existing_project_config_is_restored(tmp_path):
    cfg = tmp_path / ".cursor" / "mcp.json"
    cfg.parent.mkdir()
    original = json.dumps({"mcpServers": {"mine": {"command": "x"}}})
    cfg.write_text(original)
    with worker_scope(_worker("cursor")):
        with mcp_injection("cursor", str(tmp_path)):
            servers = json.loads(cfg.read_text())["mcpServers"]
            assert set(servers) == {"mine", "powerchannel"}
    assert json.loads(cfg.read_text()) == json.loads(original)


def test_opencode_config_adds_powerchannel():
    from powerspawn.providers import opencode
    cfg = json.loads(opencode._mcp_config(None, channel=True))
    assert set(cfg["mcp"]) == {"powerchannel"}
    assert cfg["mcp"]["powerchannel"]["command"][1:] == ["-m", "powerchannel"]
    assert "powerchannel" not in json.loads(opencode._mcp_config("oc-1"))["mcp"]


# -- lifecycle posts and the IAC.md mirror --------------------------------------

def _messages(db, channel):
    board = store.Board(db)
    try:
        return [(m.author, m.text) for m in board.recent(channel, limit=50)]
    finally:
        board.close()


def test_started_and_finished_posts_are_mirrored_to_iac(board_env):
    w = make_worker("claude", name="claude-live", channel="release", timeout=600, task="Fix login")
    with worker_scope(w):
        sid = logmod.log_spawn_start("Claude", "claude-opus-5-5", "prompt", ["all"], "Fix login")
        board = store.Board(board_env)
        board.post("claude-live", "release", "@coordinator: which branch?")
        board.post("lead", "release", "@claude-live: main")
        board.close()
        logmod.log_spawn_complete(sid, True, "Fixed it on main.", 12.0)
    msgs = _messages(board_env, "release")
    assert msgs[0][0] == "powerspawn" and msgs[0][1].startswith("started claude-live: claude (claude-opus-5-5). Task: Fix login.")
    assert msgs[-1] == ("powerspawn", "finished claude-live in 12s: Fixed it on main.")
    iac = (Path(os.environ["POWERSPAWN_STATE_DIR"]) / "IAC.md").read_text(encoding="utf-8")
    assert "Name: `claude-live` | Channel: `#release`" in iac
    for text in ("started claude-live", "@coordinator: which branch?", "@claude-live: main",
                 "finished claude-live in 12s"):
        assert text in iac
    assert iac.count("started claude-live") == 1


def test_timed_out_and_failed_posts(board_env):
    for name, error, word in (("w-timeout", "Timed out after 600s; process tree killed", "timed out"),
                              ("w-fail", "Exit code 1", "failed")):
        w = make_worker("codex", name=name, channel="ops", timeout=600)
        with worker_scope(w):
            sid = logmod.log_spawn_start("Codex", "default", "p", [], "t")
            logmod.log_spawn_complete(sid, False, "", 600.0, error=error)
        assert _messages(board_env, "ops")[-1][1].startswith(f"{word} {name} after 600s")


def test_name_without_channel_is_logged_but_nothing_posted(board_env):
    with worker_scope(make_worker("codex", name="solo")):
        sid = logmod.log_spawn_start("Codex", "default", "p", [], "t")
        logmod.log_spawn_complete(sid, True, "ok", 1.0)
    iac = (Path(os.environ["POWERSPAWN_STATE_DIR"]) / "IAC.md").read_text(encoding="utf-8")
    assert "Name: `solo`" in iac and "Channel:" not in iac
    assert store.Board(board_env).channels() == []


# -- the MCP tools ----------------------------------------------------------------

def test_tool_schemas_have_name_everywhere_and_channel_where_supported():
    from powerspawn import mcp_server
    tools = {t.name: t.inputSchema["properties"] for t in asyncio.run(mcp_server.list_tools())}
    for tool, props in tools.items():
        if tool.startswith("spawn_"):
            assert "name" in props, tool
            assert ("channel" in props) == (tool in mcp_server.CHANNEL_TOOLS), tool
    assert "dedicated" in tools["spawn_codex"]["channel"]["description"]


def test_handle_spawn_end_to_end(board_env):
    from powerspawn import mcp_server
    from powerspawn.providers.types import AgentResult

    def fake_spawn(prompt, *, model=None, timeout=900, task_summary=None):
        sid = logmod.log_spawn_start("Fake", "m1", prompt, [], task_summary)
        assert prompt.startswith("# PowerChannel") and "Do the thing" in prompt
        assert task_summary == "Do the thing"
        logmod.log_spawn_complete(sid, True, "done", 0.5)
        return AgentResult(success=True, text="done")

    async def run():
        out = await mcp_server.handle_spawn({"prompt": "Do the thing", "channel": "dedicated",
                                             "name": "fake-1"}, "codex", fake_spawn)
        resp = json.loads(out[0].text)
        assert resp["name"] == "fake-1" and resp["channel"] == "dm-fake-1"
        # no timeout passed: no limit, so the worker waits up to 12 h for an answer
        assert "watch" in resp and resp["worker_waits_up_to_seconds"] == 43200
        await asyncio.to_thread(mcp_server.agent_manager.wait_for_all, 10)
        res = json.loads((await mcp_server.handle_result({"agent_id": resp["agent_id"]}))[0].text)
        assert res["name"] == "fake-1" and res["channel"] == "dm-fake-1" and res["success"]
        listed = json.loads((await mcp_server.handle_list())[0].text)
        assert any(c["name"] == "fake-1" for c in listed["completed"])
        bad = json.loads((await mcp_server.handle_spawn({"prompt": "x", "channel": "release"},
                                                        "grok", fake_spawn))[0].text)
        assert bad["error_type"] == "ChannelError"

    asyncio.run(run())
    authors = [a for a, _ in _messages(board_env, "dm-fake-1")]
    assert authors == ["powerspawn", "powerspawn"]


def test_claude_provider_passes_the_mcp_config(monkeypatch):
    from powerspawn.providers import claude
    seen = {}

    def fake_run(cmd, cwd, timeout, stdin_text, env):
        seen["cmd"] = cmd
        cfg = cmd[cmd.index("--mcp-config") + 1]
        seen["cfg"] = json.loads(Path(cfg).read_text())
        return 0, json.dumps({"type": "result", "subtype": "success", "result": "ok"}), "", False

    monkeypatch.setattr(claude, "run_captured", fake_run)
    monkeypatch.setattr(claude, "log_spawn_start", lambda **kw: "id")
    monkeypatch.setattr(claude, "log_spawn_complete", lambda **kw: None)
    with worker_scope(_worker("claude")):
        assert claude.spawn_claude("hi").success
    assert "powerchannel" in seen["cfg"]["mcpServers"]
    assert seen["cmd"][-2:] == ["--allowedTools", "mcp__powerchannel"]


def test_shared_channel_mirror_keeps_only_this_workers_messages(board_env):
    w = make_worker("codex", name="w-a", channel="team", timeout=600)
    with worker_scope(w):
        sid = logmod.log_spawn_start("Codex", "default", "p", [], "t")
        board = store.Board(board_env)
        board.post("powerspawn", "team", "started w-b: claude (m). Task: other.")
        board.post("w-b", "team", "@lead: unrelated")
        board.post("lead", "team", "@w-a: use main")
        board.post("lead", "team", "@all: freeze at 5")
        board.post("w-a", "team", "ok")
        board.close()
        logmod.log_spawn_complete(sid, True, "done", 2.0)
    iac = (Path(os.environ["POWERSPAWN_STATE_DIR"]) / "IAC.md").read_text(encoding="utf-8")
    assert "@w-a: use main" in iac and "@all: freeze at 5" in iac and "finished w-a" in iac
    assert "unrelated" not in iac and "started w-b" not in iac


def test_mcp_handshake_sends_the_instructions():
    """The initialize result carries INSTRUCTIONS (they mention channels)."""
    import subprocess
    import sys
    root = Path(__file__).resolve().parent.parent.parent
    p = subprocess.Popen([sys.executable, "-m", "powerspawn.mcp_server"], cwd=str(root),
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "t", "version": "0"}}}) + "\n")
        p.stdin.flush()
        init = json.loads(p.stdout.readline())["result"]
    finally:
        p.kill()
    assert "channel=\"dedicated\"" in init["instructions"]


def test_mirror_filter_matches_whole_names_only():
    w = Worker(name="auth", cli="codex", channel="team")
    msg = lambda author, text: store.Message(1, "team", author, text, 0.0)
    assert w._concerns_me(msg("lead", "@auth: go"))
    assert w._concerns_me(msg("lead", "@all: freeze"))
    assert w._concerns_me(msg("powerspawn", "finished auth in 3s: ok"))
    assert not w._concerns_me(msg("lead", "@auth-fix: go"))
    assert not w._concerns_me(msg("lead", "@allison: hi"))
    assert not w._concerns_me(msg("powerspawn", "started auth-fix: codex (m)."))


def test_timeout_notice_is_standard_for_every_cli(board_env):
    w = make_worker("cursor", name="w-cur", channel="ops", timeout=900)
    with worker_scope(w):
        sid = logmod.log_spawn_start("Cursor", "auto", "p", [], "t")
        logmod.log_spawn_complete(sid, False, "", 900.0,
                                  error="some stderr\n[powerspawn] cursor timed out after 900s; process tree killed")
    assert _messages(board_env, "ops")[-1][1] == "timed out w-cur after 900s (spawn timeout 900s); PowerSpawn stopped it"


def test_cursor_cleanup_keeps_edits_made_during_the_run(tmp_path):
    cfg = tmp_path / ".cursor" / "mcp.json"
    with worker_scope(_worker("cursor")):
        with mcp_injection("cursor", str(tmp_path)):
            data = json.loads(cfg.read_text())
            data["mcpServers"]["mine"] = {"command": "x"}
            cfg.write_text(json.dumps(data))
    assert json.loads(cfg.read_text())["mcpServers"] == {"mine": {"command": "x"}}


def test_started_notice_keeps_the_cut_marker(board_env):
    w = make_worker("codex", name="w-long", channel="ops", task="x" * 200)
    with worker_scope(w):
        logmod.log_spawn_start("Codex", "m", "p", [], "t")
    assert "x" * 77 + "..." in _messages(board_env, "ops")[-1][1]
