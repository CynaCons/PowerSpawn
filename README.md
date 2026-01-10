# PowerSpawn - Universal Multi-Agent MCP Server

**Live:** [powerspawn.com](https://powerspawn.com) | **Version 1.6.2**

> **Spawn Claude, Codex, AND Copilot from one coordinator. Your agents leave a paper trail.**

A lightweight MCP server for cross-model AI agent orchestration. Works with Claude Code, GitHub Copilot, and any MCP-compatible client. Supports GPT, Claude, Gemini, Grok, and Mistral models through CLI and API providers.

---

## Two Modes of Operation

PowerSpawn offers two distinct ways to spawn agents, each with different capabilities:

### CLI Agents (Full Autonomy)

| Provider | Command | Can Edit Files | Can Run Commands | Best For |
|----------|---------|----------------|------------------|----------|
| **Claude** | `spawn_claude` | ✓ Yes | ✓ Yes | Complex reasoning, code review |
| **Codex** | `spawn_codex` | ✓ Yes | ✓ Yes | Code generation, testing |
| **Copilot** | `spawn_copilot` | ✓ Yes | ✓ Yes | Multi-model via CLI |
| **Gemini** | `spawn_gemini_cli` | ✓ Yes | ✓ Yes | Multimodal via CLI |

**Use CLI agents for:**
- Code refactoring across multiple files
- Running test suites and fixing failures
- Creating new features with file creation
- Git operations and commits
- Any task requiring filesystem access

### API Agents (Text Response Only)

| Provider | Function | Can Edit Files | Can Run Commands | Best For |
|----------|----------|----------------|------------------|----------|
| **Grok** | `spawn_grok` | ✗ No | ✗ No | Fast responses, real-time info |
| **Gemini** | `spawn_gemini` | ✗ No | ✗ No | Long context, multimodal |
| **Mistral** | `spawn_mistral` | ✗ No | ✗ No | European AI, code tasks |

**Use API agents for:**
- Research and summarization (coordinator applies results)
- Getting a "second opinion" from different models
- Drafting text (cover letters, documentation)
- Code review analysis (coordinator applies fixes)
- Translation, brainstorming, ideation
- Parallel queries to multiple models

### Key Difference

```
CLI Agent:   Coordinator → Agent → [MODIFIES FILES] → Result
API Agent:   Coordinator → Agent → [TEXT RESPONSE] → Coordinator applies changes
```

**Example workflow with API agents:**
```
Coordinator: "Ask Gemini and Grok to review this function"
→ spawn_gemini("Review this code: ...")
→ spawn_grok("Review this code: ...")
→ Both return analysis text
→ Coordinator synthesizes feedback and applies fixes
```

## Why PowerSpawn?

### 1. Uses Your Existing CLI Subscriptions
PowerSpawn spawns **real CLI agents** (Claude Code, GitHub Copilot, Codex) that you already have installed. No API keys to manage separately - just use your existing subscriptions.

### 2. Deterministic, Not Hopeful
The MCP server **wraps** sub-agents and handles all logging deterministically. We don't rely on agents "following instructions" to update files - the orchestrator captures inputs/outputs automatically.

### 3. Distribute Load Across Subscriptions
Hit Claude's rate limit? Spawn a Codex agent instead. PowerSpawn lets you **balance work across multiple AI subscriptions**, maximizing your throughput.

### 4. Full Oversight for User and Coordinator
- **IAC.md** - Inter Agent Context: Active agents table at top + complete audit trail of all inputs and outputs (newest first, last 15 entries)

### 5. Persistent Memory Across Sessions
File-based state means **sessions can resume** even after:
- Coordinator agent runs out of context window
- Process restarts or crashes
- Hours or days between work sessions

### 6. Parallel Work in the Same Project
Multiple agents can work on different tasks simultaneously. The file-based architecture prevents conflicts and provides clear separation.

### 7. Extend Your Context Window
Sub-agents do the heavy lifting — reading files, searching code, running tests — and return **concise summaries** instead of raw data. Your coordinator's context stays lean, enabling:
- **Longer sessions** before hitting context limits
- **More complex tasks** within model constraints
- **Better focus** on orchestration, not file contents

---

## Comparison with Other Frameworks

| Feature | PowerSpawn | AutoGen | CrewAI | LangGraph |
|---------|------------|---------|--------|-----------|
| Cross-model spawning | **Yes** (Claude + Codex + Copilot) | No | No | No |
| Model diversity | **GPT, Claude, Gemini** | Limited | Limited | Limited |
| Uses existing CLI subscriptions | **Yes** | No | No | No |
| Deterministic logging | **Yes** | No | No | No |
| File-based persistence | **Yes** (IAC.md) | No | No | No |
| Context window optimization | **Yes** (summaries) | No | No | No |
| Zero infrastructure | **Yes** | Partial | Partial | No |
| MCP protocol native | **Yes** | No | No | No |

## The IAC Pattern (Inter Agent Context)

Traditional multi-agent systems use in-memory message passing or databases. PowerSpawn uses a single **markdown file** (IAC.md) as both status tracker and communication channel:

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
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ CODEX SUB-AGENT │ │ CLAUDE SUB-AGENT│ │COPILOT SUB-AGENT│
│ • GPT-5.1       │ │ • Claude models │ │ • GPT/Claude/   │
│ • Reads AGENTS  │ │ • Reads CLAUDE  │ │   Gemini models │
│ • Writes IAC.md │ │ • Writes IAC.md │ │ • Reads AGENTS  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
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

### Windows: Install PowerShell Core (required for Copilot shell commands)

Copilot CLI uses PowerShell Core (`pwsh`) for shell commands on Windows. Without it, file operations (Create, Edit, Read) work, but shell commands fail.

```powershell
# Install via winget
winget install Microsoft.PowerShell

# Verify installation
pwsh --version  # Should show PowerShell 7.x
```

> **Note:** After installation, restart your terminal for PATH changes to take effect.

### Configure your MCP client

#### Claude Code (Two files required)

**Step 1: Define the MCP server** (`.mcp.json` in project root):
```json
{
  "$schema": "https://raw.githubusercontent.com/anthropics/mcp/main/schema/mcp.json",
  "mcpServers": {
    "agents": {
      "command": "python",
      "args": ["powerspawn/mcp_server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

**Step 2: Enable the MCP server** (`.claude/settings.local.json`):
```json
{
  "permissions": {
    "allow": [],
    "deny": [],
    "ask": []
  },
  "enabledMcpjsonServers": [
    "agents"
  ],
  "enableAllProjectMcpServers": true
}
```

**Step 3: Restart Claude Code** to load the MCP server.

> **Note:** The `.claude/` directory is created automatically if it doesn't exist. Both files are required - `.mcp.json` defines the server, and `settings.local.json` enables it.

#### GitHub Copilot (Single file)

**`.vscode/mcp.json`:**
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
mcp__agents__spawn_claude   - Spawn Claude sub-agent (haiku/sonnet/opus)
mcp__agents__spawn_codex    - Spawn Codex sub-agent (GPT-5.1)
mcp__agents__spawn_copilot  - Spawn Copilot sub-agent (GPT/Claude/Gemini)
mcp__agents__list           - List running/completed agents
mcp__agents__result         - Get agent result by ID
mcp__agents__wait_for_agents - Wait for all agents to complete
```

**Example prompt:**
> "Can you powerspawn a Codex to run the test suite while you review the code?"

### Standalone Python

```python
from spawner import spawn_claude, spawn_codex, spawn_copilot

# Spawn Claude for code review
result = spawn_claude("Review src/App.tsx for security issues")

# Spawn Codex for testing (preserves Claude rate limit)
result = spawn_codex("Run npm test and report failures")

# Spawn Copilot with any model (GPT, Claude, or Gemini)
result = spawn_copilot("Analyze this codebase structure", model="gpt-5.1")
result = spawn_copilot("Write documentation", model="gemini")
```

## Architecture

```
powerspawn/
├── mcp_server.py      # MCP server entry point (~500 lines)
├── spawner.py         # Core spawn logic for Claude/Codex
├── api_providers.py   # API provider implementations (Grok, Gemini, Mistral)
├── logger.py          # IAC.md logging with file locking
├── context_loader.py  # Example: future role-based context (not currently used)
├── parser.py          # Response parsing (JSON, JSONL)
├── __init__.py        # Package exports
├── requirements.txt   # Python dependencies (just 'mcp')
├── schemas/           # JSON output schemas
├── examples/          # Usage examples
├── site/              # Landing page (powerspawn.com)
├── README.md          # This file
├── MCP_DESIGN.md      # Detailed architecture docs
└── DESIGN.md          # Original design document
```

**Auto-generated files (gitignored):**
- `IAC.md` - Inter Agent Context (active agents + interaction history)

## Key Files

### Context Files (Auto-loaded by CLIs)

PowerSpawn relies on the CLI tools' built-in context loading:

| Agent | CLI | Auto-loads |
|-------|-----|------------|
| Claude | `claude` | `CLAUDE.md` from project root |
| Codex | `codex` | `AGENTS.md` from project root |
| Copilot | `copilot` | `AGENTS.md` from project root |

These files should contain:
- Project structure overview
- Key file locations
- Current sprint/iteration goals
- Role guidelines (do's and don'ts)

### IAC.md - Inter Agent Context
Contains active agents status at the top, followed by interaction history. The coordinator writes task assignments here. Agents read instructions and append results. Format:

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

### AGENTS.md - Codex Agent Instructions
Auto-loaded by Codex CLI. Defines:
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

### spawn_copilot
```json
{
  "prompt": "Your task description",
  "model": "gpt-5.1"  // gpt-5.1 | gpt-5 | gpt-5.1-codex | gpt-5-mini |
                       // claude-sonnet | claude-haiku | claude-opus | gemini
}
```

**Available models:**
| Model | Provider | Description |
|-------|----------|-------------|
| `gpt-5.1` | OpenAI | GPT-5.1 (default) |
| `gpt-5` | OpenAI | GPT-5 |
| `gpt-5.1-codex` | OpenAI | Optimized for code |
| `gpt-5-mini` | OpenAI | Fast, lightweight |
| `claude-sonnet` | Anthropic | Claude Sonnet 4.5 |
| `claude-haiku` | Anthropic | Claude Haiku 4.5 |
| `claude-opus` | Anthropic | Claude Opus 4.5 |
| `gemini` | Google | Gemini 3 Pro Preview |

### spawn_grok
Spawn a Grok sub-agent via X.ai API (text response only).
```json
{
  "prompt": "Your task description",
  "model": "grok-3",           // grok-3 | grok-3-fast
  "system_prompt": "Optional role context"
}
```
**Note:** API agent - returns text only, cannot modify files.

### spawn_gemini
Spawn a Gemini sub-agent via Google API (text response only).
```json
{
  "prompt": "Your task description",
  "model": "gemini-2.0-flash"  // gemini-2.0-flash | gemini-1.5-pro | gemini-1.5-flash
}
```
**Note:** API agent - returns text only, cannot modify files.

### spawn_mistral
Spawn a Mistral sub-agent via Mistral API (text response only).
```json
{
  "prompt": "Your task description",
  "model": "mistral-large"     // mistral-large | mistral-small | codestral | devstral
}
```
**Note:** API agent - returns text only, cannot modify files.

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

### API Provider Keys

For API agents (Grok, Gemini, Mistral), configure keys via:

1. **Local file** (takes priority): Create `api_keys.json`:
   ```json
   {
     "XAI_API_KEY": "your-grok-key",
     "GEMINI_API_KEY": "your-gemini-key",
     "MISTRAL_API_KEY": "your-mistral-key"
   }
   ```

2. **Environment variables**: Set `XAI_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY`

Aliases supported: `GROK_API_KEY`, `GOOGLE_API_KEY` also work.

Get keys from:
- Grok: https://console.x.ai
- Gemini: https://aistudio.google.com/apikey
- Mistral: https://console.mistral.ai

## Deep Dive: Design Philosophy

For a comprehensive understanding of PowerSpawn's architecture and the reasoning behind our design decisions, read **[DESIGN.md](DESIGN.md)**.

Key highlights:
- **Why deterministic logging?** Agents are 95% unreliable at self-reporting (Section 6.1)
- **Layered supervision model** - User → Coordinator → Python → Sub-agents (Section 2.3)
- **The Determinism Principle** - Everything that CAN be done deterministically SHOULD be (Section 2.1)
- **Agent capability matrix** - When to use Claude vs Codex (Section 11)

## Troubleshooting

### Copilot "Permission denied" for file writes

**Symptom:** Copilot agent reports "Permission denied and could not request permission from user" when trying to create or edit files.

**Cause:** The `--allow-tool` flag in Copilot CLI takes a **variadic argument list**, meaning multiple tools must be passed as arguments to a single flag.

**Wrong:**
```bash
copilot --allow-tool shell --allow-tool write  # Each flag only gets one arg
```

**Correct:**
```bash
copilot --allow-tool shell write  # Both tools as args to one flag
```

**Fix in code:**
```python
# Wrong - separate flags
cmd = ["--allow-tool", "shell", "--allow-tool", "write"]

# Correct - single flag with multiple args
cmd = ["--allow-tool", "shell", "write"]
```

This was fixed in PowerSpawn v1.6.2 (spawner.py:611).

---

## Roadmap

- [x] Landing page at powerspawn.com
- [x] GitHub Copilot integration (spawn_copilot)
- [x] API agents: Grok, Gemini, Mistral
- [ ] MCP Registry submission
- [ ] Unit and integration test suite

## License

MIT - Use it, fork it, improve it.

---

**Built with AI, for AI orchestration.**

*Part of the [PowerTimeline](https://github.com/CynaCons/powertimeline) project.*
