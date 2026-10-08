"""Workspace / state / config resolution for installed vs vendored PowerSpawn."""
import json
from pathlib import Path

from PowerSpawn import paths
from PowerSpawn.config import Settings


def test_workspace_is_client_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("POWERSPAWN_WORKSPACE", raising=False)
    monkeypatch.chdir(tmp_path)
    assert paths.get_workspace_dir() == tmp_path.resolve()


def test_workspace_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("POWERSPAWN_WORKSPACE", str(tmp_path))
    assert paths.get_workspace_dir() == tmp_path.resolve()


def test_installed_package_writes_state_into_project(tmp_path, monkeypatch):
    """Package outside the workspace (site-packages / uvx cache) -> <project>/.powerspawn."""
    monkeypatch.delenv("POWERSPAWN_STATE_DIR", raising=False)
    monkeypatch.setenv("POWERSPAWN_WORKSPACE", str(tmp_path))
    assert paths.get_state_dir() == tmp_path.resolve() / ".powerspawn"


def test_vendored_package_keeps_state_next_to_package(monkeypatch):
    """Legacy layout: <project>/powerspawn/ -> IAC.md stays in powerspawn/."""
    monkeypatch.delenv("POWERSPAWN_STATE_DIR", raising=False)
    monkeypatch.setenv("POWERSPAWN_WORKSPACE", str(paths.PACKAGE_DIR.parent))
    assert paths.get_state_dir() == paths.PACKAGE_DIR


def test_models_override_is_layered(tmp_path, monkeypatch):
    """A project models.json adds/changes aliases without replacing the bundled registry."""
    monkeypatch.setenv("POWERSPAWN_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("POWERSPAWN_CONFIG_DIR", str(tmp_path / "no-user-config"))
    (tmp_path / ".powerspawn").mkdir()
    (tmp_path / ".powerspawn" / "models.json").write_text(json.dumps(
        {"codex": {"default": "gpt-7", "aliases": {"gpt-7": "gpt-7"}}}), encoding="utf-8")
    s = Settings()
    assert s.get_model_alias("codex", None) == "gpt-7"
    assert s.get_model_alias("codex", "astra") == "gpt-6-astra"  # bundled alias kept
    assert s.get_model_alias("claude", None) == "sonnet"          # other providers untouched


def test_project_api_keys_beat_user_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("POWERSPAWN_WORKSPACE", str(tmp_path / "proj"))
    monkeypatch.setenv("POWERSPAWN_CONFIG_DIR", str(tmp_path / "user"))
    for d, key in (("user", "user-key"), ("proj/.powerspawn", "proj-key")):
        (tmp_path / d).mkdir(parents=True)
        (tmp_path / d / "api_keys.json").write_text(json.dumps({"MISTRAL_API_KEY": key}), encoding="utf-8")
    assert Settings().get_api_key("mistral") == "proj-key"
