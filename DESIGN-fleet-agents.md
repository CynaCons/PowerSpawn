# Design: Conversational & Persistent Agents (PowerSpawn fleet)

Status: **proposal / awaiting approval**. Two related features that turn PowerSpawn
from "fire-and-forget one-shot spawns" into an addressable fleet the coordinator
can converse with and re-invoke cheaply.

- **Feature A — Persistent / resumable role agents:** give a worker a role, then
  re-invoke *the same* worker later (reusing the CLI's session) without re-sending
  the full context.
- **Feature B — Worker questions:** let a running worker ask the coordinator and
  wait for the answer. **Built in v1.12.0 on PowerChannel**; the filesystem mailbox
  first planned for it is dropped (see Feature B below).

They share one substrate and compose (a persistent expert that can also ask
questions), but are independently shippable. **Recommended order: A first** (lower
risk, leverages existing session capture), then **B**.

---

## 0. Substrate we already have

The MCP server already runs an **async agent manager**: `spawn_*` returns an
`agent_id` and runs the CLI in the background; `list`, `result`, and
`wait_for_agents` poll/join. Both features extend this manager rather than
introduce a new runtime. Key existing hooks:

- `providers/claude.py` already captures `session_id` from the CLI JSON.
- `providers/codex.py` already captures `thread_id` (session) from `thread.started`.
- `grok` CLI exposes `--continue`, `--resume`, `-s/--session-id`, `--fork-session`.

---

## Feature A — Persistent / resumable role agents

### Concept
A **persistent agent** is a named handle bound to `(provider, model, role,
session_id, cwd)`. Created once with a role (its standing briefing/expertise);
re-invoked by name with only the *new* prompt. The CLI's own session retains the
conversation, so we never re-inject the full context.

### Per-provider resume capability
| Provider | Resume mechanism | Notes |
|---|---|---|
| claude | `--resume <session_id>` (session_id already captured) | first-class |
| codex  | resume by `thread_id` | first-class |
| grok   | `--resume` / `-s <session_id>` / `--continue` | first-class |
| cursor | varies; may lack headless resume | fallback |
| gemini | no reliable headless resume | fallback |
| API (mistral/grok_api) | no server session | fallback |

**Fallback for no-resume providers:** keep a compact rolling **transcript summary**
per agent and re-inject `role + summary + new prompt` (a "poor-man's session").
Costs tokens but preserves the same API.

### Data model
Registry persisted to `.powerspawn/agents.json` (+ in-memory in the manager):
```
{ name, provider, model, role, session_id, cwd,
  created_at, last_used, turns, status,        // active | retired | dead
  transcript_summary? }                        // only for fallback providers
```

### API (new MCP tools + Python)
- `create_persistent_agent(name, role, provider, model=None, cwd=None)` → establishes
  the session (an initial no-op / "ack your role" turn) and stores the handle.
- `ask_persistent_agent(name, prompt, timeout=...)` → resume the session with just
  `prompt`; update `session_id`/`last_used`/`turns`; return the reply.
- `list_persistent_agents()` / `retire_agent(name)`.

`spawn_*` gains an internal `resume_session_id` param the providers pass to their
CLI's resume flag; `create/ask_persistent_agent` are thin wrappers over that.

### Risks
- Session TTL/eviction differs per CLI; a resumed session may be gone → detect the
  resume failure and transparently fall back to `role + summary`.
- Concurrency: serialize turns per named agent (a session isn't safe to drive twice
  at once).

---

## Feature B — Worker questions over PowerChannel (replaces the ask-coordinator mailbox)

**Status: decided 2026-11-22, built in v1.12.0.** The filesystem mailbox planned here
(`.powerspawn/ipc/<agent_id>/`, `python -m powerspawn.ask`, `list_pending_questions`,
`answer_agent`) is **dropped**. Worker questions go over
[PowerChannel](https://github.com/CynaCons/PowerChannel) instead: named channels in one
SQLite file shared by every agent on the machine, with `channels`, `post` and a `read` that
can wait for the next message. The guide is [docs/powerchannel.md](docs/powerchannel.md).

Why: PowerChannel already is the blocking, cross-app message channel this section was going
to build, and it works for agents PowerSpawn didn't spawn too (the owner's own Claude Code,
Codex and Cursor sessions). One mechanism instead of two.

How it works now:
- Every `spawn_*` gives its worker a unique agent name (`name`, or generated `<cli>-<4 hex>`).
- `channel` is optional; the coordinator chooses: none, a shared feature channel
  (`channel="release"`), or one for that worker alone (`channel="dedicated"` -> `dm-<name>`).
- With a channel, PowerSpawn adds the PowerChannel MCP server to that one run and prepends a
  brief: read once, post results and questions, start questions with `@coordinator:`, then
  `read(wait_seconds=N)` with N below both the spawn timeout and the CLI's MCP tool limit.
- The coordinator watches with its own `read(..., wait_seconds=...)` and answers with `post`.
- PowerSpawn posts started / finished / failed / timed out as `powerspawn`, and mirrors the
  channel traffic of the run into IAC.md, which stays the audit log.

What the old risks became:
- *Model compliance*: unchanged; the brief tells the worker exactly what to call, with a
  fallback ("no answer after 3 waits: proceed and say what you assumed").
- *CLI tool timeouts*: per-CLI wait limits in the brief (Cursor CLI 50 s, Gemini 540 s,
  Claude/Codex up to 12 h capped by the spawn timeout).
- *Coordinator notification*: the coordinator waits in `read`; nothing pushes to it.
- *Cleanup*: PowerChannel keeps 7 days of messages; there are no mailboxes to sweep.

Still open (backlog, "Phase 3"): a watcher that **resumes a sleeping worker** when a message
lands on its dedicated channel (`claude -p --resume`, `codex exec resume`,
`cursor-agent --resume`; headless resume is proven for those three in PowerChannel's wake
probe). This is where Feature A and B meet.

---

## Composition & phasing

They compose: a persistent expert (A) that can also ask questions (B) becomes a
long-lived collaborator the coordinator converses with both directions.

**Phase 1 (A):** resume adapters + registry + `create/ask/list/retire` tools +
no-resume fallback. Testable today against claude/grok/codex.
**Phase 2 (B):** done in v1.12.0 over PowerChannel (`name` + `channel` on every
`spawn_*`); no mailbox, no `list_pending_questions` / `answer_agent`.
**Phase 3:** a watcher that resumes a sleeping worker when a message lands on its
dedicated channel (backlog).

Each phase is independently useful and independently gated.

---

## Recommendation

Both are worth building; they're a real capability jump. Do **A first** — it's
mostly a registry over session features PowerSpawn already captures, low risk, and
immediately cuts token cost on repeated calls to the same worker. Then **B** in the
PowerChannel (B shipped in v1.12.0; the filesystem mailbox is dropped). Ship each
phase behind its own gate.
