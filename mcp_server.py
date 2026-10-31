#!/usr/bin/env python3
"""
MCP Agent Spawner Server v1.8.0

Exposes agent spawning as MCP tools for Claude Code.
Uses modular provider architecture and singleton state management.

Tools:
  spawn_claude, spawn_codex, spawn_copilot (CLI)
  spawn_cursor (CLI, Cursor credits: Gemini/Grok/Kimi/GPT/Claude models)
  spawn_grok, spawn_gemini, spawn_mistral (API)

Persistent Agents (v1.8.0):
  create_persistent_agent, send_to_agent, terminate_agent, list_persistent_agents

Management:
  list, result, wait_for_agents

Configuration:
  - api_keys.json (local file)
  - Environment variables
  - models.json (model aliases)

Changelog v1.8.0:
  - Added persistent agents with conversation memory
  - New tools: create_persistent_agent, send_to_agent, terminate_agent, list_persistent_agents
  - Claude CLI resume support via --resume flag
  - 1-hour idle timeout for persistent agents

Changelog v1.7.1:
  - spawn_claude now defaults dangerously_skip_permissions=True
  - Allows spawned agents to write files, search web, fetch URLs
  - Fixes permission issues from v1.7.0
"""

import asyncio
import json
import sys
import threading
from typing import Any

from .agent_manager import agent_manager
from .config import settings
from .persistent_agent import persistent_registry
from .providers import (
    spawn_claude,
    spawn_codex,
    spawn_copilot,
    spawn_cursor,
    spawn_grok,
    spawn_gemini,
    spawn_gemini_cli,
    spawn_mistral
)

# Ensure UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SERVER_VERSION = "1.8.0"

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    from mcp.server.models import InitializationOptions
    from mcp.server.lowlevel import NotificationOptions
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

server = Server("agents")

# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="spawn_claude",
            description="Spawn Claude CLI agent. Context: CLAUDE.md.",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("claude")},
                    "timeout": {"type": "integer", "default": 600},
                    "dangerously_skip_permissions": {
                        "type": "boolean",
                        "default": True,
                        "description": "Bypass permission checks (allows spawned agents to write files, search web, etc.)"
                    }
                }
            }
        ),
        Tool(
            name="spawn_codex",
            description="Spawn Codex CLI agent. Context: AGENTS.md.",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("codex")}
                }
            }
        ),
        Tool(
            name="spawn_copilot",
            description="Spawn GitHub Copilot CLI agent. Context: AGENTS.md.",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("copilot")}
                }
            }
        ),
        Tool(
            name="spawn_cursor",
            description="Spawn Cursor CLI agent (headless; reaches Gemini/Grok/Kimi/GPT/Claude via Cursor credits). Context: AGENTS.md.",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("cursor")},
                    "timeout": {"type": "integer", "default": 600},
                    "read_only": {
                        "type": "boolean",
                        "default": True,
                        "description": "Read-only Q&A (--mode ask). Set false to let the agent edit files and run commands."
                    },
                    "working_dir": {"type": "string", "description": "Workspace directory (default: repo root)."}
                }
            }
        ),
        Tool(
            name="spawn_gemini_cli",
            description="Spawn Gemini CLI agent (requires 'gemini' in PATH).",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("gemini-cli")},
                    "yolo": {"type": "boolean", "default": False, "description": "Auto-approve all actions (YOLO mode)."}
                }
            }
        ),
        Tool(
            name="spawn_grok",
            description="Spawn Grok agent via API. Needs XAI_API_KEY.",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("grok")},
                    "system_prompt": {"type": "string"}
                }
            }
        ),
        Tool(
            name="spawn_gemini",
            description="Spawn Gemini agent via API. Needs GEMINI_API_KEY.",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("gemini")},
                    "system_prompt": {"type": "string"}
                }
            }
        ),
        Tool(
            name="spawn_mistral",
            description="Spawn Mistral agent via API. Needs MISTRAL_API_KEY.",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("mistral")},
                    "system_prompt": {"type": "string"}
                }
            }
        ),
        Tool(
            name="list",
            description="List running agents.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="result",
            description="Get agent result.",
            inputSchema={
                "type": "object",
                "required": ["agent_id"],
                "properties": {"agent_id": {"type": "string"}}
            }
        ),
        Tool(
            name="wait_for_agents",
            description="Block until all agents complete.",
            inputSchema={
                "type": "object",
                "properties": {
                    "timeout": {"type": "integer", "default": 300}
                }
            }
        ),
        # =========================================================================
        # PERSISTENT AGENTS (v1.8.0)
        # =========================================================================
        Tool(
            name="create_persistent_agent",
            description="Create a persistent agent with conversation memory. Returns agent_id for use with send_to_agent.",
            inputSchema={
                "type": "object",
                "required": ["provider"],
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["claude", "copilot"],
                        "description": "Agent provider (claude or copilot support persistence via --resume)"
                    },
                    "role": {
                        "type": "string",
                        "description": "Human-readable role name (e.g., 'resume-reviewer', 'regulator')"
                    },
                    "personality": {
                        "type": "string",
                        "description": "System prompt defining agent behavior and expertise (Claude only)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use (provider-specific)"
                    }
                }
            }
        ),
        Tool(
            name="send_to_agent",
            description="Send a message to an existing persistent agent. Agent remembers previous conversation.",
            inputSchema={
                "type": "object",
                "required": ["agent_id", "prompt"],
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Persistent agent ID (from create_persistent_agent)"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Message to send to the agent"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 600,
                        "description": "Timeout in seconds"
                    }
                }
            }
        ),
        Tool(
            name="terminate_agent",
            description="Terminate a persistent agent and free resources.",
            inputSchema={
                "type": "object",
                "required": ["agent_id"],
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Persistent agent ID to terminate"
                    }
                }
            }
        ),
        Tool(
            name="list_persistent_agents",
            description="List all persistent agents with their status and conversation stats.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

# =============================================================================
# TOOL HANDLERS
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "spawn_claude":
            return await handle_spawn(arguments, "claude", spawn_claude)
        elif name == "spawn_codex":
            return await handle_spawn(arguments, "codex", spawn_codex)
        elif name == "spawn_copilot":
            return await handle_spawn(arguments, "copilot", spawn_copilot)
        elif name == "spawn_cursor":
            return await handle_spawn(arguments, "cursor", spawn_cursor)
        elif name == "spawn_gemini_cli":
            return await handle_spawn(arguments, "gemini_cli", spawn_gemini_cli)
        elif name == "spawn_grok":
            return await handle_spawn(arguments, "grok", spawn_grok)
        elif name == "spawn_gemini":
            return await handle_spawn(arguments, "gemini", spawn_gemini)
        elif name == "spawn_mistral":
            return await handle_spawn(arguments, "mistral", spawn_mistral)
        elif name == "list":
            return await handle_list()
        elif name == "result":
            return await handle_result(arguments)
        elif name == "wait_for_agents":
            return await handle_wait_for_agents(arguments)
        # Persistent agent tools (v1.8.0)
        elif name == "create_persistent_agent":
            return await handle_create_persistent_agent(arguments)
        elif name == "send_to_agent":
            return await handle_send_to_agent(arguments)
        elif name == "terminate_agent":
            return await handle_terminate_agent(arguments)
        elif name == "list_persistent_agents":
            return await handle_list_persistent_agents()
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }, indent=2))]

async def handle_spawn(args: dict, agent_type: str, spawn_func) -> list[TextContent]:
    """Generic handler for all spawn functions."""
    prompt = args["prompt"]
    model = args.get("model")
    
    # Register intent to start
    agent_id = agent_manager.register_start(agent_type, model or "default", prompt)
    
    def run_wrapper():
        try:
            # Call the specific provider function with passed args
            # Using **args to pass optional params like system_prompt, timeout etc.
            result = spawn_func(**args)
            
            # Register completion
            agent_manager.register_complete(agent_id, {
                "success": result.success,
                "result": result.text,
                "cost_usd": result.cost_usd,
                "error": result.error,
                "usage": result.usage
            })
        except Exception as e:
            agent_manager.register_complete(agent_id, {
                "success": False,
                "result": "",
                "error": str(e)
            })

    # Start background thread
    thread = threading.Thread(target=run_wrapper, daemon=True)
    agent_manager.register_thread(agent_id, thread)
    thread.start()

    return [TextContent(type="text", text=json.dumps({
        "agent_id": agent_id,
        "agent_type": agent_type,
        "status": "running",
        "message": f"{agent_type} agent spawned."
    }, indent=2))]

async def handle_list() -> list[TextContent]:
    running = agent_manager.get_running_list()
    recent = agent_manager.get_recent_completed_ids()
    return [TextContent(type="text", text=json.dumps({
        "running": running,
        "completed_ids": recent,
        "tip": "Use wait_for_agents() to block until done"
    }))]

async def handle_result(args: dict) -> list[TextContent]:
    agent_id = args["agent_id"]
    
    # Check completed
    res = agent_manager.get_result(agent_id)
    if res:
        return [TextContent(type="text", text=json.dumps(res, indent=2, ensure_ascii=False))]
        
    # Check running
    info = agent_manager.get_running_info(agent_id)
    if info:
        return [TextContent(type="text", text=json.dumps({
            "agent_id": agent_id,
            "status": "running",
            "message": "Agent still running."
        }, indent=2))]
        
    return [TextContent(type="text", text=json.dumps({
        "status": "not_found",
        "message": "No agent found with this ID."
    }))]

async def handle_wait_for_agents(args: dict) -> list[TextContent]:
    timeout = args.get("timeout", 300)
    # Blocking wait on threads/events
    result = await asyncio.to_thread(agent_manager.wait_for_all, timeout)
    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


# =============================================================================
# PERSISTENT AGENT HANDLERS (v1.8.0)
# =============================================================================

async def handle_create_persistent_agent(args: dict) -> list[TextContent]:
    """Create a new persistent agent."""
    provider = args["provider"]
    role = args.get("role")
    personality = args.get("personality")
    model = args.get("model")

    # Validate provider supports persistence
    supported_providers = ["claude", "copilot"]
    if provider not in supported_providers:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Provider '{provider}' does not support persistent agents. Use: {supported_providers}"
        }, indent=2))]

    # Note: Copilot doesn't support custom system prompts
    if provider == "copilot" and personality:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "Copilot does not support custom personality/system prompts. Use Claude for custom personalities."
        }, indent=2))]

    agent = persistent_registry.create(
        provider=provider,
        role=role,
        personality=personality,
        model=model,
    )

    return [TextContent(type="text", text=json.dumps({
        "success": True,
        "agent_id": agent.id,
        "provider": agent.provider,
        "role": agent.role,
        "model": agent.model,
        "message": f"Persistent agent created. Use send_to_agent(agent_id='{agent.id}', prompt='...') to interact."
    }, indent=2))]


async def handle_send_to_agent(args: dict) -> list[TextContent]:
    """Send a message to a persistent agent."""
    agent_id = args["agent_id"]
    prompt = args["prompt"]
    timeout = args.get("timeout", 600)

    # Get the agent
    agent = persistent_registry.get(agent_id)
    if not agent:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Agent '{agent_id}' not found."
        }, indent=2))]

    if agent.is_terminated():
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Agent '{agent_id}' has been terminated or expired."
        }, indent=2))]

    if agent.status == "busy":
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Agent '{agent_id}' is currently busy. Wait for it to complete."
        }, indent=2))]

    # Mark as busy
    persistent_registry.set_status(agent_id, "busy")

    # Run the agent call in a thread to not block
    def run_persistent_agent():
        try:
            # Dispatch based on provider
            if agent.provider == "claude":
                result = _run_claude_persistent(agent, prompt, timeout)
            elif agent.provider == "copilot":
                result = _run_copilot_persistent(agent, prompt, timeout)
            else:
                raise ValueError(f"Unsupported provider: {agent.provider}")

            # Store session_id for future resumes (if first call)
            if result.session_id and not agent.session_id:
                persistent_registry.update_session_id(agent_id, result.session_id)

            # Record conversation turn
            agent.add_turn("user", prompt)
            agent.add_turn("assistant", result.text)

            # Track cost
            if result.cost_usd:
                persistent_registry.add_cost(agent_id, result.cost_usd)

            return result

        finally:
            # Mark as idle when done
            persistent_registry.set_status(agent_id, "idle")

    # Execute synchronously for now (we want to return the result)
    result = await asyncio.to_thread(run_persistent_agent)

    return [TextContent(type="text", text=json.dumps({
        "success": result.success,
        "agent_id": agent_id,
        "role": agent.role,
        "turn_number": agent.total_turns,
        "session_id": agent.session_id,
        "result": result.text,
        "cost_usd": result.cost_usd,
        "total_cost_usd": agent.total_cost_usd,
        "error": result.error
    }, indent=2, ensure_ascii=False))]


def _run_claude_persistent(agent, prompt: str, timeout: int):
    """Run Claude persistent agent."""
    if agent.session_id:
        return spawn_claude(
            prompt=prompt,
            model=agent.model,
            timeout=timeout,
            resume_session_id=agent.session_id,
            system_prompt=None
        )
    else:
        return spawn_claude(
            prompt=prompt,
            model=agent.model,
            timeout=timeout,
            system_prompt=agent.personality
        )


def _run_copilot_persistent(agent, prompt: str, timeout: int):
    """Run Copilot persistent agent."""
    return spawn_copilot(
        prompt=prompt,
        model=agent.model,
        timeout=timeout,
        resume_session_id=agent.session_id  # None on first call
    )


async def handle_terminate_agent(args: dict) -> list[TextContent]:
    """Terminate a persistent agent."""
    agent_id = args["agent_id"]

    success = persistent_registry.terminate(agent_id)

    if success:
        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "agent_id": agent_id,
            "message": "Agent terminated."
        }, indent=2))]
    else:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Agent '{agent_id}' not found."
        }, indent=2))]


async def handle_list_persistent_agents() -> list[TextContent]:
    """List all persistent agents."""
    agents = persistent_registry.list_active()

    return [TextContent(type="text", text=json.dumps({
        "persistent_agents": agents,
        "count": len(agents),
        "tip": "Use send_to_agent(agent_id, prompt) to interact with an agent"
    }, indent=2))]


# =============================================================================
# MAIN
# =============================================================================

async def main():
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
