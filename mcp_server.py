#!/usr/bin/env python3
"""
MCP Agent Spawner Server v1.7.0

Exposes agent spawning as MCP tools for Claude Code.
Uses modular provider architecture and singleton state management.

Tools:
  spawn_claude, spawn_codex, spawn_copilot (CLI)
  spawn_grok, spawn_gemini, spawn_mistral (API)
  
Management:
  list, result, wait_for_agents

Configuration:
  - api_keys.json (local file)
  - Environment variables
  - models.json (model aliases)
"""

import asyncio
import json
import sys
import threading
from typing import Any

from .agent_manager import agent_manager
from .config import settings
from .providers import (
    spawn_claude,
    spawn_codex,
    spawn_copilot,
    spawn_grok,
    spawn_gemini,
    spawn_gemini_cli,
    spawn_mistral
)

# Ensure UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SERVER_VERSION = "1.7.0"

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
                    "timeout": {"type": "integer", "default": 600}
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
