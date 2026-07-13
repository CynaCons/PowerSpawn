"""
Universal sub-agent context (AGENTS.md).

Re-implements the intent of PR #1 ("make AGENTS.md the universal context for all
sub-agents") against the current ``providers/`` package layout.

Rationale: every spawned worker should share the same focused, task-oriented
briefing regardless of which CLI backs it. Some CLIs already auto-load AGENTS.md
from the project root (Codex, Copilot); others load a different file or nothing
(Claude auto-loads CLAUDE.md, which is heavy *coordinator* instruction a worker
should ignore; Cursor/Gemini/Grok load their own or none). For the providers
that do NOT natively treat AGENTS.md as their briefing, we prepend its contents
to the prompt so the context is identical across the fleet.

Providers listed in ``NATIVELY_LOADS_AGENTS_MD`` are skipped to avoid injecting
the file twice.
"""

import os
from pathlib import Path
from typing import Optional

# Providers whose CLI already auto-loads AGENTS.md from the project root — do not
# inject it again for these (it would duplicate a potentially large file).
NATIVELY_LOADS_AGENTS_MD = frozenset({"codex", "copilot"})


def _workspace_root() -> Path:
    # powerspawn/context.py -> powerspawn/ -> workspace root
    return Path(__file__).resolve().parent.parent


def load_agents_context(working_dir: Optional[str] = None) -> str:
    """Return the raw contents of AGENTS.md, or '' if it is not found.

    Looks in ``working_dir`` first (the directory the worker will run in), then
    the powerspawn workspace root.
    """
    candidates = []
    if working_dir:
        candidates.append(Path(working_dir) / "AGENTS.md")
    candidates.append(_workspace_root() / "AGENTS.md")
    for path in candidates:
        try:
            if path.is_file():
                return path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
    return ""


def inject_agents_context(
    prompt: str,
    working_dir: Optional[str] = None,
    *,
    provider: Optional[str] = None,
) -> str:
    """Prepend the AGENTS.md briefing to ``prompt`` for workers that need it.

    No-op (returns ``prompt`` unchanged) when the provider natively auto-loads
    AGENTS.md, when AGENTS.md is absent, or when injection is disabled via the
    ``POWERSPAWN_NO_AGENTS_CONTEXT`` environment variable.
    """
    if os.environ.get("POWERSPAWN_NO_AGENTS_CONTEXT"):
        return prompt
    if provider and provider in NATIVELY_LOADS_AGENTS_MD:
        return prompt
    context = load_agents_context(working_dir)
    if not context:
        return prompt
    return (
        "# Primary briefing (AGENTS.md)\n\n"
        "The following is your shared operating context for this workspace. "
        "Treat it as your primary briefing. Ignore any coordinator-only or "
        "orchestrator instructions it does not directly assign to you as a worker.\n\n"
        f"{context}\n\n"
        "---\n\n"
        "# Your task\n\n"
        f"{prompt}"
    )
