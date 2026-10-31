"""
Cursor CLI Provider

Runs a prompt through the Cursor CLI (cursor-agent) headless, so Cursor credits
can reach Gemini / Grok / Kimi / GPT / Claude models.
"""

import os
import shutil
import subprocess
import time
import sys
from pathlib import Path
from typing import Optional

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from .types import AgentResult

IS_WINDOWS = sys.platform == "win32"

def get_workspace_dir() -> Path:
    return Path(__file__).parent.parent.parent


def _find_cursor_cli() -> str:
    """Resolve the cursor-agent executable (the Windows installer is not always on PATH)."""
    found = shutil.which("cursor-agent")
    if found:
        return found
    local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    fallback = Path(local_app_data) / "cursor-agent" / "cursor-agent.cmd"
    return str(fallback) if fallback.exists() else "cursor-agent"


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Kill the CLI and its children (cmd -> powershell -> node on Windows)."""
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=15,
            )
        else:
            proc.kill()
    except Exception:
        pass


def spawn_cursor(
    prompt: str,
    *,
    model: str = None,
    timeout: int = 600,
    task_summary: Optional[str] = None,
    working_dir: Optional[str] = None,
    read_only: bool = True,
) -> AgentResult:
    """
    Spawn a Cursor CLI agent (headless).

    Context Handling:
        Cursor CLI loads AGENTS.md and .cursor/rules from the workspace.

    Args:
        read_only: If True (default), run in `--mode ask` (read-only Q&A).
                   If False, the agent may edit files and run commands (`--force`).

    Long prompts:
        The prompt is piped via stdin (`-p` with no prompt argument), so the
        8191-char cmd.exe command-line limit never applies.
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("cursor", model)

    spawn_id = log_spawn_start(
        agent="Cursor",
        model=resolved_model,
        prompt=prompt,
        tools=["mode:ask"] if read_only else ["all", "force"],
        task_summary=task_summary,
        agent_type="CLI"
    )

    cwd = working_dir or str(get_workspace_dir())

    # cursor-agent -p --model <m> --output-format text --trust --workspace <dir> [--mode ask | --force]
    cmd = [
        _find_cursor_cli(),
        "-p",                           # Print mode (headless); prompt comes from stdin
        "--model", resolved_model,
        "--output-format", "text",
        "--trust",                      # Skip the workspace-trust prompt
        "--workspace", cwd,
    ]
    if read_only:
        cmd.extend(["--mode", "ask"])
    else:
        cmd.append("--force")           # Apply edits / run commands without approval

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            shell=IS_WINDOWS,
            encoding='utf-8',
            errors='replace',
        )

        try:
            stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            # shell=True only kills cmd.exe; take the whole tree down so pipes close
            _kill_process_tree(proc)
            try:
                proc.communicate(timeout=10)
            except Exception:
                pass
            duration = time.time() - start_time
            error_msg = f"Timed out after {timeout}s"
            log_spawn_complete(spawn_id, False, "", duration, 0.0, error_msg)
            return AgentResult(success=False, text="", spawn_id=spawn_id, error=error_msg, provider="cursor")

        duration = time.time() - start_time

        output_text = stdout.strip() if stdout else ""
        error_text = stderr.strip() if stderr else ""

        success = proc.returncode == 0 and output_text != ""

        # If failure with no output, use stderr
        if not success and not output_text:
            error_msg = error_text or f"Exit code {proc.returncode}"
            log_spawn_complete(spawn_id, False, "", duration, 0.0, error_msg)
            return AgentResult(success=False, text="", spawn_id=spawn_id, error=error_msg, provider="cursor")

        log_spawn_complete(
            spawn_id=spawn_id,
            success=success,
            result_text=output_text,
            duration_seconds=duration,
            cost_usd=0.0,
            error=(error_text or f"Exit code {proc.returncode}") if not success else None
        )

        return AgentResult(
            success=success,
            text=output_text,
            spawn_id=spawn_id,
            duration_ms=int(duration * 1000),
            error=(error_text or f"Exit code {proc.returncode}") if not success else None,
            model=resolved_model,
            provider="cursor"
        )

    except Exception as e:
        duration = time.time() - start_time
        if proc and proc.poll() is None:
            _kill_process_tree(proc)
        log_spawn_complete(spawn_id, False, "", duration, 0.0, str(e))
        return AgentResult(success=False, text="", spawn_id=spawn_id, error=str(e), provider="cursor")
