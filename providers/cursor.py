"""
Cursor CLI Provider

Drives the Cursor CLI agent (`cursor-agent`) in headless/print mode.
Auth is via the CURSOR_API_KEY environment variable (read by the CLI itself),
so no key handling happens here — same as the Gemini CLI provider.
"""

import os
import subprocess
import time
import sys
from pathlib import Path
from typing import Optional

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from ..proc import run_captured
from .types import AgentResult

IS_WINDOWS = sys.platform == "win32"

# The Cursor CLI binary. Normally `cursor-agent` (the installer puts it on
# PATH). TEMPORARY SHIM: honor CURSOR_AGENT_BIN so a machine whose install
# isn't on PATH can point at the full path (e.g. an agent.cmd). See TODO.md —
# this override should be removed once installs land cursor-agent on PATH.
CURSOR_BIN = os.environ.get("CURSOR_AGENT_BIN", "cursor-agent")

def get_workspace_dir() -> Path:
    return Path(__file__).parent.parent.parent

def spawn_cursor(
    prompt: str,
    *,
    model: str = None,
    timeout: int = 300,
    task_summary: Optional[str] = None,
    working_dir: Optional[str] = None,
    force: bool = False,
) -> AgentResult:
    """
    Spawn a Cursor CLI agent.

    Assumes `cursor-agent` is on PATH and CURSOR_API_KEY is set. Without
    `force`, the agent proposes changes but does not apply them to files.
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("cursor", model)

    tools_list = ["all"]
    if force:
        tools_list.append("force")

    spawn_id = log_spawn_start(
        agent="Cursor",
        model=resolved_model,
        prompt=prompt,
        tools=tools_list,
        task_summary=task_summary,
        agent_type="CLI"
    )

    # cursor-agent -p "<prompt>" --model <m> --output-format text [--force]
    cmd = [CURSOR_BIN, "-p", prompt, "--model", resolved_model, "--output-format", "text"]

    if force:
        cmd.append("--force")

    cwd = working_dir or str(get_workspace_dir())

    try:
        # Hardened run: output to temp files (no pipe-EOF drain hang),
        # process-tree kill on timeout. See powerspawn/proc.py.
        returncode, output_text, error_text, timed_out = run_captured(
            cmd, cwd=cwd, timeout=timeout,
        )

        duration = time.time() - start_time

        if timed_out:
            error_text = (error_text + f"\n[powerspawn] cursor timed out after "
                          f"{timeout}s; process tree killed").strip()

        success = (not timed_out) and returncode == 0 and output_text != ""

        if not success and not output_text:
            error_msg = error_text or f"Exit code {returncode}"
            log_spawn_complete(spawn_id, False, "", duration, 0.0, error_msg)
            return AgentResult(success=False, text="", spawn_id=spawn_id, error=error_msg, provider="cursor")

        log_spawn_complete(
            spawn_id=spawn_id,
            success=success,
            result_text=output_text,
            duration_seconds=duration,
            cost_usd=0.0,
            error=error_text if not success else None
        )

        return AgentResult(
            success=success,
            text=output_text,
            spawn_id=spawn_id,
            duration_ms=int(duration * 1000),
            error=error_text if not success else None,
            model=resolved_model,
            provider="cursor"
        )

    except Exception as e:
        duration = time.time() - start_time
        log_spawn_complete(spawn_id, False, "", duration, 0.0, str(e))
        return AgentResult(success=False, text="", spawn_id=spawn_id, error=str(e), provider="cursor")
