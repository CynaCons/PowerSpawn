#!/usr/bin/env python3
"""
MCP Agent Spawner Server v1.13.0

Exposes agent spawning as MCP tools for Claude Code.
Uses modular provider architecture and singleton state management.

Tools:
  spawn_claude, spawn_codex, spawn_copilot, spawn_opencode, spawn_grok, spawn_gemini_cli, spawn_cursor (CLI)
  spawn_grok_api, spawn_gemini, spawn_mistral (API)

Management:
  list, result, wait_for_agents

Configuration:
  - api_keys.json (local file)
  - Environment variables
  - models.json (model aliases)

Changelog v1.13.0:
  - CLI spawns (claude, codex, copilot, cursor, gemini_cli, opencode, grok) no
    longer have a kill timer by default (was 600 s for Claude and Grok, 900 s for
    the others, 300 s for Gemini CLI), which killed long coding tasks and workers
    waiting on PowerChannel.
  - Pass timeout=<seconds> to limit one spawn, or set POWERSPAWN_TIMEOUT to give
    every spawn without a timeout a limit; timeout=0 means no limit.
  - With no limit, a channel worker waits up to 12 h for one answer (was 600 s).
  - spawn_grok defaults to force=true (--always-approve): without it PowerSpawn ran
    Grok in plan mode, so workers only proposed changes. force=false keeps plan mode.
  - spawn_grok reads the CLI's JSON result (--output-format json): success needs
    exit 0, no {"type":"error"} object, stopReason end_turn and non-empty text;
    cost, usage and session id are now reported.
Changelog v1.12.1:
  - Codex workers on a channel get default_tools_approval_mode='approve' for the
    PowerChannel server: without it `codex exec` refused calls that needed
    approval (seen with bypass_sandbox=False).
  - Guide: coordinators can use PowerChannel 0.6's standby instead of waiting in read.
  - Publish workflow runs in the "pypi" environment.
Changelog v1.12.0:
  - PowerChannel integration (optional; `pip install "powerspawn[channel]"`).
    Every spawn_* takes `name` (unique agent name, default <cli>-<4 hex>), and
    the Claude, Codex, Copilot, Cursor, Gemini CLI and OpenCode spawns take
    `channel` (a feature channel, or "dedicated" for dm-<name>). With a channel
    the worker gets the PowerChannel MCP for that run only, a brief (read once,
    post results and questions, ask-and-wait limits), and PowerSpawn posts
    started / finished / failed / timed out as "powerspawn", mirrored into
    IAC.md. list and result show name and channel. Guide: docs/powerchannel.md.
  - spawn_cursor and spawn_gemini_cli pass the prompt on stdin (a multi-line
    prompt passed as an argument lost every flag after its first newline on
    Windows). spawn_gemini_cli exposes timeout and working_dir.
  - IAC.md: a failure whose error holds backslashes (Windows paths) no longer
    crashes the logger (re.sub "bad escape" error).
  - MCP server instructions describe spawning, results and channels.
Changelog v1.11.2:
  - Board cards no longer get skipped when PowerSpawn starts the board hub
    itself (standalone PowerBoard on 41778): "No PowerBoard/PowerScroll ... is
    connected" is retried for 15 s, longer than the app's 10 s redial backoff.
Changelog v1.11.1:
  - spawn_codex, spawn_copilot and spawn_cursor expose `timeout` (default now
    900 s, was an undocumented 300 s that killed real coding tasks) and
    `working_dir`; spawn_claude and spawn_grok expose `working_dir`. spawn_claude
    now really defaults to the 600 s its schema advertises.
Changelog v1.11.0:
  - Board reporting now targets PowerBoard (providers/powerboard.py). PowerBoard
    runs standalone (PowerBoard.html, served by powerboard-mcp on port 41778) or
    embedded in a PowerScroll notebook (powerscroll-mcp); both expose the same
    board tools, so only configuration changes.
  - New POWERBOARD_MCP_COMMAND / POWERBOARD_BOARD (legacy POWERSCROLL_* names
    still read; POWERBOARD_* wins). The agent's board MCP gets both
    POWERBOARD_AGENT_NAME and POWERNOTE_AGENT_NAME and is named `powerboard`.
Changelog v1.10.3:
  - spawn_opencode backs off 60 s, then 120 s, after "Rate limit exceeded" (was 5 s, 10 s).

Changelog v1.10.2:
  - spawn_opencode retries "Upstream request failed: Endpoint is unavailable".

Changelog v1.10.1:
  - spawn_opencode exposes working_dir (one git worktree per agent task).

Changelog v1.10.0:
  - spawn_opencode: OpenCode CLI headless (free DeepSeek V4.1 Flash / GLM 5.3
    Flash and any OpenCode model), retries dropped free-endpoint connections.
  - PowerBoard board reporting: each OpenCode agent gets a card on the owner's
    open board (created/closed by PowerSpawn) plus the powerboard MCP under its
    own name for live checklist ticks and notes.

Changelog v1.9.0:
  - Model refresh (Oct 2026): Claude Fable 5.1 / Opus 5.5 / Sonnet 5.5;
    Codex GPT-6 Astra / Sol / Luna (sol = gpt-6.1-sol; no model -> Codex's own default; retired gpt-5.4/5.3/5.2/5.1
    ids dropped); Copilot default claude-opus-5.5; Grok CLI default grok-4.6
    (+ grok-4.7); Grok API default grok-4.7 (+ grok-build-0.1); Gemini 3.8 Flash
    as gemini-flash; Mistral Large 4 / Medium 3.5 / Small 4 pinned ids.

Changelog v1.8.1:
  - Codex models: GPT-5.6 Sol / Terra / Luna (sol, terra, tera, luna aliases).
  - Grok CLI default: Cursor Grok 4.5; legacy build/composer aliases map to 4.5.
  - Unit tests: PowerSpawn import alias + model registry coverage; logger cap test.
  - powerspawn.com: MCP overview section + updated model examples.

Changelog v1.8.0:
  - spawn_grok now drives the Grok CLI (Grok Build) headless — the primary
    Grok path. Models: grok-4.5 (default / Cursor Grok 4.5); legacy build/composer
    aliases map to grok-4.5.
    Prompt goes via --prompt-file (no Windows 8KB CLI limit); force=true
    auto-approves tool executions (edits applied), otherwise plan mode.
  - Legacy x.ai chat-completions path preserved as spawn_grok_api.

Changelog v1.7.1:
  - spawn_claude now defaults dangerously_skip_permissions=True
  - Allows spawned agents to write files, search web, fetch URLs
  - Fixes permission issues from v1.7.0
"""

import asyncio
import inspect
import json
import sys
import threading
from typing import Any

from .agent_manager import agent_manager
from .config import DEFAULT_SPAWN_TIMEOUT, default_spawn_timeout, settings
from .providers import (
    spawn_claude,
    spawn_codex,
    spawn_copilot,
    spawn_grok,
    spawn_grok_api,
    spawn_gemini,
    spawn_gemini_cli,
    spawn_mistral,
    spawn_cursor,
    spawn_opencode,
)
from .providers.availability import verify_providers_availability
from .channel import ChannelError, make_worker, worker_scope

# Ensure UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SERVER_VERSION = "1.13.0"

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    from mcp.server.models import InitializationOptions
    from mcp.server.lowlevel import NotificationOptions
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

INSTRUCTIONS = """\
PowerSpawn spawns CLI coding agents (Claude, Codex, Copilot, Cursor, Gemini CLI, Grok, OpenCode)
and API agents (Grok API, Gemini, Mistral) as workers, and logs every spawn and result to IAC.md.

- spawn_* returns an agent_id at once; the worker runs in the background. Collect it with
  result(agent_id), list, or wait_for_agents. Check the work yourself: a worker's report is a claim.
- The prompt is the worker's whole context: paste the task, the files it may touch, how to check
  its work, and the report you want back.
- Every spawn gets a unique agent name (pass `name`, or get a generated one like codex-3f9a),
  shown in the spawn response, list, result and IAC.md.

Channels (optional; need PowerChannel in the Python that runs PowerSpawn:
  uvx --from "powerspawn[channel]" powerspawn, pipx inject powerspawn powerchannel, or
  <that python> -m pip install powerchannel; the spawn error names that Python)
- Without `channel` a worker joins no channel. channel="<name>" (e.g. "release") puts it on a
  shared feature channel; channel="dedicated" gives it its own channel, dm-<worker name>.
- With a channel, the worker gets the PowerChannel tools for that run and a short brief: read
  once, post results and questions there, start questions with "@coordinator:", wait for answers
  with read(wait_seconds=...). PowerSpawn posts started / finished / failed / timed out there as
  "powerspawn", and mirrors the worker's conversation into its IAC.md entry.
- To watch and answer, use your own PowerChannel tools under a name of your own (not
  "powerspawn"; call `channels` first and pick names, yours and the workers', not active there):
  read(me=<you>, channel=<channel>, wait_seconds=600), then
  post(me=<you>, channel=<channel>, message="@<worker name>: ..."). Use a shorter wait if your
  app stops tool calls sooner (Cursor: 50, Gemini CLI: 540; Codex needs tool_timeout_sec=43200).
  While a channel worker runs, wait with read, not wait_for_agents, or its questions go unanswered.
  In an interactive session with PowerChannel 0.6+, you can instead call standby(me, channel) and
  end your turn: the next message on the channel wakes you.
- Spawns have no time limit by default; pass timeout=<seconds> (or set POWERSPAWN_TIMEOUT) to
  have PowerSpawn kill a run after that long. A worker with no limit waits up to 12 h for one
  answer; with a timeout it waits about (timeout - 120) / 2 seconds, at least 60. The spawn
  response shows it as worker_waits_up_to_seconds. With several workers, answer within the
  smallest of their budgets.
- Channels work for spawn_claude, spawn_codex, spawn_copilot, spawn_cursor, spawn_gemini_cli
  and spawn_opencode. spawn_grok and the API agents return an error if given a channel.
- Full guide: https://github.com/CynaCons/powerspawn/blob/main/docs/powerchannel.md
"""

server = Server("powerspawn", instructions=INSTRUCTIONS)

# Spawn tools whose CLI can take the PowerChannel MCP server for one run.
CHANNEL_TOOLS = {"spawn_claude", "spawn_codex", "spawn_copilot", "spawn_cursor",
                 "spawn_gemini_cli", "spawn_opencode"}

NAME_SCHEMA = {
    "type": "string",
    "description": ("Unique agent name for this worker: its name on PowerChannel and in list, result and "
                    "IAC.md. 1-64 lowercase letters, digits, '.', '_' or '-', starting with a letter or digit; "
                    "'human' and 'powerspawn' are reserved; must differ from every running worker's name. "
                    "Default: generated as <cli>-<4 hex>, e.g. codex-3f9a."),
}
CHANNEL_SCHEMA = {
    "type": "string",
    "description": ("PowerChannel channel for this worker (needs PowerChannel installed). Omit it and the worker "
                    "joins no channel. A channel name such as 'release': the worker joins that shared feature "
                    "channel. 'dedicated': the worker gets a channel of its own, named dm-<name>. With a channel, "
                    "the worker gets the PowerChannel tools for this run and a brief with its name and channel, "
                    "and PowerSpawn posts started / finished / failed / timed out there as 'powerspawn'. Watch "
                    "and answer with your own PowerChannel read and post."),
}


def _with_channel_args(tools: list) -> list:
    """Add `name` to every spawn tool and `channel` to those whose CLI supports it."""
    for tool in tools:
        if not tool.name.startswith("spawn_"):
            continue
        props = tool.inputSchema.setdefault("properties", {})
        props["name"] = dict(NAME_SCHEMA)
        if tool.name in CHANNEL_TOOLS:
            props["channel"] = dict(CHANNEL_SCHEMA)
    return tools

# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

# The kill timer every CLI spawn takes (spawn_claude, spawn_codex, ...).
TIMEOUT_SCHEMA = {
    "type": "integer",
    "default": DEFAULT_SPAWN_TIMEOUT,
    "minimum": 0,
    "description": ("Seconds before PowerSpawn kills the worker's process tree. 0 = no limit. "
                    "Omitted: POWERSPAWN_TIMEOUT if set, else no limit."),
}

# Agent types whose `timeout` is the CLI kill timer (the API agents' timeout is an
# HTTP client timeout and keeps its own default).
CLI_AGENTS = frozenset({"claude", "codex", "copilot", "gemini_cli", "cursor", "opencode", "grok"})

@server.list_tools()
async def list_tools() -> list[Tool]:
    return _with_channel_args([
        Tool(
            name="spawn_claude",
            description="Spawn Claude CLI agent. Context: AGENTS.md (injected as the shared worker briefing) + CLAUDE.md (CLI auto-load).",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("claude")},
                    "timeout": TIMEOUT_SCHEMA,
                    "working_dir": {"type": "string", "description": "Directory the agent works in, e.g. a git worktree per task (default: the workspace)."},
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
            description="Spawn Codex CLI agent (GPT-6 Astra/Sol/Luna + GPT-5.6 Sol/Terra/Luna). Context: AGENTS.md.",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("codex")},
                    "timeout": TIMEOUT_SCHEMA,
                    "working_dir": {"type": "string", "description": "Directory the agent works in, e.g. a git worktree per task (default: the workspace)."}
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
                    "model": {"type": "string", "enum": settings.get_model_list("copilot")},
                    "timeout": TIMEOUT_SCHEMA,
                    "working_dir": {"type": "string", "description": "Directory the agent works in, e.g. a git worktree per task (default: the workspace)."}
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
                    "timeout": TIMEOUT_SCHEMA,
                    "working_dir": {"type": "string", "description": "Directory the agent works in, e.g. a git worktree per task (default: the workspace)."},
                    "yolo": {"type": "boolean", "default": False, "description": "Auto-approve all actions (YOLO mode)."}
                }
            }
        ),
        Tool(
            name="spawn_cursor",
            description="Spawn Cursor CLI agent (requires 'cursor-agent' in PATH + CURSOR_API_KEY).",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("cursor")},
                    "timeout": TIMEOUT_SCHEMA,
                    "working_dir": {"type": "string", "description": "Directory the agent works in, e.g. a git worktree per task (default: the workspace)."},
                    "force": {"type": "boolean", "default": False, "description": "Apply file changes directly (--force)."}
                }
            }
        ),
        Tool(
            name="spawn_opencode",
            description=("Spawn OpenCode CLI agent (free models: deepseek = DeepSeek V4.1 Flash, glm = GLM 5.3 Flash). "
                         "Edits files, runs commands. Context: AGENTS.md. Reports live to the owner's PowerBoard: "
                         "PowerSpawn creates the agent's card (doing), the agent adds steps/ticks/notes via the powerboard MCP, "
                         "and the card is closed with the result (done) or moved to waiting on failure."),
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "description": "Alias (" + ", ".join(settings.get_model_list("opencode")) + ") or any OpenCode provider/model id."},
                    "timeout": TIMEOUT_SCHEMA,
                    "agent_name": {"type": "string", "description": "Older name for `name` (the agent's name on the board and on PowerChannel); `name` wins when both are given."},
                    "task_summary": {"type": "string", "description": "Card title (default: first line of the prompt)."},
                    "board": {"type": "string", "description": "Board id or title (default: POWERBOARD_BOARD, else POWERSCROLL_BOARD, else the first board)."},
                    "working_dir": {"type": "string", "description": "Directory the agent works in, e.g. a git worktree per task (default: the workspace)."}
                }
            }
        ),
        Tool(
            name="spawn_grok",
            description="Spawn Grok CLI agent (Grok Build, requires 'grok' on PATH + grok login). Headless single-turn; edits land on disk (force=true, the default); force=false runs in plan mode (proposes, no writes). No `channel`: the Grok CLI has no per-run MCP option in headless mode.",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("grok")},
                    "force": {"type": "boolean", "default": True, "description": "Auto-approve all tool executions so edits land on disk (--always-approve). false = plan mode: it only proposes."},
                    "timeout": TIMEOUT_SCHEMA,
                    "working_dir": {"type": "string", "description": "Directory the agent works in, e.g. a git worktree per task (default: the workspace)."},
                    "system_prompt": {"type": "string", "description": "Extra rules appended to the agent's system prompt (--rules)."}
                }
            }
        ),
        Tool(
            name="spawn_grok_api",
            description="Spawn Grok agent via x.ai API (legacy text-only fallback). Needs XAI_API_KEY.",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": settings.get_model_list("grok-api")},
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
            description="List running agents (id, seconds, type, name, channel) and the last completed ones.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="result",
            description="Get an agent's result, with its name and channel.",
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
        Tool(
            name="verify_providers_availability",
            description="Check which spawn_* providers can run here (CLI on PATH, API key set), with install links for missing ones.",
            inputSchema={"type": "object", "properties": {}}
        )
    ])

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
        elif name == "spawn_cursor":
            return await handle_spawn(arguments, "cursor", spawn_cursor)
        elif name == "spawn_opencode":
            return await handle_spawn(arguments, "opencode", spawn_opencode)
        elif name == "spawn_grok":
            return await handle_spawn(arguments, "grok", spawn_grok)
        elif name == "spawn_grok_api":
            return await handle_spawn(arguments, "grok_api", spawn_grok_api)
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
        elif name == "verify_providers_availability":
            return [TextContent(type="text", text=json.dumps(verify_providers_availability(), indent=2))]
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }, indent=2))]

def _default_timeout(spawn_func) -> Any:
    param = inspect.signature(spawn_func).parameters.get("timeout")
    return param.default if param is not None else None


async def handle_spawn(args: dict, agent_type: str, spawn_func) -> list[TextContent]:
    """Generic handler for all spawn functions."""
    args = dict(args)
    prompt = args["prompt"]
    model = args.get("model")
    name = args.pop("name", None)
    channel = args.pop("channel", None)
    if agent_type == "opencode":
        name = name or args.get("agent_name")

    # The worker's unique name and optional PowerChannel channel. Errors here are
    # the coordinator's to fix, so they come back before anything starts.
    # The kill timer: an explicit timeout wins (0 = no limit); otherwise a CLI agent
    # gets POWERSPAWN_TIMEOUT or DEFAULT_SPAWN_TIMEOUT.
    if args.get("timeout") is None:
        args.pop("timeout", None)
        if agent_type in CLI_AGENTS:
            args["timeout"] = default_spawn_timeout()
    timeout = args["timeout"] if "timeout" in args else _default_timeout(spawn_func)

    try:
        worker = make_worker(
            agent_type, name=name, channel=channel,
            timeout=timeout or None,
            task=prompt, names_in_use=agent_manager.names_in_use(),
        )
    except ChannelError as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False, "error": str(e), "error_type": "ChannelError"}, indent=2))]

    if agent_type == "opencode":
        args["agent_name"] = worker.name
    if worker.channel:
        args["prompt"] = worker.brief() + prompt
        params = inspect.signature(spawn_func).parameters
        if "task_summary" in params and not args.get("task_summary") and worker.task:
            args["task_summary"] = worker.task  # IAC.md title: the task, not the brief

    # Register intent to start
    agent_id = agent_manager.register_start(agent_type, model or "default", prompt,
                                            name=worker.name, channel=worker.channel)

    def run_wrapper():
        try:
            # The worker belongs to this thread: providers add the PowerChannel MCP
            # server from it; the logger posts started/finished and mirrors to IAC.md.
            with worker_scope(worker):
                result = spawn_func(**args)

            # Register completion
            agent_manager.register_complete(agent_id, {
                "success": result.success,
                "result": result.text,
                "cost_usd": result.cost_usd,
                "error": result.error,
                "usage": result.usage,
                **worker.summary(),
            })
        except Exception as e:
            agent_manager.register_complete(agent_id, {
                "success": False,
                "result": "",
                "error": str(e),
                **worker.summary(),
            })

    # Start background thread
    thread = threading.Thread(target=run_wrapper, daemon=True)
    agent_manager.register_thread(agent_id, thread)
    thread.start()

    response = {
        "agent_id": agent_id,
        "agent_type": agent_type,
        "name": worker.name,
        "channel": worker.channel,
        "status": "running",
        "message": f"{agent_type} agent spawned as {worker.name}.",
    }
    if worker.channel:
        response["message"] += (f" It is on channel {worker.channel}; PowerSpawn posts its start and "
                                "finish there. Its questions to you start with @coordinator:. Watch with "
                                "read (not wait_for_agents) so you can answer.")
        response["worker_waits_up_to_seconds"] = worker.answer_budget
        response["watch"] = (f'read(me="<your name>", channel="{worker.channel}", wait_seconds=600); '
                             f'answer with post(me="<your name>", channel="{worker.channel}", '
                             f'message="@{worker.name}: ...")')
    return [TextContent(type="text", text=json.dumps(response, indent=2))]

async def handle_list() -> list[TextContent]:
    running = agent_manager.get_running_list()
    recent = agent_manager.get_recent_completed()
    return [TextContent(type="text", text=json.dumps({
        "running": running,
        "completed": recent,
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
            "name": info.get("name"),
            "channel": info.get("channel"),
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
            server_name="powerspawn",
            server_version=SERVER_VERSION,
            instructions=INSTRUCTIONS,
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
        await server.run(read_stream, write_stream, init_options)

def run() -> None:
    """Console-script entry point (`powerspawn`)."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
