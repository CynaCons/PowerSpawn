"""Integration tests for MCP server."""
import pytest


def test_server_module_imports():
    """Test MCP server module imports without error."""
    try:
        from PowerSpawn import mcp_server
        assert hasattr(mcp_server, 'main')
        assert hasattr(mcp_server, 'server')
    except ImportError as e:
        pytest.skip(f"MCP server import failed: {e}")


def test_server_version_constant():
    """Test that SERVER_VERSION constant exists."""
    try:
        from PowerSpawn.mcp_server import SERVER_VERSION
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
        from PowerSpawn.mcp_server import list_tools, server
        assert callable(list_tools)
        # Server should be an MCP Server instance
        assert hasattr(server, 'list_tools')
    except ImportError:
        pytest.skip("MCP server not accessible")


def test_call_tool_handler_exists():
    """Test that call_tool handler is defined."""
    try:
        from PowerSpawn.mcp_server import call_tool
        assert callable(call_tool)
    except ImportError:
        pytest.skip("MCP server not accessible")


def test_spawn_functions_callable():
    """Test spawn functions are callable."""
    from PowerSpawn.providers import spawn_claude, spawn_codex, spawn_copilot, spawn_gemini_cli

    assert callable(spawn_claude)
    assert callable(spawn_codex)
    assert callable(spawn_copilot)
    assert callable(spawn_gemini_cli)


def test_agent_result_dataclass():
    """Test AgentResult dataclass structure."""
    from PowerSpawn.providers import AgentResult

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
    from PowerSpawn.providers.codex import CodexEvent

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


def test_agent_manager_exists():
    """Test Agent Manager is accessible."""
    try:
        from PowerSpawn.agent_manager import agent_manager
        assert agent_manager is not None
    except ImportError:
        pytest.skip("Agent manager not accessible")


def test_config_models_exist():
    """Test Config settings are accessible."""
    try:
        from PowerSpawn.config import settings
        copilot_models = settings.get_model_list("copilot")
        assert isinstance(copilot_models, list)
        assert len(copilot_models) > 0
    except ImportError:
        pytest.skip("Config not accessible")
