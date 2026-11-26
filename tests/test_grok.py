"""spawn_grok: force by default, success judged from the CLI's JSON result."""
import json

import pytest

from PowerSpawn.providers import grok


def _run(monkeypatch, stdout, returncode=0, stderr="", timed_out=False, **kwargs):
    seen = {}

    def fake_run(cmd, cwd=None, timeout=None, **_):
        seen["cmd"] = cmd
        return returncode, stdout, stderr, timed_out

    monkeypatch.setattr(grok, "run_captured", fake_run)
    return grok.spawn_grok("do it", **kwargs), seen["cmd"]


OK = json.dumps({"text": "Done: fixed the bug.", "stopReason": "end_turn", "sessionId": "s-1",
                 "usage": {"total_tokens": 42}, "total_cost_usd": 0.0123})


def test_force_is_the_default(monkeypatch):
    _, cmd = _run(monkeypatch, OK)
    assert "--always-approve" in cmd and "plan" not in cmd
    assert cmd[cmd.index("--output-format") + 1] == "json"


def test_force_false_is_plan_mode(monkeypatch):
    _, cmd = _run(monkeypatch, OK, force=False)
    assert "--always-approve" not in cmd and cmd[cmd.index("--permission-mode") + 1] == "plan"


def test_success_reads_the_json(monkeypatch):
    res, _ = _run(monkeypatch, OK)
    assert res.success and res.text == "Done: fixed the bug." and res.error is None
    assert res.session_id == "s-1" and res.cost_usd == pytest.approx(0.0123)
    assert res.usage == {"total_tokens": 42}


def test_error_object_is_a_failure(monkeypatch):
    res, _ = _run(monkeypatch, json.dumps({"type": "error", "message": "Couldn't start session: auth"}),
                  returncode=1)
    assert not res.success and "Couldn't start session" in res.error


def test_error_object_with_exit_zero_is_still_a_failure(monkeypatch):
    res, _ = _run(monkeypatch, json.dumps({"type": "error", "message": "boom"}))
    assert not res.success and "boom" in res.error


@pytest.mark.parametrize("stop", ["max_tokens", "max_turns", "refusal"])
def test_abnormal_stop_reason_is_a_failure(monkeypatch, stop):
    res, _ = _run(monkeypatch, json.dumps({"text": "partial", "stopReason": stop}))
    assert not res.success and stop in res.error and res.text == "partial"


def test_empty_text_is_a_failure(monkeypatch):
    res, _ = _run(monkeypatch, json.dumps({"text": "", "stopReason": "end_turn"}))
    assert not res.success and "no text" in res.error


def test_nonzero_exit_with_text_is_a_failure(monkeypatch):
    res, _ = _run(monkeypatch, OK, returncode=1, stderr="crash")
    assert not res.success and "code 1" in res.error and "crash" in res.error


def test_log_line_before_the_json(monkeypatch):
    res, _ = _run(monkeypatch, "updating...\n" + OK)
    assert res.success and res.text == "Done: fixed the bug."


def test_plain_output_falls_back(monkeypatch):
    res, _ = _run(monkeypatch, "just text")
    assert res.success and res.text == "just text"


def test_timeout(monkeypatch):
    res, _ = _run(monkeypatch, "", returncode=-9, timed_out=True, timeout=5)
    assert not res.success and "timed out after 5s" in res.error


def test_schema_default_matches():
    import asyncio
    import inspect
    from PowerSpawn.mcp_server import list_tools
    tools = {t.name: t.inputSchema["properties"] for t in asyncio.run(list_tools())}
    assert tools["spawn_grok"]["force"]["default"] is True
    assert inspect.signature(grok.spawn_grok).parameters["force"].default is True
