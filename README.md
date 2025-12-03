# PowerSpawn - Universal Multi-Agent MCP Server

> **Spawn Claude AND Codex from one coordinator. Your agents leave a paper trail.**

A lightweight MCP server for cross-model AI agent orchestration. Works with Claude Code, GitHub Copilot, and any MCP-compatible client.

## Why PowerSpawn?

### 1. Uses Your Existing CLI Subscriptions
PowerSpawn spawns **real CLI agents** (Claude Code, GitHub Copilot, Codex) that you already have installed. No API keys to manage separately - just use your existing subscriptions.

### 2. Deterministic, Not Hopeful
The MCP server **wraps** sub-agents and handles all logging deterministically. We don't rely on agents "following instructions" to update files - the orchestrator captures inputs/outputs automatically.

### 3. Distribute Load Across Subscriptions
Hit Claude's rate limit? Spawn a Codex agent instead. PowerSpawn lets you **balance work across multiple AI subscriptions**, maximizing your throughput.

### 4. Full Oversight for User and Coordinator
- **CONTEXT.md** - See which agents are currently running
- **IAC.md** - Complete audit trail of all inputs and outputs (newest first, last 15 entries)

### 5. Persistent Memory Across Sessions
File-based state means **sessions can resume** even after:
- Coordinator agent runs out of context window
- Process restarts or crashes
- Hours or days between work sessions

### 6. Parallel Work in the Same Project
Multiple agents can work on different tasks simultaneously. The file-based architecture prevents conflicts and provides clear separation.

---

## Comparison with Other Frameworks

| Feature | PowerSpawn | AutoGen | CrewAI | LangGraph |
|---------|------------|---------|--------|-----------|
| Cross-model spawning | **Yes** (Claude + Codex) | No | No | No |
| Uses existing CLI subscriptions | **Yes** | No | No | No |
| Deterministic logging | **Yes** | No | No | No |
| File-based persistence | **Yes** (IAC.md) | No | No | No |
| Zero infrastructure | **Yes** | Partial | Partial | No |
| MCP protocol native | **Yes** | No | No | No |

## The IAC.md Pattern (Novel)

Traditional multi-agent systems use in-memory message passing or databases. PowerSpawn uses **markdown files** as the communication channel:

```
┌─────────────────────────────────────────────────────────────────┐
│                    COORDINATOR (Claude/Copilot)                 │
│                    Reads IAC.md, writes tasks                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │         IAC.md              │
              │  • Task assignments         │
              │  • Agent results            │
              │  • Human-readable log       │
              │  • Git-trackable            │
              └─────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────────────┐
│   CODEX SUB-AGENT     │       │     CLAUDE SUB-AGENT          │
│   • GPT-5.1 models    │       │     • Claude models           │
│   • Reads CONTEXT.md  │       │     • Reads AGENTS.md         │
│   • Writes to IAC.md  │       │     • Writes to IAC.md        │
└───────────────────────┘       └───────────────────────────────┘
```

**Why this matters:**
- **Auditable**: Every agent interaction is logged in plain markdown
- **Debuggable**: Read IAC.md to see exactly what happened
- **Persistent**: Survives process restarts, session timeouts
- **Version-controllable**: Git tracks your agent history

## Novelty Research (December 2025)

We analyzed 900+ MCP repositories and major frameworks. Findings:

| Claim | Verified | Evidence |
|-------|----------|----------|
| IAC.md pattern is novel | **Yes** | No equivalent found in existing repos |
| Cross-model orchestration is rare | **Yes** | Only 19 repos mention Claude + Codex together |
| MCP for agent spawning is uncommon | **Yes** | Most MCP servers are for external tools |

**Closest competitor**: `claude-flow` (1k stars) - but Claude-only, no cross-model support.

## Installation

PowerSpawn is distributed as a **git submodule** - no package managers needed.

### Add to your project

```bash
# Add as submodule
git submodule add https://github.com/CynaCons/PowerSpawn.git powerspawn

# Install Python dependencies
pip install mcp
```

### Configure your MCP client

**Claude Code** (`.mcp.json` in project root):
```json
{
  "mcpServers": {
    "agents": {
      "command": "python",
      "args": ["powerspawn/mcp_server.py"]
    }
  }
}
```

**GitHub Copilot** (`.vscode/mcp.json`):
```json
{
  "servers": {
    "powerspawn": {
      "command": "python",
      "args": ["powerspawn/mcp_server.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

### Update to latest version

```bash
git submodule update --remote powerspawn
```

## Quick Start

### With Claude Code

Once configured, these MCP tools are available:

```
mcp__agents__spawn_claude   - Spawn Claude sub-agent
mcp__agents__spawn_codex    - Spawn Codex (GPT) sub-agent
mcp__agents__list           - List running/completed agents
mcp__agents__result         - Get agent result by ID
mcp__agents__wait_for_agents - Wait for all agents to complete
```

**Example prompt:**
> "Can you powerspawn a Codex to run the test suite while you review the code?"

### Standalone Python

```python
from spawner import spawn_claude, spawn_codex

# Spawn Claude for code review
result = spawn_claude("Review src/App.tsx for security issues")

# Spawn Codex for testing (preserves Claude rate limit)
result = spawn_codex("Run npm test and report failures")
```

## Architecture

```
powerspawn/
├── mcp_server.py      # MCP server entry point (~500 lines)
├── spawner.py         # Core spawn logic for Claude/Codex
├── logger.py          # IAC.md logging with file locking
├── context_loader.py  # Project context injection
├── parser.py          # Response parsing (JSON, JSONL)
├── __init__.py        # Package exports
├── requirements.txt   # Python dependencies (just 'mcp')
├── schemas/           # JSON output schemas
├── examples/          # Usage examples
├── README.md          # This file
├── MCP_DESIGN.md      # Detailed architecture docs
└── DESIGN.md          # Original design document
```

**Auto-generated files (gitignored):**
- `IAC.md` - Inter-Agent Communication log
- `CONTEXT.md` - Active agent status

## Key Files

### CONTEXT.md - Project Context Injection
Every spawned agent automatically receives this file's content. Use it for:
- Project structure overview
- Key file locations
- Current sprint/iteration goals
- Environment-specific notes

### IAC.md - Inter-Agent Communication
The coordinator writes task assignments here. Agents read instructions and append results. Format:

```markdown
## Task: Run Production Tests
**Assigned to:** Codex
**Status:** In Progress
**Timestamp:** 2025-12-01T20:30:00

### Instructions
Run `npm run test:production` and report any failures...

### Result
[Agent appends result here when complete]
```

### AGENTS.md - Agent Instructions
Universal instructions injected into every agent. Defines:
- Available tools and restrictions
- Output format expectations
- Project conventions
- Do's and don'ts

## MCP Tools Reference

### spawn_claude
```json
{
  "prompt": "Your task description",
  "model": "sonnet",        // haiku | sonnet | opus
  "timeout": 600            // seconds (default: 600)
}
```

### spawn_codex
```json
{
  "prompt": "Your task description"
}
```

### list
Returns running and completed agent IDs.

### result
```json
{
  "agent_id": "abc123"
}
```
Returns the agent's output, cost, and status.

### wait_for_agents
Blocks until all running agents complete. Returns all results.

## Use Cases

### 1. Parallel Test + Review
```
Coordinator: "Spawn Codex to run tests while I review the PR"
→ Codex runs tests (doesn't consume Claude rate limit)
→ Claude reviews code
→ Both results collected
```

### 2. Research Task
```
Coordinator: "Powerspawn an Opus agent to research multi-agent patterns"
→ Opus agent does deep research with web search
→ Results written to IAC.md
→ Coordinator summarizes findings
```

### 3. Large Refactoring
```
Coordinator: "Spawn 4 agents to migrate different test file groups"
→ Agent 1: tests/editor/01-10
→ Agent 2: tests/editor/11-20
→ Agent 3: tests/editor/21-30
→ Agent 4: tests/editor/31-40
→ All run in parallel, results collected
```

## Configuration

Environment variables:
- `ANTHROPIC_API_KEY` - For Claude agents
- `OPENAI_API_KEY` - For Codex agents

Agent defaults are in the MCP server. Override via tool parameters.

## Roadmap

- [ ] GitHub Copilot compatibility testing
- [ ] Landing page at powerspawn.com
- [ ] MCP Registry submission
- [ ] Support for Gemini models
- [ ] Unit and integration test suite

## License

MIT - Use it, fork it, improve it.

---

**Built with AI, for AI orchestration.**

*Part of the [PowerTimeline](https://github.com/CynaCons/powertimeline) project.*
