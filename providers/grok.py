"""
Grok CLI Provider (Grok Build)

Drives the Grok CLI (`grok`) in headless single-turn mode. This is the primary
way to spawn Grok; the legacy x.ai chat-completions path lives in grok_api.py
(spawn_grok_api) as a fallback.

Auth is `grok login` (grok.com account), handled by the CLI itself — no key
handling here, same as the Cursor and Gemini CLI providers.

Models (from `grok models`): grok-build (default), grok-composer-2.5-fast.

The prompt is always passed via --prompt-file (a temp file) rather than as a
command-line argument, so long spec prompts do not hit the Windows ~8 KB
command-line length limit that bit the Cursor provider.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from .types import AgentResult

IS_WINDOWS = sys.platform == "win32"

# The Grok CLI binary. Normally `grok` (the installer puts ~/.grok/bin on
# PATH). Honor GROK_BIN so a machine without it on PATH can point at the exe.
GROK_BIN = os.environ.get("GROK_BIN", "grok")

def get_workspace_dir() -> Path:
    return Path(__file__).parent.parent.parent

def spawn_grok(
    prompt: str,
    *,
    model: str = None,
    timeout: int = 600,
    task_summary: Optional[str] = None,
    working_dir: Optional[str] = None,
    force: bool = False,
    system_prompt: Optional[str] = None,
) -> AgentResult:
    """
    Spawn a Grok CLI agent (headless single-turn).

    Assumes `grok` is on PATH and logged in (`grok login`). Without `force`
    the agent runs in plan mode (proposes changes, no writes); with `force`
    every tool execution is auto-approved and edits land on disk — same
    semantics as the Cursor provider's force flag.

    `system_prompt` is appended to the agent's system prompt via --rules
    (not an override), so Grok Build's own agentic scaffolding stays intact.
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("grok", model)

    tools_list = ["all"]
    if force:
        tools_list.append("force")

    spawn_id = log_spawn_start(
        agent="Grok",
        model=resolved_model,
        prompt=prompt,
        tools=tools_list,
        task_summary=task_summary,
        agent_type="CLI"
    )

    cwd = working_dir or str(get_workspace_dir())

    prompt_file = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", prefix="powerspawn-grok-", delete=False, encoding="utf-8"
        ) as f:
            f.write(prompt)
            prompt_file = f.name

        # grok --prompt-file <path> --model <m> --output-format plain
        #      [--always-approve | --permission-mode plan] [--rules <extra>]
        cmd = [
            GROK_BIN,
            "--prompt-file", prompt_file,
            "--model", resolved_model,
            "--output-format", "plain",
        ]

        if force:
            cmd.append("--always-approve")
        else:
            cmd.extend(["--permission-mode", "plan"])

        if system_prompt:
            cmd.extend(["--rules", system_prompt])

        result = subprocess.run(
            cmd,
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

        if not success and not output_text:
            error_msg = error_text or f"Exit code {result.returncode}"
            log_spawn_complete(spawn_id, False, "", duration, 0.0, error_msg)
            return AgentResult(success=False, text="", spawn_id=spawn_id, error=error_msg, provider="grok")

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
            provider="grok"
        )

    except Exception as e:
        duration = time.time() - start_time
        log_spawn_complete(spawn_id, False, "", duration, 0.0, str(e))
        return AgentResult(success=False, text="", spawn_id=spawn_id, error=str(e), provider="grok")

    finally:
        if prompt_file:
            try:
                os.unlink(prompt_file)
            except OSError:
                pass
