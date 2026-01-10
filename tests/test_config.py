"""Test configuration loading."""
import os
import json
import pytest
from pathlib import Path
from powerspawn.config import Settings

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
    # Mock __file__ in config module so Path(__file__).parent points to tmp_path
    monkeypatch.setattr("powerspawn.config.__file__", str(mock_keys_file.parent / "config.py"))
    
    monkeypatch.setenv("XAI_API_KEY", "test_env_key")
    
    settings = Settings()
    assert settings.get_api_key("grok") == "test_file_key"

def test_settings_env_fallback(monkeypatch):
    """Test fallback to env vars if file missing."""
    monkeypatch.setenv("MISTRAL_API_KEY", "env_mistral_key")
    
    # Point __file__ to a non-existent dir so no api_keys.json found
    monkeypatch.setattr("powerspawn.config.__file__", "/non/existent/config.py")
    
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
    
    monkeypatch.setattr("powerspawn.config.Settings._load_models", lambda self: setattr(self, "_models", models))
    
    settings = Settings()
    assert settings.get_model_alias("test_provider", "latest") == "model-v2-beta"
    assert settings.get_model_alias("test_provider", None) == "model-v1"
    assert settings.get_model_alias("test_provider", "unknown") == "unknown"
