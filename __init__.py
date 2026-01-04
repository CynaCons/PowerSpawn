"""
PowerSpawn - Multi-Agent Orchestration System v1.6

Two modes of agent spawning:

CLI AGENTS (Full Autonomy):
    spawn_claude   - Claude Code sub-agent (can edit files, run commands)
    spawn_codex    - Codex sub-agent (can edit files, run commands)
    spawn_copilot  - Copilot sub-agent (can edit files, run commands)

API AGENTS (Text Response Only):
    spawn_grok     - X.ai Grok (text analysis, research)
    spawn_gemini   - Google Gemini (long context, multimodal)
    spawn_mistral  - Mistral AI (European model, code tasks)

Key features:
- Automatic logging to IAC.md (Inter Agent Context)
- IAC.md contains Active Agents table + Interaction History
- CLI agents auto-load context (CLAUDE.md / AGENTS.md)
- API agents return text; coordinator applies changes

See DESIGN.md for architecture rationale.

Usage:
    from PowerSpawn import spawn_claude, spawn_grok, AgentResult

    # CLI Agent - can modify files directly
    result = spawn_claude("Refactor the auth module", model="sonnet")
    print(result.text)

    # API Agent - returns text response
    result = spawn_grok("Analyze this code for security issues")
    print(result.text)  # Coordinator applies suggestions
"""

from spawner import (
    spawn_claude,
    spawn_codex,
    spawn_codex_stream,
    spawn_copilot,
    AgentResult,
    CodexEvent,
    CODEX_MODELS,
    CODEX_DEFAULT_MODEL,
    COPILOT_MODELS,
    COPILOT_DEFAULT_MODEL,
)
from api_providers import (
    spawn_grok,
    spawn_gemini,
    spawn_mistral,
    get_available_api_providers,
    GROK_MODELS,
    GROK_DEFAULT_MODEL,
    GEMINI_MODELS,
    GEMINI_DEFAULT_MODEL,
    MISTRAL_MODELS,
    MISTRAL_DEFAULT_MODEL,
)
from parser import (
    parse_claude_response,
    parse_codex_jsonl,
)
from context_loader import (
    load_project_context,
    load_minimal_context,
    load_full_context,
    format_prompt_with_context,
)
from logger import (
    log_spawn_start,
    log_spawn_complete,
    get_logger,
)

__version__ = "1.6.2"
__all__ = [
    # CLI Agents (full file/command access)
    "spawn_claude",
    "spawn_codex",
    "spawn_codex_stream",
    "spawn_copilot",
    # CLI Agent model configs
    "CODEX_MODELS",
    "CODEX_DEFAULT_MODEL",
    "COPILOT_MODELS",
    "COPILOT_DEFAULT_MODEL",
    # API Agents (text response only)
    "spawn_grok",
    "spawn_gemini",
    "spawn_mistral",
    "get_available_api_providers",
    # API Agent model configs
    "GROK_MODELS",
    "GROK_DEFAULT_MODEL",
    "GEMINI_MODELS",
    "GEMINI_DEFAULT_MODEL",
    "MISTRAL_MODELS",
    "MISTRAL_DEFAULT_MODEL",
    # Results
    "AgentResult",
    "CodexEvent",
    # Parsing
    "parse_claude_response",
    "parse_codex_jsonl",
    # Context loading
    "load_project_context",
    "load_minimal_context",
    "load_full_context",
    "format_prompt_with_context",
    # Logging
    "log_spawn_start",
    "log_spawn_complete",
    "get_logger",
]
