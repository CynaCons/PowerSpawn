"""
Copilot CLI Provider
"""

import subprocess
import time
import sys
import re
import tempfile
from pathlib import Path
from typing import Optional

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from .types import AgentResult

IS_WINDOWS = sys.platform == "win32"

def get_workspace_dir() -> Path:
    return Path(__file__).parent.parent.parent


def _extract_session_id(share_file: Path) -> Optional[str]:
    """Extract session ID from Copilot share markdown file."""
    try:
        content = share_file.read_text(encoding='utf-8')
        # Format: > **Session ID:** `d6cd98d2-fea3-4ac0-b79a-3f2be203ede9`
        match = re.search(r'\*\*Session ID:\*\*\s*`([a-f0-9-]+)`', content)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def spawn_copilot(
    prompt: str,
    *,
    model: str = None,
    timeout: int = 300,
    task_summary: Optional[str] = None,
    working_dir: Optional[str] = None,
    resume_session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> AgentResult:
    """
    Spawn a GitHub Copilot CLI agent.

    Context Handling:
        Copilot CLI automatically loads AGENTS.md from the project root.

    Args:
        resume_session_id: If provided, resume an existing session.
        system_prompt: Not currently used (Copilot doesn't support custom system prompts).
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("copilot", model)

    spawn_id = log_spawn_start(
        agent="Copilot",
        model=resolved_model,
        prompt=prompt,
        tools=["all"],
        task_summary=task_summary or (f"Resume:{resume_session_id[:8]}" if resume_session_id else None),
        agent_type="CLI"
    )

    # Copilot CLI argument construction
    cmd = [
        "copilot",
        "-s",                   # Silent (output only response)
        "--allow-all-tools",    # Auto-approve all tools
        "--allow-all-paths",    # Allow access to any path
        "--allow-tool", "shell", "write",
        "--model", resolved_model,
    ]

    # For session management
    share_file = None
    session_id = None

    if resume_session_id:
        # Resume existing session
        cmd.extend(["--resume", resume_session_id])
        session_id = resume_session_id
    else:
        # New session: use --share to capture session ID
        share_file = Path(tempfile.gettempdir()) / f"copilot_session_{spawn_id}.md"
        cmd.extend(["--share", str(share_file)])

    cwd = working_dir or str(get_workspace_dir())

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            shell=IS_WINDOWS,
            encoding='utf-8',
            errors='replace',
        )

        duration = time.time() - start_time

        output_text = result.stdout.strip() if result.stdout else ""
        error_text = result.stderr.strip() if result.stderr else ""

        success = result.returncode == 0 and output_text != ""

        # Extract session ID from share file (new sessions only)
        if share_file and share_file.exists():
            session_id = _extract_session_id(share_file)
            # Clean up temp file
            try:
                share_file.unlink()
            except Exception:
                pass

        # If failure with no output, use stderr
        if not success and not output_text:
            error_msg = error_text or f"Exit code {result.returncode}"
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
            session_id=session_id,
            duration_ms=int(duration * 1000),
            error=error_text if not success else None,
            model=resolved_model,
            provider="copilot"
        )

    except Exception as e:
        duration = time.time() - start_time
        log_spawn_complete(spawn_id, False, "", duration, 0.0, str(e))
        return AgentResult(success=False, text="", spawn_id=spawn_id, error=str(e), provider="copilot")
