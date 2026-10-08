"""verify_providers_availability: one entry per spawn_* tool, CLI by PATH, API by key."""

from PowerSpawn.providers import availability


def test_every_spawn_tool_is_covered(monkeypatch):
    from PowerSpawn.mcp_server import list_tools
    import asyncio

    spawn_tools = {t.name for t in asyncio.run(list_tools()) if t.name.startswith("spawn_")}
    assert {p["tool"] for p in availability.verify_providers_availability()["providers"].values()} == spawn_tools


def test_cli_by_path_and_api_by_key(monkeypatch):
    monkeypatch.setattr(availability.shutil, "which", lambda b: "/bin/x" if b == "codex" else None)
    monkeypatch.setattr(availability.settings, "get_api_key", lambda p: "k" if p == "mistral" else None)
    report = availability.verify_providers_availability()
    p = report["providers"]
    assert p["codex"]["available"] and p["codex"]["message"] == "ready"
    assert not p["claude"]["available"] and "'claude' is not on PATH" in p["claude"]["message"]
    assert p["mistral"]["available"] and not p["grok_api"]["available"]
    assert report["summary"] == {"total_providers": 9, "available": 2,
                                 "cli_available": 1, "api_available": 1}
    assert report["overall"] == "limited"


def test_none_available(monkeypatch):
    monkeypatch.setattr(availability.shutil, "which", lambda b: None)
    monkeypatch.setattr(availability.settings, "get_api_key", lambda p: None)
    assert availability.verify_providers_availability()["overall"] == "none"
