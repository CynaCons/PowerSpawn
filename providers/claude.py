"""
Claude CLI Provider
"""

import json
import subprocess
import time
import sys
from pathlib import Path
from typing import Optional

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from ..proc import run_captured
from ..context import inject_agents_context
from .types import AgentResult

IS_WINDOWS = sys.platform == "win32"

def get_workspace_dir() -> Path:
    """Get the workspace root directory (parent of powerspawn/)."""
    return Path(__file__).parent.parent.parent

def _parse_claude_response(response_text: str) -> AgentResult:
    """Parse JSON output from Claude CLI."""
    try:
        data = json.loads(response_text)
        return AgentResult(
            success=data.get("type") == "result" and data.get("subtype") == "success",
            text=data.get("result", ""),
            structured_output=data.get("structured_output"),
            session_id=data.get("session_id"),
            duration_ms=data.get("duration_ms", 0),
            cost_usd=data.get("total_cost_usd", 0.0),
            usage=data.get("usage", {}),
            error=None if data.get("subtype") == "success" else data.get("result"),
            raw_response=data,
            provider="claude"
        )
    except json.JSONDecodeError as e:
        return AgentResult(
            success=False,
            text="",
            error=f"Failed to parse JSON response: {e}",
            provider="claude"
        )

def spawn_claude(
    prompt: str,
    *,
    model: str = None,
    tools: Optional[list[str]] = None,
    timeout: int = 300,
    task_summary: Optional[str] = None,
    dangerously_skip_permissions: bool = True,
    working_dir: Optional[str] = None,
) -> AgentResult:
    """
    Spawn a Claude CLI agent.
    
    Context Handling:
        Claude CLI automatically loads CLAUDE.md from the project root.
    """
    start_time = time.time()
    
    # Resolve model
    resolved_model = settings.get_model_alias("claude", model)
    
    # Log start
    spawn_id = log_spawn_start(
        agent="Claude",
        model=resolved_model,
        prompt=prompt,
        tools=tools or [],
        task_summary=task_summary,
        agent_type="CLI"
    )
    
    # Build command
    cmd = ["claude", "-p", "--output-format", "json"]
    cmd.extend(["--model", resolved_model])
    
    if tools:
        cmd.extend(["--tools", ",".join(tools)])
        
    if dangerously_skip_permissions:
        cmd.append("--dangerously-skip-permissions")

    cwd = working_dir or str(get_workspace_dir())
    # AGENTS.md is the shared worker briefing; Claude's CLI only auto-loads
    # CLAUDE.md (coordinator instruction), so inject AGENTS.md explicitly.
    prompt = inject_agents_context(prompt, working_dir, provider="claude")

    try:
        # Hardened run: prompt via stdin, output to temp files (no pipe-EOF
        # drain hang), process-tree kill on timeout. See powerspawn/proc.py.
        returncode, stdout_text, stderr_text, timed_out = run_captured(
            cmd, cwd=cwd, timeout=timeout, stdin_text=prompt,
        )

        duration = time.time() - start_time

        if timed_out or (returncode != 0 and not stdout_text):
            error_msg = (f"Timed out after {timeout}s; process tree killed"
                         if timed_out else (stderr_text or f"Exit code {returncode}"))
            log_spawn_complete(
                spawn_id=spawn_id,
                success=False,
                result_text="",
                duration_seconds=duration,
                error=error_msg
            )
            return AgentResult(success=False, text="", spawn_id=spawn_id, error=error_msg, provider="claude")

        agent_result = _parse_claude_response(stdout_text)
        agent_result.spawn_id = spawn_id
        agent_result.model = resolved_model
        
        log_spawn_complete(
            spawn_id=spawn_id,
            success=agent_result.success,
            result_text=agent_result.text,
            duration_seconds=duration,
            cost_usd=agent_result.cost_usd,
            error=agent_result.error
        )
        
        return agent_result
        
    except Exception as e:
        duration = time.time() - start_time
        log_spawn_complete(
            spawn_id=spawn_id,
            success=False,
            result_text="",
            duration_seconds=duration,
            error=str(e)
        )
        return AgentResult(success=False, text="", spawn_id=spawn_id, error=str(e), provider="claude")
