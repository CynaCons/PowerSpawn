"""
Grok CLI Provider (Grok Build)

Drives the Grok CLI (`grok`) in headless single-turn mode. This is the primary
way to spawn Grok; the legacy x.ai chat-completions path lives in grok_api.py
(spawn_grok_api) as a fallback.

Auth is `grok login` (grok.com account), handled by the CLI itself — no key
handling here, same as the Cursor and Gemini CLI providers.

Models (from `grok models`): grok-4.6 (default), grok-4.7, grok-4.5.
Legacy aliases (build, composer, …) resolve to the default so older callers keep working.

The prompt is always passed via --prompt-file (a temp file) rather than as a
command-line argument, so long spec prompts do not hit the Windows ~8 KB
command-line length limit that bit the Cursor provider.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from ..logger import log_spawn_start, log_spawn_complete
from ..config import DEFAULT_SPAWN_TIMEOUT, settings
from ..proc import run_captured
from ..context import inject_agents_context
from .types import AgentResult

IS_WINDOWS = sys.platform == "win32"

# The Grok CLI binary. Normally `grok` (the installer puts ~/.grok/bin on
# PATH). Honor GROK_BIN so a machine without it on PATH can point at the exe.
GROK_BIN = os.environ.get("GROK_BIN", "grok")


from ..paths import get_workspace_dir

# stopReason values that mean the turn finished normally.
_OK_STOP_REASONS = {None, "end_turn", "stop_sequence"}


def _parse_grok_json(stdout: str) -> Optional[dict]:
    """The object `grok --output-format json` prints, or None if stdout isn't one.

    The CLI prints one JSON object after the turn: {"text", "stopReason", "sessionId",
    "usage", "total_cost_usd", ...} on success, {"type": "error", "message"} on failure.
    Some builds may log a line before it, so the last line that parses as an object wins.
    """
    text = (stdout or "").strip()
    if not text:
        return None
    candidates = [text] + [line for line in reversed(text.splitlines()) if line.strip().startswith("{")]
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _judge(returncode: int, stdout: str, timed_out: bool) -> dict:
    """Success, text, error, cost, usage and session from one grok run."""
    data = _parse_grok_json(stdout)
    if data is None:
        # Not JSON (an older CLI, or a crash before output): fall back to the
        # plain-text rule PowerSpawn used before.
        ok = (not timed_out) and returncode == 0 and bool(stdout)
        return {"success": ok, "text": stdout, "error": None, "cost": 0.0, "usage": {}, "session": None}
    if data.get("type") == "error":
        return {"success": False, "text": "", "error": str(data.get("message") or "grok reported an error"),
                "cost": 0.0, "usage": {}, "session": None}
    text = str(data.get("text") or "").strip()
    stop = data.get("stopReason")
    error = None
    if timed_out:
        error = None  # the caller appends the timeout notice
    elif returncode != 0:
        error = f"grok exited with code {returncode}"
    elif stop not in _OK_STOP_REASONS:
        error = f"grok stopped early: stopReason={stop}"
    elif not text:
        error = "grok returned no text"
    ok = (not timed_out) and error is None
    return {
        "success": ok, "text": text, "error": error,
        "cost": float(data.get("total_cost_usd") or 0.0),
        "usage": data.get("usage") or {},
        "session": data.get("sessionId"),
    }


def spawn_grok(
    prompt: str,
    *,
    model: str = None,
    timeout: int = DEFAULT_SPAWN_TIMEOUT,
    task_summary: Optional[str] = None,
    working_dir: Optional[str] = None,
    force: bool = True,
    system_prompt: Optional[str] = None,
) -> AgentResult:
    """
    Spawn a Grok CLI agent (headless single-turn).

    Assumes `grok` is on PATH and logged in (`grok login`). With `force` (the
    default) every tool execution is auto-approved (--always-approve) and edits
    land on disk; with force=False the agent runs in plan mode and only proposes.

    Success is read from the CLI's JSON result (--output-format json): exit 0, no
    {"type": "error"} object, a normal stopReason and non-empty text.

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
    worker_prompt = inject_agents_context(prompt, working_dir, provider="grok")

    prompt_file = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", prefix="powerspawn-grok-", delete=False, encoding="utf-8"
        ) as f:
            f.write(worker_prompt)
            prompt_file = f.name

        # grok --prompt-file <path> --model <m> --output-format json
        #      [--always-approve | --permission-mode plan] [--rules <extra>]
        cmd = [
            GROK_BIN,
            "--prompt-file", prompt_file,
            "--model", resolved_model,
            "--output-format", "json",
        ]

        if force:
            cmd.append("--always-approve")
        else:
            cmd.extend(["--permission-mode", "plan"])

        if system_prompt:
            cmd.extend(["--rules", system_prompt])

        # Hardened run: output to temp files (no pipe-EOF drain hang), stdin
        # DEVNULL, process-tree kill on timeout. See powerspawn/proc.py.
        returncode, output_text, error_text, timed_out = run_captured(
            cmd, cwd=cwd, timeout=timeout,
        )
        duration = time.time() - start_time

        verdict = _judge(returncode, output_text, timed_out)
        problems = [p for p in (verdict["error"], error_text[-1500:] if not verdict["success"] else "") if p]
        if timed_out:
            problems.append(f"[powerspawn] grok timed out after {timeout}s; process tree killed")
        success = verdict["success"]
        error_msg = None if success else ("\n".join(problems) or f"Exit code {returncode}")
        text = verdict["text"]

        log_spawn_complete(
            spawn_id=spawn_id,
            success=success,
            result_text=text,
            duration_seconds=duration,
            cost_usd=verdict["cost"],
            error=error_msg,
        )

        return AgentResult(
            success=success,
            text=text,
            spawn_id=spawn_id,
            session_id=verdict["session"],
            duration_ms=int(duration * 1000),
            cost_usd=verdict["cost"],
            usage=verdict["usage"],
            error=error_msg,
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
