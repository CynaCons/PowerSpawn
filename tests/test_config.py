"""Test configuration loading."""
import os
import json
import pytest
from pathlib import Path
from PowerSpawn.config import Settings

@pytest.fixture
def mock_keys_file(tmp_path, monkeypatch):
    """Create a mock api_keys.json"""
    keys = {"grok": "test_file_key"}
    key_file = tmp_path / "api_keys.json"
    with open(key_file, "w") as f:
        json.dump({"XAI_API_KEY": "test_file_key"}, f)
    
    return key_file

def test_settings_load_priority(mock_keys_file, monkeypatch):
    """Test that file keys take priority over env vars."""
    monkeypatch.setenv("POWERSPAWN_CONFIG_DIR", str(mock_keys_file.parent))
    monkeypatch.setenv("POWERSPAWN_WORKSPACE", str(mock_keys_file.parent / "workspace"))
    monkeypatch.setenv("XAI_API_KEY", "test_env_key")

    settings = Settings()
    assert settings.get_api_key("grok") == "test_file_key"

def test_settings_env_fallback(tmp_path, monkeypatch):
    """Test fallback to env vars if no api_keys.json is found."""
    monkeypatch.setenv("MISTRAL_API_KEY", "env_mistral_key")
    monkeypatch.setenv("POWERSPAWN_CONFIG_DIR", str(tmp_path / "missing"))
    monkeypatch.setenv("POWERSPAWN_WORKSPACE", str(tmp_path))

    settings = Settings()
    assert settings.get_api_key("mistral") == "env_mistral_key"

def test_model_alias_resolution(monkeypatch):
    """Test model alias resolution."""
    # Mock models.json
    models = {
        "test_provider": {
            "default": "model-v1",
            "aliases": {
                "latest": "model-v2-beta",
                "stable": "model-v1"
            }
        }
    }
    
    monkeypatch.setattr("PowerSpawn.config.Settings._load_models", lambda self: setattr(self, "_models", models))
    
    settings = Settings()
    assert settings.get_model_alias("test_provider", "latest") == "model-v2-beta"
    assert settings.get_model_alias("test_provider", None) == "model-v1"
    assert settings.get_model_alias("test_provider", "unknown") == "unknown"


def test_codex_gpt6_astra_sol_luna_aliases():
    """Live models.json must expose GPT-6 Astra / Sol / Luna for spawn_codex (sol = 6.1)."""
    settings = Settings()
    assert settings.get_model_alias("codex", None) == "gpt-6.1-sol"
    assert settings.get_model_alias("codex", "astra") == "gpt-6-astra"
    assert settings.get_model_alias("codex", "sol") == "gpt-6.1-sol"
    assert settings.get_model_alias("codex", "gpt-6-sol") == "gpt-6-sol"
    assert settings.get_model_alias("codex", "luna") == "gpt-6-luna"
    assert settings.get_model_alias("codex", "gpt-6.1-sol") == "gpt-6.1-sol"
    # GPT-5.6 generation stays reachable (Terra has no GPT-6 successor)
    assert settings.get_model_alias("codex", "terra") == "gpt-5.6-terra"
    assert settings.get_model_alias("codex", "tera") == "gpt-5.6-terra"
    assert settings.get_model_alias("codex", "gpt-5.6-sol") == "gpt-5.6-sol"
    for alias in ("astra", "sol", "luna", "gpt-6-astra", "gpt-6-sol", "gpt-6-luna", "gpt-5.6-terra"):
        assert alias in settings.get_model_list("codex")


def test_codex_retired_models_removed():
    """Models Codex retired (gpt-5.4*, gpt-5.3-codex*, older codex ids) must not be offered."""
    codex = Settings().get_model_list("codex")
    for retired in ("gpt-5.4", "gpt-5.4-mini", "gpt-5.3-codex", "gpt-5.3-codex-spark",
                    "gpt-5.2-codex", "gpt-5.1-codex", "gpt-5.1-codex-max"):
        assert retired not in codex


def test_grok_cli_defaults_to_4_6():
    """Grok CLI path defaults to grok-4.6; 4.7 and 4.5 stay selectable; legacy aliases map to the default."""
    settings = Settings()
    assert settings.get_model_alias("grok", None) == "grok-4.6"
    assert settings.get_model_alias("grok", "grok-4.7") == "grok-4.7"
    assert settings.get_model_alias("grok", "grok-4.5") == "grok-4.5"
    assert settings.get_model_alias("grok", "cursor-grok-4.5") == "grok-4.5"
    assert settings.get_model_alias("grok", "build") == "grok-4.6"
    assert "grok-4.6" in settings.get_model_list("grok")


def test_latest_frontier_defaults():
    """Oct 2026 refresh: Copilot on Opus 5.5, Grok API on 4.7, Gemini flash alias on 3.8."""
    settings = Settings()
    assert settings.get_model_alias("copilot", None) == "claude-opus-5.5"
    assert settings.get_model_alias("claude", "opus-5.5") == "claude-opus-5-5"
    assert settings.get_model_alias("claude", "fable-5.1") == "claude-fable-5-1"
    assert settings.get_model_alias("grok-api", None) == "grok-4.7"
    assert settings.get_model_alias("gemini", "gemini-flash") == "gemini-3.8-flash"
    assert settings.get_model_alias("gemini-cli", "gemini-flash") == "gemini-3.8-flash"


def test_every_provider_default_is_offered():
    """Each provider's default must be one of its alias keys or resolved values."""
    settings = Settings()
    for provider, cfg in settings._models.items():
        aliases = cfg.get("aliases", {})
        assert cfg["default"] in set(aliases) | set(aliases.values()), provider
