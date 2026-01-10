"""Test that all PowerSpawn modules import correctly."""
import pytest


def test_provider_imports():
    """Test provider module imports."""
    from providers import (
        spawn_claude, 
        spawn_codex, 
        spawn_copilot, 
        spawn_grok,
        spawn_gemini,
        spawn_gemini_cli,
        spawn_mistral,
        AgentResult
    )
    assert callable(spawn_claude)
    assert callable(spawn_codex)
    assert callable(spawn_copilot)
    assert callable(spawn_grok)
    assert callable(spawn_gemini)
    assert callable(spawn_gemini_cli)
    assert callable(spawn_mistral)


def test_logger_imports():
    """Test logger module imports."""
    from logger import log_spawn_start, log_spawn_complete, generate_spawn_id
    assert callable(log_spawn_start)
    assert callable(log_spawn_complete)
    assert callable(generate_spawn_id)


def test_config_imports():
    """Test config module imports."""
    from config import settings
    assert settings is not None
