# Design brief: "powerboard", a local blackboard for coordinating AI agents across desktop apps

Status: proposal, under review. Date: 2026-10-08. Owner: CynaCons (author of PowerSpawn, powerplan).

## 1. Problem

The owner works on one Windows 11 workstation with several AI coding agents open at the same
time in different desktop apps: Claude Code (CLI and the Code tab in the Claude desktop app),
Codex Desktop (0.160.1) and Codex CLI (0.154), Cursor desktop, sometimes Claude Desktop (chat).
These are long-lived sessions the human drives, NOT workers spawned by an orchestrator.

Today, to make them cooperate, the owner hand-rolls file-based IPC: agents read and write a shared
file. Claude Code notices file changes (it has a file watcher); Codex does not, so the owner sets
up cyclic triggers so Codex re-reads the file. This is messy and wastes model turns.

The owner also wants the same mechanism for non-agent coordination, e.g. "who is currently
controlling remote PC-3", i.e. a general shared "blackboard".

## 2. Goals

- An agent can create a named board (channel), others can discover/search boards and join one.
- Agents can push messages to a board and pull from it.
- Pull can be a tool call that blocks until something arrives (no model-level polling).
- Push notification to subscribed agents when possible; polling as worst case.
- Shared state, not only messages: keys with owner, version, optional lease/TTL, claim-if-free.
- Works across Claude Code, Codex (Desktop + CLI), Cursor, ideally Claude Desktop.
- Simple to install and use.

## 3. Facts established so far

### Measured on this machine (MCP tool call that sleeps, logs heartbeats)
| Client | Asked | Outcome |
|---|---|---|
| Claude Code CLI 2.1.293 | 150 s | completed |
| Codex CLI 0.154, default config (no tool_timeout_sec), with or without progress notifications | 90 s | completed |
| Codex CLI 0.154, tool_timeout_sec=400 | 150 s | completed |
| Codex Desktop 0.160.1, tool_timeout_sec=900 | 300 s | completed |
| Cursor desktop ("cursor-vscode 1.0.0") | 300 s | completed |
| Cursor CLI (cursor-agent) | 90 s | cancelled at exactly 60.0 s (-32001); it sends no progress token |
| Claude Desktop | n/a | not measured: the app rewrote claude_desktop_config.json on restart and dropped the server |

### From documentation / issue trackers (not verified locally)
- Claude Code CLI: MCP calls still running after 2 min are moved to a background task; the
  result is delivered later as a task notification that wakes the model
  (CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS). MCP_TOOL_TIMEOUT default very long; idle timeout 30 min
  for stdio (CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT).
- Claude Code "channels" (research preview): an MCP server declaring experimental capability
  `claude/channel` can push `notifications/claude/channel` {content, meta} into a session, which
  starts a turn even when idle. Custom servers require
  `claude --dangerously-load-development-channels server:<name>`, interactive sessions only.
  The Claude desktop app does not expose --channels (open feature request).
- Claude Code desktop app was reported (May 2026, one issue, closed not planned) to cancel stdio
  MCP calls at ~60 s ignoring MCP_TOOL_TIMEOUT.
- Codex hooks (CLI and Desktop): Stop hook input has session_id, transcript_path, cwd, turn_id,
  stop_hook_active, last_assistant_message. Output `{"decision":"block","reason":"..."}` makes
  Codex continue with `reason` as a new prompt. Hook timeout default 600 s, configurable.
  Known bug in 0.154: additionalContext rejected on SessionStart/Stop.
- Codex `codex queue --thread <id> --message <text>`: queues input to an existing thread. Wakes
  only threads loaded in the shared app-server daemon; on 0.154 an idle TUI is not woken
  (openai/codex#44491, closed not planned). From 0.158 the TUI runs on the shared daemon and
  third-party tools report live wake. `CODEX_THREAD_ID` is in the shell env of Codex sessions.
  Codex 0.157+ shared daemon reportedly breaks per-session identity for MCP servers.
- Cursor hooks (desktop + CLI): `stop` hook output `followup_message` is auto-submitted as the next
  user message; `loop_limit` default 5, null removes it. Stop hooks are fire-and-forget.
  `sessionStart` hook can return `additional_context` and `env`.
- Claude Desktop (chat): no hooks; MCP timeouts reported ~60 s (4 min on Windows).
- MCP spec has "Tasks" (durable handles, notifications/tasks); no evidence Claude Code / Codex /
  Cursor surface them to the model yet.
- Existing open-source projects in this space: osteele/agent-mail (on-disk spool, Claude channel
  push, Codex via check_inbox + reminder hooks), MustaphaSteph/agent-bus (one SQLite file,
  20 tools, no daemon), ajouthuse/mbus (rooms, presence, SQLite), alessandrobologna/agent-bus-mcp
  (topics, cursors, sync()), avivsinai/agent-message-queue (maildir, CLI, wake via codex queue),
  jtianling cross-agent-teams.

## 4. Proposed design (v1)

- New standalone MCP server package "powerboard" (sibling of powerplan / PowerSpawn), Python,
  stdio, distributed on PyPI (`uvx powerboard`), like powerplan-mcp.
- Each client app launches its own powerboard process; all share one SQLite database in WAL mode
  at a user-level path (~/.powerboard/board.db). No daemon.
- Storage behind a small interface so a networked board server can be added later (multi-PC).
- Data model:
  - board(name, topic, created_by, created_at)
  - member(board, name, last_seen, read cursor)
  - message(id, board, author, to?, text, created_at)
  - state(board, key, value, owner, version, expires_at)  -- leases via claim-if-free + TTL
- MCP tools (v1): board_list(query), board_create(name, topic), board_post(board, text, to?),
  board_read(board) [since this member's cursor], board_wait(board, timeout<=~300 s) [blocks
  until new message or watched key change; internal 250 ms check of PRAGMA data_version; sends
  progress notifications], state_get, state_set, state_claim(key, ttl), state_release,
  board_who.
- Identity: the agent passes its own member name (e.g. "codex-desktop", "claude-cli") when
  joining / posting, because one MCP server process may serve several conversations
  (Claude Desktop, Codex shared daemon) so process identity is unreliable.
- Human view: `powerboard tail <board>` and `powerboard ls` CLI.
- Phase 2 (idle wake): one `powerboard hook` command registered as the Stop hook in Claude Code,
  Codex and Cursor; checks unread messages for the session's memberships and returns them in each
  client's dialect (block/reason, followup_message), optionally "parking" for a few minutes.
  Open problem: mapping hook session_id -> board member name.
- Phase 3 (true push): Claude Code channels capability; Codex `codex queue` live wake (0.158+).

## 5. Open questions for reviewers

1. Is this worth building, versus adopting/forking an existing project?
2. Is the design sound (store, concurrency, identity, wake, failure modes, security/prompt
   injection between agents, cleanup/retention)?
3. Is it convenient for agents (tool count, naming, instructions) and for the human?
4. How to make install and deployment simple across Claude Code, Claude Desktop, Codex Desktop,
   Cursor (MCP registration + hooks), on Windows first, macOS/Linux too?
