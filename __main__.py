#!/usr/bin/env python3
"""
PowerSpawn CLI Entry Point

Allows running the MCP server via: python -m powerspawn

Usage:
    python -m powerspawn          # Start MCP server (stdio)
    python -m powerspawn --help   # Show help
    python -m powerspawn --version  # Show version
"""

import sys
import asyncio

from __init__ import __version__


def print_help():
    """Print CLI help message."""
    print(f"""PowerSpawn v{__version__} - Universal Multi-Agent MCP Server

Usage:
    python -m powerspawn [OPTIONS]

Options:
    --help, -h      Show this help message
    --version, -v   Show version number

Description:
    Starts the PowerSpawn MCP server using stdio transport.
    This server exposes tools for spawning Claude and Codex sub-agents.

Available MCP Tools:
    spawn_claude    Spawn a Claude sub-agent (haiku/sonnet/opus)
    spawn_codex     Spawn a Codex (GPT-5.1) sub-agent
    list            List running/completed agents
    result          Get agent result by ID
    wait_for_agents Block until all agents complete

Configuration:
    POWERSPAWN_OUTPUT_DIR   Directory for IAC.md/CONTEXT.md (default: script dir)
    ANTHROPIC_API_KEY       Required for Claude agents
    OPENAI_API_KEY          Required for Codex agents

Example MCP Configuration (.mcp.json):
    {{
      "mcpServers": {{
        "agents": {{
          "command": "python",
          "args": ["-m", "powerspawn"]
        }}
      }}
    }}

Learn more: https://github.com/CynaCons/PowerSpawn
""")


def main():
    """Main CLI entry point."""
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print_help()
        sys.exit(0)

    if "--version" in args or "-v" in args:
        print(f"PowerSpawn v{__version__}")
        sys.exit(0)

    # Import and run the MCP server
    from mcp_server import main as server_main
    asyncio.run(server_main())


if __name__ == "__main__":
    main()
