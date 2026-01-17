"""Test response parsing functions."""
import pytest
from PowerSpawn.providers.claude import _parse_claude_response
from PowerSpawn.providers.codex import _parse_codex_event


def test_parse_valid_claude_json():
    """Test parsing valid Claude JSON response."""
    json_str = '{"type": "result", "subtype": "success", "result": "Hello", "total_cost_usd": 0.01}'
    result = _parse_claude_response(json_str)
    assert result is not None
    assert result.success is True
    assert result.text == "Hello"
    assert result.cost_usd == 0.01


def test_parse_claude_error():
    """Test parsing Claude error response."""
    json_str = '{"type": "result", "subtype": "error", "result": "Something went wrong"}'
    result = _parse_claude_response(json_str)
    assert result is not None
    assert result.success is False
    assert result.error == "Something went wrong"


def test_parse_invalid_json():
    """Test parsing invalid JSON returns error."""
    result = _parse_claude_response("not json {")
    assert result.success is False
    assert result.error is not None
    assert "Failed to parse JSON" in result.error


def test_parse_valid_codex_event():
    """Test parsing valid Codex JSONL event."""
    json_str = '{"type": "thread.started", "thread_id": "abc123"}'
    event = _parse_codex_event(json_str)
    assert event is not None
    assert event.type == "thread.started"
    assert event.data["thread_id"] == "abc123"


def test_parse_codex_message_event():
    """Test parsing Codex message completion event."""
    json_str = '{"type": "item.completed", "item": {"type": "agent_message", "text": "Task done"}}'
    event = _parse_codex_event(json_str)
    assert event is not None
    assert event.is_message is True
    assert event.text == "Task done"


def test_parse_codex_invalid_json():
    """Test parsing invalid Codex JSON returns None."""
    event = _parse_codex_event("not json {")
    assert event is None
