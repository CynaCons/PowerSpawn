"""Test that all PowerSpawn modules import correctly."""
import pytest


def test_spawner_imports():
    """Test spawner module imports."""
    from spawner import spawn_claude, spawn_codex, spawn_copilot, AgentResult
    assert callable(spawn_claude)
    assert callable(spawn_codex)
    assert callable(spawn_copilot)


def test_logger_imports():
    """Test logger module imports."""
    from logger import log_spawn_start, log_spawn_complete, generate_spawn_id
    assert callable(log_spawn_start)
    assert callable(log_spawn_complete)
    assert callable(generate_spawn_id)


def test_parser_imports():
    """Test parser module imports."""
    from parser import parse_claude_response, parse_codex_event
    assert callable(parse_claude_response)
    assert callable(parse_codex_event)
