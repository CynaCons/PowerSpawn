# MCP Agent Spawner - Design Document

**Version:** 1.4
**Date:** 2025-12-05
**Status:** Implemented

---

## 1. Purpose

Expose agent spawning as MCP tools so the orchestrator (Claude Code) can delegate tasks to sub-agents with:
- Automatic logging (IAC.md, CONTEXT.md)
- Deterministic behavior (no memory required)
- Thread-safe concurrent execution

## 2. Tools

### spawn_claude

Spawn a Claude sub-agent for reasoning tasks.

```
Parameters:
  prompt (required)  - The task to perform
  model (optional)   - haiku | sonnet | opus (default: sonnet)
```

Settings:
- Tools: Bash, Read, Write, Edit, Glob, Grep
- Timeout: 300s (600s for test tasks)
- Context: Claude CLI auto-loads CLAUDE.md from project root

### spawn_codex

Spawn a Codex (GPT-5.1) sub-agent for any task.

```
Parameters:
  prompt (required)  - The task to perform
```

Settings:
- Sandbox: `--dangerously-bypass-approvals-and-sandbox` (required for write access)
- Timeout: 300s
- Context: Codex CLI auto-loads AGENTS.md from project root

### spawn_copilot

Spawn a GitHub Copilot CLI sub-agent with any supported model.

```
Parameters:
  prompt (required)  - The task to perform
  model (optional)   - gpt-5.1 | gpt-5 | claude-sonnet | gemini (default: gpt-5.1)
```

Settings:
- Flags: `-s -p <prompt> --allow-all-tools --allow-all-paths --allow-tool shell --allow-tool write`
- Timeout: 600s
- Context: Copilot CLI auto-loads AGENTS.md from project root

**Supported models:**
| Model | Provider |
|-------|----------|
| `gpt-5.1`, `gpt-5`, `gpt-5-mini` | OpenAI |
| `claude-sonnet`, `claude-haiku`, `claude-opus` | Anthropic |
| `gemini` | Google |

### list

List running and recently completed agents.

```
Parameters: none
```

### result

Get the result of a completed agent.

```
Parameters:
  agent_id (required) - ID returned from spawn
```

### wait_for_agents

Block until all running agents complete, then return all results.

```
Parameters:
  timeout (optional) - Max seconds to wait (default: 300)
```

## 3. Architecture

```
┌──────────────────────────────────────────────────────┐
│  Claude Code (Orchestrator)                          │
│                                                      │
│  User says: "delegate testing to Codex"              │
│  Claude calls: mcp__agents__spawn_codex(prompt)      │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  MCP Server (mcp_server.py)                          │
│                                                      │
│  1. Log start to IAC.md                              │
│  2. Spawn subprocess (claude/codex/copilot CLI)      │
│     - CLI auto-loads context                         │
│  3. Log completion to IAC.md                         │
│  4. Return result                                    │
└──────────────────────────────────────────────────────┘
```

## 4. Context Loading

Context is loaded by the respective CLIs, not injected by the MCP server:

| Agent | CLI | Auto-loads |
|-------|-----|------------|
| Claude | `claude` | `CLAUDE.md` from project root |
| Codex | `codex` | `AGENTS.md` from project root |
| Copilot | `copilot` | `AGENTS.md` from project root |

## 5. Logging

**IAC.md** records:
- Spawn ID, agent type, timestamp (UTC)
- Task summary and full input prompt
- Duration, cost, success/failure status

**CONTEXT.md** shows currently active agents (resets on server restart).

## 6. Agent Comparison

| Agent | Best For | Rate Limit | Models |
|-------|----------|------------|--------|
| Claude | Reasoning, analysis | Anthropic quota | haiku/sonnet/opus |
| Codex | Any task | OpenAI quota | GPT-5.1 |
| Copilot | Any task, multi-model | GitHub subscription | GPT/Claude/Gemini |

## 7. Files

| File | Purpose |
|------|---------|
| `mcp_server.py` | MCP server implementation |
| `spawner.py` | Core spawn functions |
| `logger.py` | Writes to IAC.md |
| `IAC.md` | Inter-agent communication log |
| `CONTEXT.md` | Active agents status |

## 8. Configuration

`.mcp.json` in project root:

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
