#!/usr/bin/env python3
"""
MCP Agent Spawner Server v1.5

Exposes agent spawning as MCP tools for Claude Code.
Simplified design with minimal parameters.

Tools (CLI-based):
  spawn_claude(prompt, model?)  - Spawn Claude sub-agent (auto-loads CLAUDE.md)
  spawn_codex(prompt)           - Spawn Codex sub-agent (auto-loads AGENTS.md)
  spawn_copilot(prompt, model?) - Spawn Copilot sub-agent (GPT/Claude/Gemini)

Tools (API-based):
  spawn_grok(prompt, model?)    - Spawn Grok via X.ai API (requires XAI_API_KEY)
  spawn_gemini(prompt, model?)  - Spawn Gemini via Google API (requires GEMINI_API_KEY)
  spawn_mistral(prompt, model?) - Spawn Mistral via API (requires MISTRAL_API_KEY)

Management:
  list()                        - List running agents (compact output)
  result(agent_id)              - Get agent result
  wait_for_agents(timeout?)     - Block until all agents complete, return results

Context is auto-loaded by the respective CLIs:
  - Claude CLI: auto-loads CLAUDE.md
  - Codex CLI: auto-loads AGENTS.md

All logging to IAC.md is automatic via spawner.py/api_providers.py.

See MCP_DESIGN.md for architecture documentation.
"""

import asyncio
import json
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .spawner import (
        AgentResult,
        spawn_claude as _spawn_claude,
        spawn_codex as _spawn_codex,
        spawn_copilot as _spawn_copilot,
    )
    from .api_providers import (
        spawn_grok as _spawn_grok,
        spawn_gemini as _spawn_gemini,
        spawn_mistral as _spawn_mistral,
        get_available_api_providers,
        GROK_MODELS,
        GEMINI_MODELS,
        MISTRAL_MODELS,
    )
except ImportError:
    from spawner import (
        AgentResult,
        spawn_claude as _spawn_claude,
        spawn_codex as _spawn_codex,
        spawn_copilot as _spawn_copilot,
    )
    from api_providers import (
        spawn_grok as _spawn_grok,
        spawn_gemini as _spawn_gemini,
        spawn_mistral as _spawn_mistral,
        get_available_api_providers,
        GROK_MODELS,
        GEMINI_MODELS,
        MISTRAL_MODELS,
    )

# Ensure UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

IS_WINDOWS = sys.platform == "win32"

# Version (single source of truth)
SERVER_VERSION = "1.5.0"

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    from mcp.server.models import InitializationOptions
    from mcp.server.lowlevel import NotificationOptions
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Initialize MCP server
server = Server("agents")

# Track agents (protected by _agents_lock)
_agents_lock = threading.Lock()
running_agents: dict[str, dict] = {}
completed_agents: dict[str, dict] = {}
background_threads: dict[str, threading.Thread] = {}

# Limit completed_agents to prevent unbounded memory growth
MAX_COMPLETED_AGENTS = 100


def sanitize_for_json(text: str) -> str:
    """Sanitize text for JSON output."""
    if not text:
        return ""
    return text.encode('utf-8', errors='replace').decode('utf-8')


def utc_now_iso() -> str:
    """Get current local timestamp in ISO format (for dev tool convenience)."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _cleanup_completed_agents():
    """Remove oldest entries if over limit (must be called with _agents_lock held)."""
    if len(completed_agents) > MAX_COMPLETED_AGENTS:
        # Remove oldest entries (dict maintains insertion order in Python 3.7+)
        keys_to_remove = list(completed_agents.keys())[:-MAX_COMPLETED_AGENTS]
        for key in keys_to_remove:
            del completed_agents[key]
            background_threads.pop(key, None)  # Also clean up thread reference


def get_workspace_dir() -> Path:
    """Get workspace root directory (parent of powerspawn/)."""
    return Path(__file__).parent.parent


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Advertise available tools."""
    return [
        Tool(
            name="spawn_claude",
            description=(
                "Spawn a Claude sub-agent to perform a task. "
                "Use for: analysis, reasoning, code review, complex tasks. "
                "Context from CLAUDE.md is auto-loaded by Claude CLI."
            ),
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task for the sub-agent to perform"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["haiku", "sonnet", "opus"],
                        "default": "sonnet",
                        "description": "Model: haiku (fast/cheap), sonnet (balanced), opus (best)"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 600,
                        "description": "Timeout in seconds (default 600 = 10 min). Use 300 for simple tasks, 900 for complex features."
                    }
                }
            }
        ),
        Tool(
            name="spawn_codex",
            description=(
                "Spawn a Codex (GPT-5.1) sub-agent to perform a task. "
                "Use for: any task, especially when Claude rate limit is reached. "
                "Context from AGENTS.md is auto-loaded by Codex CLI."
            ),
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task for the sub-agent to perform"
                    }
                }
            }
        ),
        Tool(
            name="spawn_copilot",
            description=(
                "Spawn a GitHub Copilot CLI sub-agent. Universal multi-model spawner "
                "supporting GPT, Claude, and Gemini models. "
                "Context from AGENTS.md is auto-loaded by Copilot CLI."
            ),
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task for the sub-agent to perform"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["gpt-5.1", "gpt-5", "gpt-5.1-codex", "gpt-5-mini",
                                 "claude-sonnet", "claude-haiku", "claude-opus", "gemini"],
                        "default": "gpt-5.1",
                        "description": "Model: gpt-5.1 (default), gpt-5, claude-sonnet/haiku/opus, gemini"
                    }
                }
            }
        ),
        Tool(
            name="spawn_grok",
            description=(
                "Spawn a Grok (X.ai) sub-agent via API. "
                "Use for: fast reasoning, real-time knowledge, alternative perspective. "
                "Requires XAI_API_KEY environment variable."
            ),
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task for the sub-agent to perform"
                    },
                    "model": {
                        "type": "string",
                        "enum": list(GROK_MODELS.keys()),
                        "default": "grok-4",
                        "description": "Model: grok-4 (default), grok-4.1, grok-code-fast"
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt for role/context"
                    }
                }
            }
        ),
        Tool(
            name="spawn_gemini",
            description=(
                "Spawn a Google Gemini sub-agent via API. "
                "Use for: multimodal tasks, long context, alternative perspective. "
                "Requires GEMINI_API_KEY environment variable."
            ),
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task for the sub-agent to perform"
                    },
                    "model": {
                        "type": "string",
                        "enum": list(GEMINI_MODELS.keys()),
                        "default": "gemini-3-pro",
                        "description": "Model: gemini-3-pro (default), gemini-2.5-pro, gemini-2.0-flash"
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt for role/context"
                    }
                }
            }
        ),
        Tool(
            name="spawn_mistral",
            description=(
                "Spawn a Mistral AI sub-agent via API. "
                "Use for: code generation, European AI alternative, efficiency. "
                "Requires MISTRAL_API_KEY environment variable."
            ),
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task for the sub-agent to perform"
                    },
                    "model": {
                        "type": "string",
                        "enum": list(MISTRAL_MODELS.keys()),
                        "default": "mistral-large",
                        "description": "Model: mistral-large (default), codestral, devstral, mixtral"
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt for role/context"
                    }
                }
            }
        ),
        Tool(
            name="list",
            description="List running and recently completed agents",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="result",
            description="Get the result of a completed agent",
            inputSchema={
                "type": "object",
                "required": ["agent_id"],
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent ID from spawn response"
                    }
                }
            }
        ),
        Tool(
            name="wait_for_agents",
            description=(
                "Block until all running agents complete, then return all results. "
                "Use this instead of polling list(). Saves context window."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "timeout": {
                        "type": "integer",
                        "default": 300,
                        "description": "Max seconds to wait (default 300 = 5 min)"
                    }
                }
            }
        )
    ]


# =============================================================================
# TOOL HANDLERS
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Route tool calls to handlers."""
    try:
        if name == "spawn_claude":
            return await handle_spawn_claude(arguments)
        elif name == "spawn_codex":
            return await handle_spawn_codex(arguments)
        elif name == "spawn_copilot":
            return await handle_spawn_copilot(arguments)
        elif name == "spawn_grok":
            return await handle_spawn_grok(arguments)
        elif name == "spawn_gemini":
            return await handle_spawn_gemini(arguments)
        elif name == "spawn_mistral":
            return await handle_spawn_mistral(arguments)
        elif name == "list":
            return await handle_list()
        elif name == "result":
            return await handle_result(arguments)
        elif name == "wait_for_agents":
            return await handle_wait_for_agents(arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }, indent=2))]


def _run_claude_background(agent_id: str, prompt: str, model: str, timeout: int = 600):
    """Run Claude spawn in background thread."""
    try:
        # Pass task directly - Claude CLI auto-loads CLAUDE.md
        # No extra context injection needed
        result: AgentResult = _spawn_claude(
            prompt=prompt,
            model=model,
            tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
            timeout=timeout,
            context_level="none",  # Claude CLI auto-loads CLAUDE.md
            task_summary=prompt[:50] + "..." if len(prompt) > 50 else prompt,
            dangerously_skip_permissions=True,  # Enable write access (like Codex bypass_sandbox)
        )

        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "claude",
                "model": model,
                "success": result.success,
                "result": sanitize_for_json(result.text),
                "cost_usd": round(result.cost_usd, 4),
                "completed_at": utc_now_iso(),
                "error": result.error,
            }
            _cleanup_completed_agents()

    except Exception as e:
        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "claude",
                "model": model,
                "success": False,
                "result": "",
                "cost_usd": 0,
                "completed_at": utc_now_iso(),
                "error": str(e),
            }
    finally:
        with _agents_lock:
            running_agents.pop(agent_id, None)
            background_threads.pop(agent_id, None)  # Clean up thread reference


async def handle_spawn_claude(args: dict) -> list[TextContent]:
    """Handle spawn_claude tool call."""
    prompt = args["prompt"]
    model = args.get("model", "sonnet")
    timeout = args.get("timeout", 600)  # Default 10 minutes

    agent_id = uuid.uuid4().hex[:8]
    started_at = utc_now_iso()

    # Track as running (logging is done by spawner.py)
    with _agents_lock:
        running_agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": "claude",
            "model": model,
            "started_at": started_at,
            "task": prompt[:100].replace('\n', ' '),  # Sanitize newlines for display
        }

    # Spawn in background (pass original prompt for correct task_summary logging)
    thread = threading.Thread(
        target=_run_claude_background,
        args=(agent_id, prompt, model, timeout),
        daemon=True,
    )
    thread.start()
    with _agents_lock:
        background_threads[agent_id] = thread

    return [TextContent(type="text", text=json.dumps({
        "agent_id": agent_id,
        "agent_type": "claude",
        "model": model,
        "status": "running",
        "message": "Agent spawned. Use 'list' to monitor, 'result' to get output.",
    }, indent=2, ensure_ascii=False))]


def _run_codex_background(agent_id: str, prompt: str):
    """Run Codex spawn in background thread."""
    try:
        # Pass task directly - Codex auto-loads AGENTS.md from project root
        # No extra context injection needed
        result: AgentResult = _spawn_codex(
            prompt=prompt,
            bypass_sandbox=True,  # Use --dangerously-bypass-approvals-and-sandbox for write access
            timeout=300,
            context_level="none",  # Codex auto-loads AGENTS.md
            task_summary=prompt[:50] + "..." if len(prompt) > 50 else prompt,
        )

        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "codex",
                "success": result.success,
                "result": sanitize_for_json(result.text),
                "cost_usd": 0.005 if result.success else 0,  # Estimate - Codex doesn't report cost
                "completed_at": utc_now_iso(),
                "error": result.error,
            }
            _cleanup_completed_agents()

    except Exception as e:
        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "codex",
                "success": False,
                "result": "",
                "cost_usd": 0,
                "completed_at": utc_now_iso(),
                "error": str(e),
            }
    finally:
        with _agents_lock:
            running_agents.pop(agent_id, None)
            background_threads.pop(agent_id, None)  # Clean up thread reference


async def handle_spawn_codex(args: dict) -> list[TextContent]:
    """Handle spawn_codex tool call."""
    prompt = args["prompt"]

    agent_id = uuid.uuid4().hex[:8]
    started_at = utc_now_iso()

    # Track as running (logging is done by spawner.py)
    with _agents_lock:
        running_agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": "codex",
            "started_at": started_at,
            "task": prompt[:100].replace('\n', ' '),  # Sanitize newlines for display
        }

    # Spawn in background (pass original prompt for correct task_summary logging)
    thread = threading.Thread(
        target=_run_codex_background,
        args=(agent_id, prompt),
        daemon=True,
    )
    thread.start()
    with _agents_lock:
        background_threads[agent_id] = thread

    return [TextContent(type="text", text=json.dumps({
        "agent_id": agent_id,
        "agent_type": "codex",
        "status": "running",
        "message": "Agent spawned. Use 'list' to monitor, 'result' to get output.",
    }, indent=2, ensure_ascii=False))]


def _run_copilot_background(agent_id: str, prompt: str, model: str):
    """Run Copilot spawn in background thread."""
    try:
        result: AgentResult = _spawn_copilot(
            prompt=prompt,
            model=model,
            timeout=300,
            task_summary=prompt[:50] + "..." if len(prompt) > 50 else prompt,
        )

        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "copilot",
                "model": model,
                "success": result.success,
                "result": sanitize_for_json(result.text),
                "cost_usd": 0,  # Copilot doesn't report cost
                "completed_at": utc_now_iso(),
                "error": result.error,
            }
            _cleanup_completed_agents()

    except Exception as e:
        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "copilot",
                "model": model,
                "success": False,
                "result": "",
                "cost_usd": 0,
                "completed_at": utc_now_iso(),
                "error": str(e),
            }
    finally:
        with _agents_lock:
            running_agents.pop(agent_id, None)
            background_threads.pop(agent_id, None)


async def handle_spawn_copilot(args: dict) -> list[TextContent]:
    """Handle spawn_copilot tool call."""
    prompt = args["prompt"]
    model = args.get("model", "gpt-5.1")

    agent_id = uuid.uuid4().hex[:8]
    started_at = utc_now_iso()

    # Track as running (logging is done by spawner.py)
    with _agents_lock:
        running_agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": "copilot",
            "model": model,
            "started_at": started_at,
            "task": prompt[:100].replace('\n', ' '),
        }

    # Spawn in background
    thread = threading.Thread(
        target=_run_copilot_background,
        args=(agent_id, prompt, model),
        daemon=True,
    )
    thread.start()
    with _agents_lock:
        background_threads[agent_id] = thread

    return [TextContent(type="text", text=json.dumps({
        "agent_id": agent_id,
        "agent_type": "copilot",
        "model": model,
        "status": "running",
        "message": "Copilot agent spawned. Use 'list' to monitor, 'result' to get output.",
    }, indent=2, ensure_ascii=False))]


# =============================================================================
# API-BASED PROVIDERS (Grok, Gemini, Mistral)
# =============================================================================

def _run_grok_background(agent_id: str, prompt: str, model: str, system_prompt: str | None):
    """Run Grok spawn in background thread."""
    try:
        result = _spawn_grok(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            task_summary=prompt[:50] + "..." if len(prompt) > 50 else prompt,
        )

        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "grok",
                "model": model,
                "success": result.success,
                "result": sanitize_for_json(result.text),
                "cost_usd": round(result.cost_usd, 4),
                "completed_at": utc_now_iso(),
                "error": result.error,
                "usage": result.usage,
            }
            _cleanup_completed_agents()

    except Exception as e:
        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "grok",
                "model": model,
                "success": False,
                "result": "",
                "cost_usd": 0,
                "completed_at": utc_now_iso(),
                "error": str(e),
            }
    finally:
        with _agents_lock:
            running_agents.pop(agent_id, None)
            background_threads.pop(agent_id, None)


async def handle_spawn_grok(args: dict) -> list[TextContent]:
    """Handle spawn_grok tool call."""
    prompt = args["prompt"]
    model = args.get("model", "grok-4")
    system_prompt = args.get("system_prompt")

    agent_id = uuid.uuid4().hex[:8]
    started_at = utc_now_iso()

    with _agents_lock:
        running_agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": "grok",
            "model": model,
            "started_at": started_at,
            "task": prompt[:100].replace('\n', ' '),
        }

    thread = threading.Thread(
        target=_run_grok_background,
        args=(agent_id, prompt, model, system_prompt),
        daemon=True,
    )
    thread.start()
    with _agents_lock:
        background_threads[agent_id] = thread

    return [TextContent(type="text", text=json.dumps({
        "agent_id": agent_id,
        "agent_type": "grok",
        "model": model,
        "status": "running",
        "message": "Grok agent spawned via X.ai API. Use 'list' to monitor, 'result' to get output.",
    }, indent=2, ensure_ascii=False))]


def _run_gemini_background(agent_id: str, prompt: str, model: str, system_prompt: str | None):
    """Run Gemini spawn in background thread."""
    try:
        result = _spawn_gemini(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            task_summary=prompt[:50] + "..." if len(prompt) > 50 else prompt,
        )

        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "gemini",
                "model": model,
                "success": result.success,
                "result": sanitize_for_json(result.text),
                "cost_usd": round(result.cost_usd, 4),
                "completed_at": utc_now_iso(),
                "error": result.error,
                "usage": result.usage,
            }
            _cleanup_completed_agents()

    except Exception as e:
        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "gemini",
                "model": model,
                "success": False,
                "result": "",
                "cost_usd": 0,
                "completed_at": utc_now_iso(),
                "error": str(e),
            }
    finally:
        with _agents_lock:
            running_agents.pop(agent_id, None)
            background_threads.pop(agent_id, None)


async def handle_spawn_gemini(args: dict) -> list[TextContent]:
    """Handle spawn_gemini tool call."""
    prompt = args["prompt"]
    model = args.get("model", "gemini-3-pro")
    system_prompt = args.get("system_prompt")

    agent_id = uuid.uuid4().hex[:8]
    started_at = utc_now_iso()

    with _agents_lock:
        running_agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": "gemini",
            "model": model,
            "started_at": started_at,
            "task": prompt[:100].replace('\n', ' '),
        }

    thread = threading.Thread(
        target=_run_gemini_background,
        args=(agent_id, prompt, model, system_prompt),
        daemon=True,
    )
    thread.start()
    with _agents_lock:
        background_threads[agent_id] = thread

    return [TextContent(type="text", text=json.dumps({
        "agent_id": agent_id,
        "agent_type": "gemini",
        "model": model,
        "status": "running",
        "message": "Gemini agent spawned via Google AI API. Use 'list' to monitor, 'result' to get output.",
    }, indent=2, ensure_ascii=False))]


def _run_mistral_background(agent_id: str, prompt: str, model: str, system_prompt: str | None):
    """Run Mistral spawn in background thread."""
    try:
        result = _spawn_mistral(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            task_summary=prompt[:50] + "..." if len(prompt) > 50 else prompt,
        )

        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "mistral",
                "model": model,
                "success": result.success,
                "result": sanitize_for_json(result.text),
                "cost_usd": round(result.cost_usd, 4),
                "completed_at": utc_now_iso(),
                "error": result.error,
                "usage": result.usage,
            }
            _cleanup_completed_agents()

    except Exception as e:
        with _agents_lock:
            completed_agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": "mistral",
                "model": model,
                "success": False,
                "result": "",
                "cost_usd": 0,
                "completed_at": utc_now_iso(),
                "error": str(e),
            }
    finally:
        with _agents_lock:
            running_agents.pop(agent_id, None)
            background_threads.pop(agent_id, None)


async def handle_spawn_mistral(args: dict) -> list[TextContent]:
    """Handle spawn_mistral tool call."""
    prompt = args["prompt"]
    model = args.get("model", "mistral-large")
    system_prompt = args.get("system_prompt")

    agent_id = uuid.uuid4().hex[:8]
    started_at = utc_now_iso()

    with _agents_lock:
        running_agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": "mistral",
            "model": model,
            "started_at": started_at,
            "task": prompt[:100].replace('\n', ' '),
        }

    thread = threading.Thread(
        target=_run_mistral_background,
        args=(agent_id, prompt, model, system_prompt),
        daemon=True,
    )
    thread.start()
    with _agents_lock:
        background_threads[agent_id] = thread

    return [TextContent(type="text", text=json.dumps({
        "agent_id": agent_id,
        "agent_type": "mistral",
        "model": model,
        "status": "running",
        "message": "Mistral agent spawned via Mistral AI API. Use 'list' to monitor, 'result' to get output.",
    }, indent=2, ensure_ascii=False))]


async def handle_list() -> list[TextContent]:
    """List running agents (compact output to save context window)."""
    now = datetime.now(timezone.utc)

    with _agents_lock:
        running = []
        for agent_id, info in list(running_agents.items()):
            elapsed = 0
            if "started_at" in info:
                try:
                    started = datetime.fromisoformat(info["started_at"].replace("Z", "+00:00"))
                    elapsed = int((now - started).total_seconds())
                except Exception:
                    pass
            # Compact: just ID and elapsed time
            running.append({"id": agent_id, "sec": elapsed})

        # Only last 3 completed IDs (not full details)
        recent_ids = list(completed_agents.keys())[-3:]

    # Minimal output
    return [TextContent(type="text", text=json.dumps({
        "running": running,
        "completed_ids": recent_ids,
        "tip": "Use wait_for_agents() to block until done and get all results"
    }))]


async def handle_result(args: dict) -> list[TextContent]:
    """Get result of a completed agent."""
    agent_id = args["agent_id"]

    with _agents_lock:
        if agent_id in completed_agents:
            return [TextContent(type="text", text=json.dumps(
                completed_agents[agent_id], indent=2, ensure_ascii=False
            ))]

        if agent_id in running_agents:
            info = running_agents[agent_id]
            elapsed = 0
            if "started_at" in info:
                try:
                    started = datetime.fromisoformat(info["started_at"].replace("Z", "+00:00"))
                    elapsed = int((datetime.now(timezone.utc) - started).total_seconds())
                except Exception:
                    pass

            return [TextContent(type="text", text=json.dumps({
                "agent_id": agent_id,
                "status": "running",
                "elapsed_seconds": elapsed,
                "message": "Agent still running. Check back later.",
            }, indent=2, ensure_ascii=False))]

    return [TextContent(type="text", text=json.dumps({
        "agent_id": agent_id,
        "status": "not_found",
        "message": "No agent found with this ID.",
    }, indent=2, ensure_ascii=False))]


async def handle_wait_for_agents(args: dict) -> list[TextContent]:
    """Block until all running agents complete, then return all results.

    This eliminates polling loops and saves context window by returning
    all results in a single response.
    """
    timeout = args.get("timeout", 300)  # Default 5 minutes
    poll_interval = 2  # Check every 2 seconds
    elapsed = 0

    # Track which agents we're waiting for at the start
    with _agents_lock:
        waiting_for = set(running_agents.keys())

    if not waiting_for:
        # No agents running - return any recent results
        with _agents_lock:
            recent = list(completed_agents.items())[-5:]
        return [TextContent(type="text", text=json.dumps({
            "status": "no_agents_running",
            "recent_results": [
                {"id": aid, "success": info.get("success"), "result": info.get("result", "")[:500]}
                for aid, info in recent
            ]
        }, indent=2, ensure_ascii=False))]

    # Wait for all agents to complete
    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        with _agents_lock:
            still_running = set(running_agents.keys()) & waiting_for
            if not still_running:
                # All done! Gather results
                results = []
                for agent_id in waiting_for:
                    if agent_id in completed_agents:
                        info = completed_agents[agent_id]
                        results.append({
                            "id": agent_id,
                            "type": info.get("agent_type"),
                            "success": info.get("success"),
                            "result": info.get("result", ""),
                            "error": info.get("error"),
                            "cost_usd": info.get("cost_usd", 0),
                        })

                return [TextContent(type="text", text=json.dumps({
                    "status": "all_completed",
                    "elapsed_seconds": elapsed,
                    "results": results
                }, indent=2, ensure_ascii=False))]

    # Timeout - return partial results
    with _agents_lock:
        still_running = list(set(running_agents.keys()) & waiting_for)
        completed_results = []
        for agent_id in waiting_for:
            if agent_id in completed_agents:
                info = completed_agents[agent_id]
                completed_results.append({
                    "id": agent_id,
                    "success": info.get("success"),
                    "result": info.get("result", "")[:500],  # Truncate on timeout
                })

    return [TextContent(type="text", text=json.dumps({
        "status": "timeout",
        "elapsed_seconds": elapsed,
        "still_running": still_running,
        "completed_results": completed_results
    }, indent=2, ensure_ascii=False))]


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="agents",
            server_version=SERVER_VERSION,
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
