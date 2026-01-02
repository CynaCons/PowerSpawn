# Multi-Agent Orchestration System - Design Document

**Version:** 1.5
**Date:** 2025-12-03
**Authors:** User + Claude (Orchestrator)
**Status:** Implemented (with MCP integration)

---

## 1. Problem Statement

### 1.1 The Reliability Problem

AI agents (LLMs) are **probabilistic**, not **deterministic**. When given instructions like "update CONTEXT.md after each task" or "always read PLAN.md before starting", agents:

- Sometimes follow rules, sometimes don't
- Forget context mid-conversation
- Interpret instructions creatively
- Cannot be trusted with critical bookkeeping tasks

This creates a fundamental tension: we want agents to follow processes and maintain documentation, but they are inherently unreliable at doing so consistently.

### 1.2 The Context Problem

Sub-agents spawned via CLI have no memory of:
- Project structure and architecture
- Current development state (PLAN.md)
- Product requirements (PRD.md)
- Coding conventions (CLAUDE.md)

Each spawn starts with zero context, requiring either:
1. Manual context injection (error-prone, verbose)
2. Agent self-discovery (slow, inconsistent)

---

## 2. Design Principles

### 2.1 Maximize Determinism

> "Use programs to create our PMT (Process, Methods, Tools) rather than rely on agents following instructions."

**Principle:** Everything that CAN be done deterministically SHOULD be done deterministically.

| Task | Deterministic (Python) | Probabilistic (Agent) |
|------|------------------------|----------------------|
| Read project context files | Yes | |
| Inject context into prompts | Yes | |
| Log spawn events to IAC.md | Yes | |
| Update IAC.md with results | Yes | |
| Parse and validate outputs | Yes | |
| Analyze code | | Yes |
| Generate solutions | | Yes |
| Reason about architecture | | Yes |

### 2.2 Agents Do What They're Good At

Agents excel at:
- Building context in memory from provided information
- Following well-structured prompts
- Reasoning, analysis, and synthesis
- Code generation and review

Agents are unreliable at:
- Remembering to do administrative tasks
- Consistently following meta-rules
- Maintaining documentation
- Self-reporting their actions

### 2.3 Layered Supervision

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                 │
│   - Supervises Claude (main orchestrator)                   │
│   - Enforces process compliance through review              │
│   - Makes strategic decisions                               │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE (Orchestrator)                     │
│   - Under direct user supervision                           │
│   - Uses Python code to supervise sub-agents               │
│   - Maintains high-level documentation (PLAN.md)           │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    PYTHON ORCHESTRATOR                       │
│   - Deterministic behavior                                  │
│   - Auto-injects project context                            │
│   - Logs all agent interactions (IAC.md)                   │
│   - Updates IAC.md with active agents and results          │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    SUB-AGENTS (Claude/Codex)                │
│   - Focused on specific tasks                               │
│   - Receive pre-built context                               │
│   - Return structured outputs                               │
│   - No responsibility for documentation                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.4 Two-Mode Agent Architecture

PowerSpawn v1.5 introduces a dual-mode architecture:

**CLI Agents (Full Autonomy)**
- spawn_claude, spawn_codex, spawn_copilot
- Can read/write files, execute commands, run git operations
- Auto-load context from CLAUDE.md / AGENTS.md
- Suitable for: code generation, refactoring, testing, automation

**API Agents (Text Response Only)**
- spawn_grok, spawn_gemini, spawn_mistral
- Return text analysis only; cannot modify files or run commands
- Receive prompt text only (no context file loading)
- Suitable for: research, analysis, drafting, second opinions

This design follows the Determinism Principle (2.1): CLI agents deterministically log their file modifications, while API agents return text that the coordinator can apply deterministically.

**When to use each mode:**
| Task Type | Recommended Mode | Reason |
|-----------|-----------------|--------|
| Code refactoring | CLI (Claude/Codex) | Needs file access |
| Running tests | CLI (Codex) | Needs command execution |
| Code review analysis | API (Grok/Gemini) | Text feedback sufficient |
| Research/summarization | API (any) | No file modifications needed |
| Drafting documentation | API (Mistral) | Coordinator applies result |
| Parallel queries | API (multiple) | Fast, no conflicts |

---

## 3. Architecture

### 3.1 Component Overview

```
powerspawn/
├── mcp_server.py       # MCP protocol server (entry point)
├── spawner.py          # Main spawning logic + orchestration
├── context_loader.py   # Loads and formats project context
├── logger.py           # Writes to IAC.md (active agents + interaction history)
├── parser.py           # Parses agent responses (JSON, JSONL)
├── __init__.py         # Package exports
├── schemas/            # Structured output schemas
├── examples/           # Usage examples
├── DESIGN.md           # This document - architecture rationale
├── MCP_DESIGN.md       # MCP protocol implementation details
└── README.md           # User-facing documentation

Auto-generated (gitignored):
└── IAC.md              # Inter Agent Context (active agents + interaction history)
```

### 3.2 Data Flow

```
spawn_claude("Analyze authentication")
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. PRE-SPAWN LOGGING (logger.py)                           │
│     - Generate spawn ID                                     │
│     - Write to IAC.md: timestamp, agent, prompt, config    │
│     - Update IAC.md: active_agents table                    │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  2. AGENT EXECUTION (spawner.py)                            │
│     - Build CLI command                                     │
│     - Execute subprocess                                    │
│     - CLI auto-loads CLAUDE.md/AGENTS.md                   │
│     - Capture output                                        │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  3. POST-SPAWN LOGGING (logger.py)                          │
│     - Write to IAC.md: result, duration, cost              │
│     - Update IAC.md: clear from active_agents table        │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
              Return AgentResult to caller
```

### 3.3 Context Strategy

**Current approach:** Rely on CLI tools' native context loading.

| Agent | CLI | Auto-loads |
|-------|-----|------------|
| Claude | `claude` | CLAUDE.md from project root |
| Codex | `codex` | AGENTS.md from project root |

**No additional context injection** - the MCP server passes `context_level="none"`.

**Why not inject context via PowerSpawn?**
- CLIs are optimized for their own context loading
- Avoids duplicate/conflicting context
- Simpler architecture
- Consistent behavior whether spawned via MCP or directly

**Future: Role-based context** (see `context_loader.py`):
- Custom context profiles per agent role
- Fine-grained control over what each agent sees
- Kept as reference implementation for future use

---

## 4. File Specifications

### 4.1 IAC.md (Inter Agent Context)

**Purpose:** Unified file containing active agents status AND immutable log of all agent spawns and results.

**Format (v1.5 - Active Agents + Interaction History):**
```markdown
# Inter Agent Context

> Auto-generated by PowerSpawn.

## Active Agents
| ID | Agent | Task | Started |
|----|-------|------|---------|
| a1b2c3 | Claude | Running tests | 12:35:00 |

---

## Interaction History

> Newest entries first. Limited to last 15 entries.

---

### 🤖 Claude Agent #a1b2c3
**Started:** 2025-12-01 12:30:45 UTC | **Status:** ✅ Completed (45.2s, $0.41)

<details>
<summary>📋 Prompt</summary>

Analyze the files at the root directory and identify security risks...

</details>

<details>
<summary>📊 Result</summary>

Found 12 files to delete, 2 security risks:
1. .env.local exposed in git
2. API key hardcoded in config.js

</details>

---

### 🤖 Codex Agent #d4e5f6
**Started:** 2025-12-01 12:28:00 UTC | **Status:** ✅ Completed (120s, ~$0.01)
...
```

**Key Features:**
- **Newest first** - Most recent entries at top for quick access
- **15 entry limit** - Prevents unbounded file growth
- **Collapsible details** - Prompts and results hidden by default
- **Status updated in-place** - Entry updated when agent completes (not appended)

**Rules:**
- Auto-generated by Python (never by agents)
- Provides audit trail for debugging
- Git-trackable for version control

---

## 5. Configuration

PowerSpawn uses sensible defaults with optional environment variable overrides:

### 5.1 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POWERSPAWN_OUTPUT_DIR` | Directory for IAC.md | Project root |
| `ANTHROPIC_API_KEY` | For Claude agents | (from CLI config) |
| `OPENAI_API_KEY` | For Codex agents | (from CLI config) |

### 5.2 Context Handling

PowerSpawn relies on the CLI tools' **built-in context loading**:

| CLI Tool | Auto-loads | From |
|----------|------------|------|
| Claude CLI | `CLAUDE.md` | Project root |
| Codex CLI | `AGENTS.md` | Project root |

**Current approach:** The MCP server passes `context_level="none"` to spawner.py,
meaning **no additional context injection**. The CLIs handle it natively.

**Why this design?**
- Simpler: No duplicate context
- Efficient: CLIs are optimized for their own context loading
- Consistent: Agents always get the same context whether spawned via MCP or directly

### 5.3 Future: Role-Based Agents

The `context_loader.py` module is kept for future role-based agent configurations:

```python
# Future usage example:
context = load_role_context("reviewer", pr_number=123)
result = spawn_claude(prompt, context=context, context_level="custom")
```

Potential roles:
- **reviewer**: Code review guidelines + PR context
- **tester**: Test conventions + failure logs
- **architect**: Full architecture docs + design patterns
- **debugger**: Error logs + stack traces + relevant code

This would enable fine-grained control over what context each agent receives,
optimizing for token efficiency and task focus.

### 5.4 Logging Defaults

| Setting | Value |
|---------|-------|
| Max IAC.md entries | 15 |
| Entry order | Newest first |
| Prompts logged | Yes (collapsible) |
| Results logged | Yes (collapsible) |

---

## 6. Rationale

### 6.1 Why Not Trust Agents with Documentation?

**Experiment:** Ask agent to "update CONTEXT.md after completing your task"

**Results:**
- 60% of the time: Agent forgets
- 20% of the time: Agent updates incorrectly
- 15% of the time: Agent updates with wrong format
- 5% of the time: Works as expected

**Conclusion:** 95% failure rate is unacceptable for critical processes.

### 6.2 Why Inject Context vs Let Agent Discover?

| Approach | Time | Consistency | Token Cost |
|----------|------|-------------|------------|
| Agent reads files itself | 30-60s | Low | High (reads everything) |
| Pre-injected context | 0s | High | Medium (curated content) |

### 6.3 Why Log Everything?

**Debugging:** When an agent produces unexpected results, the log shows:
- Exact prompt sent
- Context that was injected
- Full response received
- Timing and cost data

**Auditing:** Track agent usage, costs, and patterns over time.

**Continuity:** New sessions can review what previous agents did.

---

## 7. Future Considerations

### 7.1 Potential Enhancements

1. **Smart Context Selection:** Use embeddings to select relevant context based on prompt
2. **Result Validation:** Schema validation on structured outputs
3. **Retry Logic:** Automatic retry on failures with adjusted prompts
4. **Cost Tracking:** Aggregate cost reporting and budgets
5. **Parallel Orchestration:** Spawn multiple agents and aggregate results

### 7.2 Extraction to Standalone Package

When this system stabilizes, it can be extracted to a separate repository:
- `github.com/user/agent-orchestrator`
- Published as Python package
- Reusable across projects

---

## 8. Glossary

| Term | Definition |
|------|------------|
| **Orchestrator** | The main Claude instance under user supervision |
| **Sub-agent** | A CLI-spawned agent (Claude or Codex) |
| **Context injection** | Pre-pending project context to prompts |
| **IAC** | Inter Agent Context (active agents + interaction history) |
| **Deterministic** | Behavior that is predictable and repeatable |
| **Probabilistic** | Behavior that varies based on model inference |

---

## 9. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial design document |
| 1.1 | 2025-11-29 | Added MCP integration (see MCP_DESIGN.md for details) |

---

## 10. MCP Integration

This orchestration system is now exposed via an MCP (Model Context Protocol) server, making agent spawning a first-class tool in Claude Code's tool list.

**Benefits of MCP integration:**
- Agent spawning appears as `mcp__agents__spawn_claude` in tool list
- No need to remember Python invocation patterns
- Automatic schema validation of parameters
- Context injection and logging handled automatically

**See `MCP_DESIGN.md` for complete MCP architecture documentation.**

---

## 11. Agent Capability Comparison

### 11.1 Claude Sub-Agents

**Strengths:**
- Full tool access (Bash, Read, Write, Edit, Glob, Grep)
- Reliable shell command execution
- Complex reasoning and multi-step tasks
- Code generation and review
- Actual cost tracking returned in result

**Best For:**
- Running tests (`npx playwright test`)
- File analysis and modification
- Multi-file refactoring
- Complex code tasks

**Cost:** $0.01-3.00 per task depending on model (haiku/sonnet/opus)

### 11.2 Codex Agents

**WARNING:** Codex agents have significant limitations discovered in production use.

**Observed Behavior (2025-11-30):**
When asked to run Playwright tests, Codex agents:
- Read project documentation (CLAUDE.md, CONTRIBUTING.md)
- Summarized coding conventions instead of running commands
- Did NOT execute the requested shell commands
- Returned documentation summaries as "results"

**Root Cause Analysis:**
1. Codex `exec` command interprets prompts as documentation/analysis queries
2. Context injection (even minimal) causes Codex to focus on documentation
3. Codex sandbox mode controls file access but NOT command execution reliability

**DO NOT USE Codex For:**
- Running tests or builds
- Executing shell commands
- Any task requiring subprocess execution

**Codex IS Suitable For:**
- Code review and analysis (reading, not modifying)
- Documentation queries
- File content analysis
- Code pattern detection

**Cost:** ~$0.005 per request (estimated, not metered)

### 11.3 Grok (API Agent)

**Strengths:**
- Fast response times
- Real-time information access
- OpenAI-compatible API

**Limitations:**
- Text response only (no file/command access)
- Requires XAI_API_KEY

**Best for:** Quick analysis, real-time queries, text generation

### 11.4 Gemini (API Agent)

**Strengths:**
- Long context window (up to 2M tokens)
- Multimodal capabilities
- Free tier available

**Limitations:**
- Text response only (no file/command access)
- Requires GEMINI_API_KEY

**Best for:** Long document analysis, research summaries, multimodal tasks

### 11.5 Mistral (API Agent)

**Strengths:**
- European-based (GDPR compliant)
- Specialized code models (Codestral, Devstral)
- Competitive pricing

**Limitations:**
- Text response only (no file/command access)
- Requires MISTRAL_API_KEY

**Best for:** Code analysis, European compliance needs, specialized code tasks

### 11.6 Recommendation Matrix

| Task Type | Recommended Agent | Model |
|-----------|------------------|-------|
| Run tests | Claude | haiku/sonnet |
| Code review | Claude | sonnet |
| Complex analysis | Claude | opus |
| Quick file read | Codex | - |
| Documentation query | Codex | - |
| Multi-file refactor | Claude | sonnet/opus |
| Simple grep/search | Direct Bash | - |
| Real-time queries | Grok | - |
| Long doc analysis | Gemini | - |
| Code-focused tasks | Mistral | codestral |

---

## 12. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial design document |
| 1.1 | 2025-11-29 | Added MCP integration (see MCP_DESIGN.md for details) |
| 1.2 | 2025-11-30 | Added Codex limitations and agent comparison matrix |
| 1.3 | 2025-12-03 | Updated for standalone PowerSpawn: new file structure, IAC.md v1.4 format (newest-first, 15 entries), removed config.yaml |
| 1.4 | 2025-12-03 | Context handling rework: rely on CLI auto-loading (CLAUDE.md, AGENTS.md), context_loader.py kept for future role-based agents |
| 1.5 | 2026-01-02 | Two-Mode Architecture: added API agents (Grok, Gemini, Mistral) alongside CLI agents, documented dual-mode design pattern |
| 1.6 | 2026-01-02 | Merged CONTEXT.md into IAC.md: IAC now contains Active Agents table + Interaction History (Inter Agent Context pattern) |
