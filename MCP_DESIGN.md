# MCP Agent Spawner - Design Document

**Version:** 1.5
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

### spawn_grok

Spawn a Grok sub-agent via X.ai API.

**Important:** This is an API agent - returns text response only. Cannot modify files or run commands. Use for analysis, research, and getting second opinions.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | Yes | The task for Grok to perform |
| model | string | No | Model to use (default: grok-3) |
| system_prompt | string | No | Optional system role context |
| timeout | integer | No | Timeout in seconds (default: 300) |

**Available models:** grok-3, grok-3-fast

**Example:**
```json
{
  "prompt": "Analyze this code for security vulnerabilities: ...",
  "model": "grok-3"
}
```

### spawn_gemini

Spawn a Gemini sub-agent via Google API.

**Important:** This is an API agent - returns text response only. Cannot modify files or run commands. Ideal for long context analysis and research.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | Yes | The task for Gemini to perform |
| model | string | No | Model to use (default: gemini-2.0-flash) |
| system_prompt | string | No | Optional system role context |

**Available models:** gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash

### spawn_mistral

Spawn a Mistral sub-agent via Mistral API.

**Important:** This is an API agent - returns text response only. Cannot modify files or run commands. Good for code analysis and European compliance.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | Yes | The task for Mistral to perform |
| model | string | No | Model to use (default: mistral-large-latest) |
| system_prompt | string | No | Optional system role context |

**Available models:** mistral-large-latest, mistral-small-latest, codestral-latest, open-mistral-nemo

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

| Agent | Type | File Access | Command Access | Best For |
|-------|------|-------------|----------------|----------|
| Claude | CLI | Yes | Yes | Complex reasoning, code review |
| Codex | CLI | Yes | Yes | Code generation, testing |
| Copilot | CLI | Yes | Yes | Multi-model via CLI |
| Grok | API | No | No | Fast responses, real-time info |
| Gemini | API | No | No | Long context, multimodal |
| Mistral | API | No | No | European AI, code tasks |

## 7. Files

| File | Purpose |
|------|---------|
| `mcp_server.py` | MCP server implementation |
| `spawner.py` | Core spawn functions |
| `logger.py` | Writes to IAC.md |
| `IAC.md` | Inter-agent communication log |
| `CONTEXT.md` | Active agents status |

## 8. API Key Configuration

API agents require authentication. Keys can be configured via:

### Option 1: Local File (Recommended)
Create `api_keys.json` in project root:
```json
{
  "XAI_API_KEY": "your-grok-key",
  "GEMINI_API_KEY": "your-gemini-key",
  "MISTRAL_API_KEY": "your-mistral-key"
}
```

### Option 2: Environment Variables
```bash
export XAI_API_KEY="your-grok-key"
export GEMINI_API_KEY="your-gemini-key"
export MISTRAL_API_KEY="your-mistral-key"
```

### Key Aliases
PowerSpawn checks multiple env var names:
- Grok: XAI_API_KEY, GROK_API_KEY, X_API_KEY
- Gemini: GEMINI_API_KEY, GOOGLE_API_KEY, GOOGLE_AI_KEY
- Mistral: MISTRAL_API_KEY

Local file takes priority over environment variables.

## 9. Configuration

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
