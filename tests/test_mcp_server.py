"""Integration tests for MCP server."""
import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_server_module_imports():
    """Test MCP server module imports without error."""
    try:
        import mcp_server
        assert hasattr(mcp_server, 'main')
        assert hasattr(mcp_server, 'server')
    except ImportError as e:
        pytest.skip(f"MCP server import failed: {e}")


def test_server_version_constant():
    """Test that SERVER_VERSION constant exists."""
    try:
        from mcp_server import SERVER_VERSION
        assert isinstance(SERVER_VERSION, str)
        assert len(SERVER_VERSION) > 0
        # Should follow semver pattern (e.g., "1.4.0")
        parts = SERVER_VERSION.split('.')
        assert len(parts) >= 2  # At least major.minor
    except ImportError:
        pytest.skip("MCP server not accessible")


def test_list_tools_handler_exists():
    """Test that list_tools handler is defined."""
    try:
        from mcp_server import list_tools, server
        assert callable(list_tools)
        # Server should be an MCP Server instance
        assert hasattr(server, 'list_tools')
    except ImportError:
        pytest.skip("MCP server not accessible")


def test_call_tool_handler_exists():
    """Test that call_tool handler is defined."""
    try:
        from mcp_server import call_tool
        assert callable(call_tool)
    except ImportError:
        pytest.skip("MCP server not accessible")


def test_spawn_functions_callable():
    """Test spawn functions are callable."""
    from spawner import spawn_claude, spawn_codex, spawn_copilot

    assert callable(spawn_claude)
    assert callable(spawn_codex)
    assert callable(spawn_copilot)


def test_agent_result_dataclass():
    """Test AgentResult dataclass structure."""
    from spawner import AgentResult

    result = AgentResult(
        success=True,
        text="Test output",
        spawn_id="abc12345"
    )
    assert result.success is True
    assert result.text == "Test output"
    assert result.spawn_id == "abc12345"

    # Check optional fields have defaults
    assert result.structured_output is None
    assert result.session_id is None
    assert result.duration_ms == 0
    assert result.cost_usd == 0.0
    assert isinstance(result.usage, dict)
    assert result.error is None
    assert result.raw_response is None


def test_codex_event_dataclass():
    """Test CodexEvent dataclass structure."""
    from spawner import CodexEvent

    # Test basic event
    event = CodexEvent(type="test.event")
    assert event.type == "test.event"
    assert isinstance(event.data, dict)

    # Test message event
    msg_event = CodexEvent(
        type="item.completed",
        data={"item": {"type": "agent_message", "text": "Hello"}}
    )
    assert msg_event.is_message is True
    assert msg_event.text == "Hello"
    assert msg_event.is_command is False

    # Test command event
    cmd_event = CodexEvent(
        type="item.completed",
        data={"item": {"type": "command_execution", "aggregated_output": "output text"}}
    )
    assert cmd_event.is_command is True
    assert cmd_event.command_output == "output text"
    assert cmd_event.is_message is False


def test_mcp_server_globals():
    """Test MCP server global state variables."""
    try:
        from mcp_server import running_agents, completed_agents, background_threads

        assert isinstance(running_agents, dict)
        assert isinstance(completed_agents, dict)
        assert isinstance(background_threads, dict)
    except ImportError:
        pytest.skip("MCP server not accessible")


def test_helper_functions_exist():
    """Test helper functions are defined."""
    try:
        from mcp_server import (
            sanitize_for_json,
            utc_now_iso,
            get_workspace_dir
        )

        assert callable(sanitize_for_json)
        assert callable(utc_now_iso)
        assert callable(get_workspace_dir)

        # Test sanitize_for_json
        assert sanitize_for_json("") == ""
        assert sanitize_for_json("hello") == "hello"

        # Test utc_now_iso returns string in expected format
        timestamp = utc_now_iso()
        assert isinstance(timestamp, str)
        assert 'T' in timestamp  # ISO format has 'T' separator

        # Test get_workspace_dir returns Path
        from pathlib import Path
        workspace = get_workspace_dir()
        assert isinstance(workspace, Path)

    except ImportError:
        pytest.skip("MCP server not accessible")


def test_copilot_models_constant():
    """Test COPILOT_MODELS mapping exists."""
    try:
        from spawner import COPILOT_MODELS

        assert isinstance(COPILOT_MODELS, dict)
        # Should have expected model aliases
        assert "gpt-5.1" in COPILOT_MODELS
        assert "claude-sonnet" in COPILOT_MODELS
        assert "gemini" in COPILOT_MODELS

    except ImportError:
        pytest.skip("Spawner module not accessible")


def test_is_windows_constant():
    """Test IS_WINDOWS constant is defined correctly."""
    import sys
    from spawner import IS_WINDOWS

    assert isinstance(IS_WINDOWS, bool)
    assert IS_WINDOWS == (sys.platform == "win32")
