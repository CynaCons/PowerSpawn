# PowerSpawn — TODO

## Cleanup
- [ ] **Remove the `CURSOR_AGENT_BIN` env-var shim** in `providers/cursor.py`.
      Added 2026-07-05 as a temporary workaround for a local Cursor CLI install
      at `%LOCALAPPDATA%\cursor-agent\agent.cmd` that wasn't on PATH. Once
      `cursor-agent` is reliably on PATH on all target machines, drop the env
      override and go back to a bare `CURSOR_BIN = "cursor-agent"`.

## Model registry — verify best-effort strings against live provider APIs
Verified 2026-07-05: claude, codex, grok, gemini (docs); copilot backends
smoke-tested (claude-sonnet-5, gpt-5.5, kimi-k2.7-code); cursor composer-2.5
smoke-tested. Still best-effort / worth confirming:
- [ ] copilot: exact CLI model slugs (dotted names are inferred from prior config).
- [ ] mistral: pinned versioned IDs (currently anchored on `-latest` aliases for safety).
- [ ] cursor: remaining model strings resolve via `cursor-agent --model` (only composer-2.5 tested).
