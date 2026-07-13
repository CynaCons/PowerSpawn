# Design: Conversational & Persistent Agents (PowerSpawn fleet)

Status: **proposal / awaiting approval**. Two related features that turn PowerSpawn
from "fire-and-forget one-shot spawns" into an addressable fleet the coordinator
can converse with and re-invoke cheaply.

- **Feature A — Persistent / resumable role agents:** give a worker a role, then
  re-invoke *the same* worker later (reusing the CLI's session) without re-sending
  the full context.
- **Feature B — Ask-coordinator IPC channel:** let a running worker block on a
  question to the coordinator and resume once answered, with the coordinator
  notified to change focus.

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

## Feature B — Ask-coordinator IPC channel

### Concept
A running worker calls a provided **`ask_coordinator "<question>"`** command
(available as a shell tool, documented in AGENTS.md so every worker knows the
protocol). That command **blocks** until the coordinator answers, prints the answer
to stdout (which the worker reads as tool output), and the worker resumes — no
restart, no context re-injection.

### Mechanism — filesystem mailbox (portable MVP)
Per agent: `.powerspawn/ipc/<agent_id>/`. Protocol via an append-only `channel.jsonl`
(or `question.json`/`answer.json` pairs):

1. Worker runs `python -m powerspawn.ask "<question>"` (a tiny client injected via
   PATH / documented in AGENTS.md).
2. The client writes `{qid, text, ts}` to the mailbox and **polls** for a matching
   `answer` record, blocking up to `--wait` seconds (default e.g. 600s), emitting a
   periodic heartbeat so the CLI's idle-timeout doesn't kill it.
3. The **agent manager** watches mailboxes; when a question appears it flips the
   agent's status to `waiting_on_coordinator` and **emits a notification** (MCP/task
   event) so the harness nudges the coordinator to change focus. Polling via `list`
   is the fallback if notifications aren't delivered.
4. Coordinator calls `answer_agent(agent_id, answer)` → writes the `answer` record →
   the worker's client unblocks, prints the answer, the worker continues.

Chosen over named pipes/sockets: files are cross-platform, inspectable, and work
for *any* CLI that can run a shell command — no per-provider integration.

### API (new MCP tools)
- `list_pending_questions()` → `[{agent_id, qid, text, ts}]` (also surfaced in `list`).
- `answer_agent(agent_id, answer, qid=None)`.
- (client side) `powerspawn.ask` console entry-point.

### Why async spawn is required
Today a `spawn_*` MCP call blocks until the worker finishes, so the coordinator
can't answer mid-run while awaiting that same call. Feature B therefore rides the
**async manager**: spawn returns a handle, the coordinator does other work, and
answers questions as notifications/polls arrive. (This is already how
`spawn`+`wait_for_agents` behave, so no new runtime — just new tools + the mailbox.)

### Risks / open questions
- **Model compliance:** the worker must actually call `ask_coordinator` when stuck.
  Weaker models may not. Mitigate with a strong AGENTS.md convention + examples, and
  a timeout fallback ("no answer in N min → proceed with your best judgment / abort").
- **CLI idle/turn timeouts** may kill a long-blocked worker → heartbeat + keep
  `--wait` under the CLI's idle limit; re-ask if killed.
- **Coordinator notification:** best case the MCP server emits a task-event the
  harness surfaces; worst case the coordinator must poll `list_pending_questions()`.
  Confirm the notification path before promising "auto focus-change."
- **Deadlock/cleanup:** orphaned mailboxes on crash → TTL-sweep; block waits are
  bounded.

---

## Composition & phasing

They compose: a persistent expert (A) that can also ask questions (B) becomes a
long-lived collaborator the coordinator converses with both directions.

**Phase 1 (A):** resume adapters + registry + `create/ask/list/retire` tools +
no-resume fallback. Testable today against claude/grok/codex.
**Phase 2 (B.1):** mailbox + `powerspawn.ask` client + `list_pending_questions` /
`answer_agent` + AGENTS.md protocol; coordinator **polls**.
**Phase 3 (B.2):** wire the "question pending" **notification** so the coordinator
auto-changes focus (depends on MCP/harness notification support).

Each phase is independently useful and independently gated.

---

## Recommendation

Both are worth building; they're a real capability jump. Do **A first** — it's
mostly a registry over session features PowerSpawn already captures, low risk, and
immediately cuts token cost on repeated calls to the same worker. Then **B** in the
poll-first order above, promoting to notifications once the notification path is
confirmed. Ship each phase behind its own gate; keep the filesystem mailbox (not
sockets) for portability.
