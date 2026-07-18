"""
PowerSpawn - Multi-Agent Orchestration System v1.8.1

Two modes of agent spawning:

CLI AGENTS (Full Autonomy):
    spawn_claude   - Claude Code sub-agent (can edit files, run commands)
    spawn_codex    - Codex sub-agent (GPT-5.6 Sol/Terra/Luna)
    spawn_grok     - Grok Build CLI (default: Cursor Grok 4.5)
    spawn_cursor   - Cursor agent CLI
    spawn_copilot  - Copilot sub-agent (can edit files, run commands)

API AGENTS (Text Response Only):
    spawn_grok_api - X.ai Grok chat API fallback
    spawn_gemini   - Google Gemini (long context, multimodal)
    spawn_mistral  - Mistral AI (European model, code tasks)

Key features:
- Automatic logging to IAC.md (Inter Agent Context)
- IAC.md contains Active Agents table + Interaction History
- CLI agents auto-load context (CLAUDE.md / AGENTS.md)
- API agents return text; coordinator applies changes

See DESIGN.md for architecture rationale.
"""

from .providers import (
    spawn_claude,
    spawn_codex,
    spawn_copilot,
    spawn_grok,
    spawn_gemini,
    spawn_mistral,
    AgentResult
)
from .logger import (
    log_spawn_start,
    log_spawn_complete,
    get_logger,
)
from .config import settings

__version__ = "1.8.1"
__all__ = [
    # CLI Agents
    "spawn_claude",
    "spawn_codex",
    "spawn_copilot",
    # API Agents
    "spawn_grok",
    "spawn_gemini",
    "spawn_mistral",
    # Types
    "AgentResult",
    # Logging
    "log_spawn_start",
    "log_spawn_complete",
    "get_logger",
    # Configuration
    "settings",
]