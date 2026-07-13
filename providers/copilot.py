"""
Copilot CLI Provider
"""

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

def get_workspace_dir() -> Path:
    return Path(__file__).parent.parent.parent

def spawn_copilot(
    prompt: str,
    *,
    model: str = None,
    timeout: int = 300,
    task_summary: Optional[str] = None,
    working_dir: Optional[str] = None,
) -> AgentResult:
    """
    Spawn a GitHub Copilot CLI agent.
    
    Context Handling:
        Copilot CLI automatically loads AGENTS.md from the project root.
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("copilot", model)
    
    spawn_id = log_spawn_start(
        agent="Copilot",
        model=resolved_model,
        prompt=prompt,
        tools=["all"],
        task_summary=task_summary,
        agent_type="CLI"
    )
    
    # Copilot CLI argument construction
    # NOTE: We pass prompt via stdin instead of -p flag to avoid Windows command line length limits
    cmd = [
        "copilot",
        "-s",                   # Silent (output only response)
        "--allow-all-tools",    # Auto-approve all tools
        "--allow-all-paths",    # Allow access to any path
        # Variadic arg requirement: both tools passed to one flag
        "--allow-tool", "shell", "write",
        "--model", resolved_model,
    ]

    cwd = working_dir or str(get_workspace_dir())

    try:
        # Prompt via stdin (avoids Windows command line length limits). Hardened
        # run: output to temp files, process-tree kill on timeout. See proc.py.
        returncode, output_text, error_text, timed_out = run_captured(
            cmd, cwd=cwd, timeout=timeout, stdin_text=prompt,
        )

        duration = time.time() - start_time

        if timed_out:
            error_text = (error_text + f"\n[powerspawn] copilot timed out after "
                          f"{timeout}s; process tree killed").strip()

        success = (not timed_out) and returncode == 0 and output_text != ""

        # If failure with no output, use stderr
        if not success and not output_text:
            error_msg = error_text or f"Exit code {returncode}"
            log_spawn_complete(spawn_id, False, "", duration, 0.0, error_msg)
            return AgentResult(success=False, text="", spawn_id=spawn_id, error=error_msg, provider="copilot")
            
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
            provider="copilot"
        )
        
    except Exception as e:
        duration = time.time() - start_time
        log_spawn_complete(spawn_id, False, "", duration, 0.0, str(e))
        return AgentResult(success=False, text="", spawn_id=spawn_id, error=str(e), provider="copilot")
