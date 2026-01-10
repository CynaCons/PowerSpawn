"""Test IAC.md logging functions."""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

# Import will be set up by conftest.py
from logger import (
    generate_spawn_id,
    log_spawn_start,
    log_spawn_complete,
    get_logger,
    AgentLogger,
)


def test_generate_spawn_id_format():
    """Test spawn ID is 8 character hex string."""
    spawn_id = generate_spawn_id()
    assert len(spawn_id) == 8
    assert all(c in '0123456789abcdef' for c in spawn_id)


def test_generate_spawn_id_unique():
    """Test spawn IDs are unique."""
    ids = [generate_spawn_id() for _ in range(100)]
    assert len(set(ids)) == 100  # All unique


def test_log_spawn_start_creates_entry(tmp_path):
    """Test log_spawn_start creates IAC.md entry."""
    # Create a logger instance with temp directory
    with patch('logger.get_output_dir', return_value=tmp_path):
        logger = AgentLogger()

        spawn_id = logger.log_spawn_start(
            agent="Claude",
            model="sonnet",
            prompt="Test prompt",
            tools=["Bash", "Read"],
            task_summary="Test task"
        )

        # Check that IAC.md was created
        iac_file = tmp_path / "IAC.md"
        assert iac_file.exists()

        content = iac_file.read_text(encoding='utf-8')

        # Verify spawn_id is in the content
        assert spawn_id in content

        # Verify key information is present
        assert "Test task" in content
        assert "Claude" in content
        assert "sonnet" in content
        assert "Bash, Read" in content

        # Verify running status
        assert "Running" in content or "⏳" in content


def test_log_spawn_start_without_task_summary(tmp_path):
    """Test log_spawn_start generates task_summary from prompt."""
    with patch('logger.get_output_dir', return_value=tmp_path):
        logger = AgentLogger()

        long_prompt = "This is a very long first line that should be truncated when used as task summary " * 5
        spawn_id = logger.log_spawn_start(
            agent="Claude",
            model="haiku",
            prompt=long_prompt,
            tools=[]
        )

        iac_file = tmp_path / "IAC.md"
        content = iac_file.read_text(encoding='utf-8')

        # Should contain truncated summary (first 80 chars + ...)
        assert "This is a very long first line" in content


def test_log_spawn_complete_updates_entry(tmp_path):
    """Test log_spawn_complete updates existing entry."""
    with patch('logger.get_output_dir', return_value=tmp_path):
        logger = AgentLogger()

        # First create an entry
        spawn_id = logger.log_spawn_start(
            agent="Claude",
            model="haiku",
            prompt="Test prompt",
            tools=[],
            task_summary="Test task"
        )

        # Verify initial state
        iac_file = tmp_path / "IAC.md"
        content_before = iac_file.read_text(encoding='utf-8')
        assert "Running" in content_before or "⏳" in content_before

        # Then complete it
        logger.log_spawn_complete(
            spawn_id=spawn_id,
            success=True,
            result_text="Test result output",
            duration_seconds=1.5,
            cost_usd=0.01
        )

        # Verify completion
        content_after = iac_file.read_text(encoding='utf-8')

        # Should have completion marker
        assert "Done" in content_after or "✅" in content_after

        # Should show duration and cost
        assert "1.5s" in content_after
        assert "$0.01" in content_after or "0.0100" in content_after

        # Should contain result
        assert "Test result output" in content_after


def test_log_spawn_complete_with_failure(tmp_path):
    """Test log_spawn_complete handles failures correctly."""
    with patch('logger.get_output_dir', return_value=tmp_path):
        logger = AgentLogger()

        spawn_id = logger.log_spawn_start(
            agent="Claude",
            model="sonnet",
            prompt="Test prompt",
            tools=[],
            task_summary="Test task"
        )

        # Complete with failure
        logger.log_spawn_complete(
            spawn_id=spawn_id,
            success=False,
            result_text="Error output",
            duration_seconds=0.5,
            cost_usd=0.0,
            error="Test error message"
        )

        iac_file = tmp_path / "IAC.md"
        content = iac_file.read_text(encoding='utf-8')

        # Should have failure marker
        assert "Failed" in content or "❌" in content

        # Should show error message
        assert "Test error message" in content


def test_multiple_spawns_newest_first(tmp_path):
    """Test that multiple spawns are ordered newest first."""
    with patch('logger.get_output_dir', return_value=tmp_path):
        logger = AgentLogger()

        # Create multiple spawns
        spawn_id_1 = logger.log_spawn_start(
            agent="Claude",
            model="haiku",
            prompt="First task",
            tools=[],
            task_summary="Task 1"
        )

        spawn_id_2 = logger.log_spawn_start(
            agent="Claude",
            model="sonnet",
            prompt="Second task",
            tools=[],
            task_summary="Task 2"
        )

        iac_file = tmp_path / "IAC.md"
        content = iac_file.read_text(encoding='utf-8')

        # Task 2 entry should appear before Task 1 entry (newest first)
        # Use entry headers to avoid matching Active Agents table
        pos_task_1 = content.find("### 🤖 Task 1")
        pos_task_2 = content.find("### 🤖 Task 2")

        assert pos_task_2 < pos_task_1, "Newest entry should appear first"


def test_max_entries_limit(tmp_path):
    """Test that IAC.md respects MAX_IAC_ENTRIES limit."""
    with patch('logger.get_output_dir', return_value=tmp_path):
        logger = AgentLogger()

        # Create more than MAX_IAC_ENTRIES spawns (50)
        # We spawn 60 agents to ensure at least 10 are trimmed
        spawn_ids = []
        for i in range(60):
            spawn_id = logger.log_spawn_start(
                agent="Claude",
                model="haiku",
                prompt=f"Task {i}",
                tools=[],
                task_summary=f"Task {i}"
            )
            spawn_ids.append(spawn_id)

        iac_file = tmp_path / "IAC.md"
        content = iac_file.read_text(encoding='utf-8')

        # Should only have last 50 task ENTRIES (not in Active Agents table)
        # Check for entry headers (### 🤖 Task X) to verify entry limits
        assert "### 🤖 Task 59" in content  # Most recent entry (60th)
        assert "### 🤖 Task 10" in content   # 50th from end (index 10-59 = 50 items)
        assert "### 🤖 Task 9" not in content  # Entry should be trimmed


def test_global_logger_functions(tmp_path):
    """Test global log_spawn_start and log_spawn_complete functions."""
    with patch('logger.get_output_dir', return_value=tmp_path):
        # Reset global logger
        import logger as logger_module
        logger_module._logger = None

        # Use global functions
        spawn_id = log_spawn_start(
            agent="Claude",
            model="opus",
            prompt="Global test",
            tools=["Bash"],
            task_summary="Global task"
        )

        log_spawn_complete(
            spawn_id=spawn_id,
            success=True,
            result_text="Success",
            duration_seconds=2.5,
            cost_usd=0.05
        )

        # Verify files were created
        iac_file = tmp_path / "IAC.md"
        assert iac_file.exists()

        content = iac_file.read_text(encoding='utf-8')
        assert "Global task" in content
        assert "Done" in content or "✅" in content
