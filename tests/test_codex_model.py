"""spawn_codex passes --model only when the caller asked for one."""

from PowerSpawn.providers import codex


def _run(monkeypatch, **kwargs):
    seen = {}

    def fake_stream(prompt, model, bypass_sandbox, working_dir, timeout):
        seen["model"] = model
        return iter(())

    monkeypatch.setattr(codex, "_spawn_codex_stream", fake_stream)
    monkeypatch.setattr(codex, "log_spawn_start", lambda **kw: "id")
    monkeypatch.setattr(codex, "log_spawn_complete", lambda **kw: None)
    result = codex.spawn_codex("hi", **kwargs)
    return seen["model"], result


def test_no_model_lets_codex_choose(monkeypatch):
    model, result = _run(monkeypatch)
    assert model is None
    assert result.model == "codex default"


def test_alias_is_resolved_and_passed(monkeypatch):
    model, result = _run(monkeypatch, model="sol")
    assert model == "gpt-6.1-sol" and result.model == "gpt-6.1-sol"
