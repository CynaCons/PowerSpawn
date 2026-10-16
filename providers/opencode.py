"""
OpenCode CLI Provider

Runs `opencode run` headless (private server per spawn, permissions
auto-approved) with any OpenCode model, including the free `opencode/*-free`
ones (DeepSeek, GLM, ...).

Every spawn reports to the PowerScroll board the owner has open (see
powerscroll.py): PowerSpawn creates and closes the agent's card itself, and
the agent gets the powerscroll MCP server, under its own name, to add
checklist steps, ticks and notes while it works.

Context Handling:
    OpenCode loads AGENTS.md from the project root.
"""

import json
import os
import secrets
import time
from typing import Optional

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from ..proc import run_captured
from ..paths import get_workspace_dir
from .types import AgentResult
from . import powerscroll

# Free endpoints drop connections or go briefly unavailable under load; such a
# run produces no text.
TRANSIENT_ERRORS = ("socket connection was closed", "Transport:", "ECONNRESET",
                    "rate limit", "overloaded", "503", "502",
                    "Endpoint is unavailable", "Upstream request failed")
MAX_ATTEMPTS = 3


def _parse_events(stdout: str) -> tuple[list[str], list[str]]:
    """`--format json` prints one event per line: collect the text parts and the errors."""
    texts, errors = [], []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "text":
            text = (event.get("part") or {}).get("text", "")
            if text.strip():
                texts.append(text.strip())
        elif event.get("type") == "error":
            err = event.get("error") or {}
            errors.append(str(err.get("message") or err))
    return texts, errors


def _mcp_config(name: str) -> str:
    """OpenCode config that gives the agent the powerscroll MCP server under its own name."""
    base = {}
    if os.environ.get("OPENCODE_CONFIG_CONTENT"):
        try:
            base = json.loads(os.environ["OPENCODE_CONFIG_CONTENT"])
        except ValueError:
            base = {}
    base.setdefault("mcp", {})["powerscroll"] = {
        "type": "local",
        "command": powerscroll.server_command(),
        "environment": {"POWERNOTE_AGENT_NAME": name},
        "enabled": True,
    }
    return json.dumps(base)


def spawn_opencode(
    prompt: str,
    *,
    model: str = None,
    timeout: int = 900,
    agent_name: Optional[str] = None,
    board: Optional[str] = None,
    task_summary: Optional[str] = None,
    working_dir: Optional[str] = None,
) -> AgentResult:
    """
    Spawn an OpenCode CLI agent that reports to the PowerScroll board.

    Args:
        prompt: The task.
        model: Alias from models.json ("deepseek", "glm", ...) or any provider/model id.
        timeout: Seconds before the process tree is killed.
        agent_name: Name on the board (default: oc-<model>-<4 hex>).
        board: Board id or title (default: POWERSCROLL_BOARD, else the first board).
        task_summary: Card title (default: first line of the prompt).
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("opencode", model)
    short = resolved_model.split("/")[-1].replace("-free", "").split("-")[0]
    name = powerscroll.agent_name(agent_name or f"oc-{short}-{secrets.token_hex(2)}")
    title = (task_summary or next((l.strip("# ").strip() for l in prompt.splitlines() if l.strip()), "task"))[:120]

    spawn_id = log_spawn_start(
        agent="OpenCode",
        model=resolved_model,
        prompt=prompt,
        tools=["all"],
        task_summary=task_summary or title,
        agent_type="CLI",
    )

    card, board_warning = powerscroll.start_card(
        name, title, prompt[:1500], ["opencode", short], board=board,
    )
    env = {**os.environ, "POWERNOTE_AGENT_NAME": name}
    full_prompt = prompt
    if card:
        env["OPENCODE_CONFIG_CONTENT"] = _mcp_config(name)
        full_prompt = powerscroll.agent_brief(card) + prompt

    cmd = ["opencode", "run", "--standalone", "--auto", "--format", "json", "-m", resolved_model]
    cwd = working_dir or str(get_workspace_dir())
    env["PWD"] = cwd  # opencode takes its project dir from PWD when set (Git Bash, POSIX shells)

    texts, errors, error_text, returncode, timed_out = [], [], "", -1, False
    for attempt in range(1, MAX_ATTEMPTS + 1):
        remaining = max(30, int(timeout - (time.time() - start_time)))
        returncode, stdout, error_text, timed_out = run_captured(
            cmd, cwd=cwd, timeout=remaining, stdin_text=full_prompt, env=env,
        )
        texts, errors = _parse_events(stdout)
        transient = not texts and any(t.lower() in e.lower() for e in errors for t in TRANSIENT_ERRORS)
        if timed_out or not transient or attempt == MAX_ATTEMPTS:
            break
        time.sleep(5 * attempt)

    duration = time.time() - start_time
    text = "\n\n".join(texts)  # the whole run, for the coordinator
    final_answer = texts[-1] if texts else ""  # the card gets only the final reply
    success =(not timed_out) and returncode == 0 and bool(text) and not (errors and not text)
    error = None
    if not success:
        parts = errors + ([error_text[-1500:]] if error_text else [])
        if timed_out:
            parts.append(f"[powerspawn] opencode timed out after {timeout}s; process tree killed")
        error = "\n".join(parts) or f"Exit code {returncode}"

    if card:
        warn = powerscroll.finish_card(card, success, final_answer if success else (error or text), duration)
        board_warning = warn or board_warning
    if board_warning:
        text = f"{text}\n\n[powerspawn] {board_warning}".strip()

    log_spawn_complete(spawn_id, success, text, duration, 0.0, error)
    return AgentResult(
        success=success,
        text=text,
        spawn_id=spawn_id,
        duration_ms=int(duration * 1000),
        error=error,
        model=resolved_model,
        provider="opencode",
        usage={"agent_name": name, "board_card": card.ref if card else None,
               "board": card.board_title if card else None},
    )
