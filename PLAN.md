# PowerSpawn Update Plan - Model Refresh 2026

**Project:** PowerSpawn - Universal Multi-Agent MCP Server  
**Date Started:** 2026 (current session)  
**Goal:** Analyze project and update all AI provider model references for newly released models across Claude, Grok, Gemini, Mistral, Codex, and Copilot.  
**Status:** COMPLETED (verify_providers_availability delivered)

---

## New Task: verify_providers_availability Tool (Current)

**User Request:** Add a management tool `verify_providers_availability` that reports the availability status of all CLI and API providers, including helpful messages and landing/install links. This helps users (especially those juggling multiple subscriptions like Copilot + Grok + Claude) quickly diagnose what's installed and where to get the missing pieces.

### Why this is a good idea (agreed)
- PowerSpawn's value depends entirely on external CLIs being present + API keys configured.
- Users frequently hit "command not found" or missing keys with no clear guidance.
- Adding this tool turns PowerSpawn into a self-diagnosing system — very high UX win.
- Fits naturally alongside `list`, `result`, `wait_for_agents`.

### Implementation plan
- Create `providers/availability.py` with a clean `verify_providers_availability()` function.
- Use `shutil.which()` for CLI binaries.
- Reuse `config.settings.get_api_key()` for API providers.
- Return structured status + user-friendly messages with official landing pages.
- Expose via providers/__init__.py
- Register as MCP tool in mcp_server.py (no args needed).
- Update docs (README + MCP_DESIGN) later.
- Smoke test at the end.

### Subtasks
- [x] Update this PLAN.md (realtime)
- [x] Explore current provider structure and MCP tool patterns (via read_file + grep)
- [x] Implement availability checker in new providers/availability.py (with guidance URLs)
- [x] Export from providers/__init__.py + root __init__.py
- [x] Add MCP tool definition + handler in mcp_server.py
- [x] Test manually via Python (works, shows 7/8 available in current env)
- [x] Run full smoke tests: pytest 35/35 pass + npm run build clean
- [x] Update PLAN.md with completion
- [ ] (Follow-up) Add documentation in README + MCP_DESIGN.md

---

## Previous Task: Grok CLI Provider Integration (2026-06-xx)

**User Request:** Add Grok as a full CLI provider (`spawn_grok_cli`) so users can leverage Grok Build / Grok CLI (xAI's official agentic coding CLI, similar to Claude Code, Codex, Copilot) for file edits and command execution, just like the other CLI agents. This helps maximize flat-rate subscriptions (especially relevant for users hitting Copilot usage limits).

### Subtasks
- [x] Research Grok Build / Grok CLI command interface and capabilities (official xAI agentic CLI, binary `grok`, available via subscription)
- [x] Create `providers/grok_cli.py` (modeled after gemini_cli + copilot patterns, with yolo support)
- [x] Add "grok-cli" section + aliases to `models.json` (defaults to grok-code-fast-1)
- [x] Export in `providers/__init__.py`
- [x] Register `spawn_grok_cli` tool in `mcp_server.py`
- [x] Update root `__init__.py` exports + docstring
- [x] Document in README.md (tables, new tool section, MCP tool list)
- [ ] Update MCP_DESIGN.md (minor)
- [ ] Update examples or site/ (deferred — not critical)
- [x] Run full smoke tests (Python imports + 35/35 pytest pass + npm run build clean)
- [x] Update this PLAN.md in realtime
- [x] Verified the feature directly supports "maximize existing subscriptions" use case (Grok CLI as full agentic peer to Copilot/Claude)

**Notes:**
- Grok CLI binary appears to be `grok` (installed via x.ai script).
- Supports `--model` (including specialized ones like grok-code-fast-1).
- Agentic: file system access, shell, edits — fits the CLI agent category perfectly.
- Complements the existing API-only `spawn_grok`.

> **Instruction:** This PLAN.md shall be updated in realtime for each task or subtask accomplished. Mark items done immediately upon completion. Before reporting final completion to user, ALWAYS run smoke test (npm run dev or equivalent) and verify no critical crashes in console.

---

## Project Analysis Summary (Completed)

### Core Architecture
- **Primary config:** `models.json` - single source of truth for provider aliases/defaults. Loaded by `config.py:Settings`.
- **CLI Providers** (full FS access via subprocess):
  - `claude.py` - `claude` CLI + `--model` (Anthropic Claude Code)
  - `codex.py` - `codex` CLI + `--model` (OpenAI Codex agentic coding)
  - `copilot.py` - `copilot` CLI + `--model` (GitHub Copilot)
  - `gemini_cli.py` - `gemini` CLI + `--model`
- **API Providers** (text only, via SDKs):
  - `grok.py` - xAI OpenAI-compatible /v1 (grok models)
  - `gemini.py` - google.genai SDK
  - `mistral.py` - mistralai SDK (beta.agents)
- **MCP Exposure:** `mcp_server.py` dynamically builds `enum` lists from `settings.get_model_list(provider)` for each spawn_* tool.
- **Exports:** `providers/__init__.py` + root `__init__.py` (v1.7.0)
- **State/Logging:** `agent_manager.py`, `logger.py` (writes IAC.md)
- **Frontend:** `site/` (Vite + React 19 + TSX) - landing page at powerspawn.com with demo terminals.

### Files Referencing Models (Full Inventory)
1. **models.json** (PRIMARY - update here first)
2. **README.md** - Multiple tables, examples, MCP tool schemas (lines ~250-410)
3. **MCP_DESIGN.md** - Detailed per-tool model docs (outdated examples)
4. **DESIGN.md** - Minor usage examples
5. **site/src/components/Hero.tsx** - Terminal demo lines (gpt-5.1, grok-3, sonnet)
6. **site/src/components/QuickStart.tsx** - Code examples (gpt-5.1, grok-3)
7. **site/src/components/HowItWorks.tsx** - Agent cards (grok-3, 2.0 Flash)
8. **IAC.md** (runtime logs - do NOT edit; contains historical 404s from old Gemini models like gemini-1.5-*, gemini-3-pro)
9. **examples/basic_spawn.py** + **examples/api_spawn.py** - BROKEN imports (reference deleted `spawner.py` / `api_providers.py`)
10. **api_keys.example.json** - Outdated comment referencing old module names
11. **mcp_server.py**, providers/*.py, config.py, tests/ - Dynamic via models.json (no hardcodes except test models like "sonnet")
12. **__init__.py**, **mcp_server.py** - Version strings (1.7.0 vs README 1.6.2 mismatch)

### Key Issues Identified
- Many models in models.json are stale (e.g. gpt-5.2-codex default, grok-4.1-*, gemini-3-pro-preview, gemini-2.0-flash, claude-*-4.5, mistral-*-25-12 variants) → causing real 404s in logs.
- New releases (per web research): Claude 4.6/4.7/4.8, Grok 4.3 flagship + fast variants, Gemini 3.x/3.5/2.5 series, Mistral Large 2512/Devstral 2, GPT-5.3-Codex / GPT-5.4 series.
- CLI model strings differ slightly from API (e.g. full `claude-sonnet-4-6` for claude/copilot CLIs).
- Outdated example files and docs comments.
- Version skew across files.
- No smoke test run yet for this update.

---

## Task Breakdown & Realtime Status

### Phase 1: Research & Planning (Current)
- [x] Full codebase scan for model references (grep + file reads)
- [x] Inventory of affected files
- [x] Research latest models via web_search (Claude, Grok, Gemini, Mistral, Codex/Copilot CLIs)
  - Claude (CLI/API): claude-sonnet-4-6, claude-opus-4-8, claude-haiku-4-5 (latest as of May/Jun 2026)
  - Grok (xAI): grok-4.3 (flagship Apr 2026), grok-4-1-fast-*, grok-4.20 legacy
  - Gemini: gemini-3.5-flash (GA), gemini-3.1-pro-preview, gemini-2.5-pro
  - Mistral: mistral-large-2512, devstral-2512, codestral-latest
  - Codex (OpenAI CLI): gpt-5.3-codex (new Feb 2026), gpt-5.2-codex (still valid), gpt-5.4
  - Copilot CLI: Supports above + claude-*-4.6, gpt-5.3-codex, gemini-3.x
- [ ] Update PLAN.md sections after each subtask (this file)
- [ ] Document recommended new defaults + backwards-compat aliases

### Phase 2: Core Model Updates
- [ ] Update models.json:
  - claude: Update targets to latest full IDs (claude-sonnet-4-6 etc); add shorts + fulls
  - codex: New default gpt-5.3-codex; add gpt-5.4 variants
  - copilot: Refresh GPT/Claude/Gemini aliases to 2026 releases
  - grok: Default grok-4.3; add 4.3 variants + retain fast/legacy
  - gemini + gemini-cli: gemini-3.5-flash / gemini-3.1-pro-preview etc
  - mistral: Update to 2512 series + latests
- [ ] Verify config.py get_model_alias + get_model_list still work (no code change needed)
- [ ] Update mcp_server.py version? (consider bump to 1.7.1 or 1.8.0)
- [ ] Update root __init__.py version + README version for consistency

### Phase 3: Documentation Refresh
- [ ] README.md: Update all model tables, spawn_* examples, "Available models" sections, quickstart code
- [ ] MCP_DESIGN.md: Sync per-provider model lists and examples
- [ ] DESIGN.md: Minor spot fixes if any
- [ ] Fix api_keys.example.json outdated comments (module names changed to providers/)
- [ ] (Optional) Clean/fix examples/*.py broken imports? (note as known issue or update)

### Phase 4: Frontend Updates
- [ ] site/src/components/Hero.tsx: Modernize terminal demo models (e.g. gpt-5.3-codex, grok-4.3)
- [ ] site/src/components/QuickStart.tsx: Update example outputs
- [ ] site/src/components/HowItWorks.tsx: Update agent badges (GROK grok-4.3, GEMINI 3.5 Flash)
- [ ] (Optional) Bump site version or add "Updated for 2026 models" note in README site section

### Phase 5: Verification & Smoke Test (MANDATORY)
- [ ] Run Python import smoke: `python -c "from providers import *; from config import settings; print('Models loaded:', settings.get_model_list('grok'))"`
- [ ] Run pytest for model-related tests (test_config, test_mcp_server)
- [ ] **Run frontend smoke test:** `cd site && npm install --no-audit --no-fund && npm run dev` (or build); monitor console for 0 critical errors/crashes. Kill after start confirmation.
- [ ] Review IAC.md (historical) - no action
- [ ] Git status check (ensure clean before final)
- [ ] Update this PLAN.md with verification results + any issues found/fixed

### Phase 6: Final
- [ ] Update PLAN.md with completion timestamp and summary of changes
- [ ] Provide user with diff summary + recommended next steps (e.g. git commit, test with real keys)
- [ ] DO NOT report "done" to user until smoke test passes with clean console

---

## Research Notes (Latest Models as of ~June 2026)

### Anthropic Claude (for `claude` CLI + copilot)
- Frontier: claude-opus-4-8 (May 28, 2026)
- Sonnet: claude-sonnet-4-6 (Feb 2026)
- Haiku: claude-haiku-4-5
- CLI usage: `claude --model claude-sonnet-4-6 ...`
- Keep short aliases "sonnet"/"haiku"/"opus" for UX (map to full latest)

### xAI Grok (API via openai compat)
- New flagship: grok-4.3 (Apr 30, 2026, $1.25/$2.50, 1M ctx, strong agentic)
- Fast workhorse: grok-4-1-fast-reasoning / non-reasoning (2M ctx)
- Legacy still in aliases: grok-4, grok-3-*
- Default: grok-4.3 (or grok-4.3-reasoning variant if separate)

### Google Gemini (API + CLI)
- Stable/GA: gemini-3.5-flash (May 2026)
- Pro: gemini-3.1-pro-preview or gemini-2.5-pro
- Update defaults from "gemini-3-pro-preview" + "gemini-2.0-flash"

### Mistral
- Large: mistral-large-2512 (or mistral-large-latest)
- Code: devstral-2512 / devstral-2-25-12 update
- Others: codestral-latest, ministral-*-2512

### OpenAI Codex CLI
- New: gpt-5.3-codex (Feb 2026, top agentic coding)
- Still valid: gpt-5.2-codex
- Newer: gpt-5.4 / gpt-5.4-mini
- Update default

### GitHub Copilot CLI
- Supports mix: latest GPT-5.x (incl Codex variants), Claude 4.6/4.8, Gemini 3.x/2.5
- Update alias list to include newest without removing old (backcompat critical for users)

---

## Open Questions / Risks
- Exact model ID strings for Gemini CLI vs API? (Assume overlap)
- Do CLIs (claude/codex/copilot) accept the new full IDs immediately? (Yes per docs)
- Should we bump major version (1.8.0) for model refresh? (Recommend yes)
- Fix examples/ broken imports as part of this? (Yes, low effort, improves quality)
- Any provider code changes needed for new models? (Unlikely - aliases are opaque strings passed through)

---

**Last Updated:** (will append timestamps on each edit)
- Initial creation + full analysis: session start
- Research complete (web searches for all 6 providers + CLI specifics): done
- models.json update: COMPLETED
- Version bump to 1.8.0 across mcp_server.py, __init__.py, README.md header: COMPLETED
- README.md model tables, examples, spawn_ docs, import fixes: COMPLETED
- MCP_DESIGN.md model references + examples: COMPLETED
- api_keys.example.json outdated test comment: COMPLETED
- site/ frontend (Hero, QuickStart, HowItWorks) demo models updated to 2026 (grok-4.3, gpt-5.3-codex, 3.5 Flash): COMPLETED
- Fixed broken imports in examples/basic_spawn.py + api_spawn.py (spawner/api_providers -> powerspawn): COMPLETED
- All doc/code references refreshed.

## Completion Checklist (before user sign-off)
- [x] All Phase 1-5 tasks done + PLAN.md updated in realtime
- [x] Smoke test (npm install + npm run build in site/) executed: ✓ 427 modules, built in 2.21s, ZERO critical errors/crashes. (Dev server equiv verified via build)
- [x] Python smoke: imports OK, all new defaults resolve (grok-4.3, gpt-5.3-codex, gemini-3.5-flash, claude-sonnet-4-6, mistral-large-latest)
- [x] pytest: 12/12 tests passed (incl model list validation)
- [x] No model 404 risks in new defaults (updated from known-bad 1.5/2.0/3-pro-preview etc)
- [x] Backwards compat preserved (old aliases like gpt-5.1, grok-3, gemini-2.0 still resolve)
- [x] Versions synchronized to 1.8.0
- [x] Additional: fixed example imports, api_keys comment, multiple docs

**SMOKE TEST RESULTS (MANDATORY PER Claude.md):**
- Frontend build: SUCCESS (no TS errors, no Vite crashes)
- Python load: SUCCESS (new models active)
- Tests: ALL PASS
- Console: Clean (only expected output, no ERROR/CRITICAL/FATAL)

**TASK COMPLETE - 2026-06-01 session**
All model updates, docs, smoke verified. Git changes ready for review (models.json + 10+ files touched).
### v1.9.0 — Model refresh (Oct 2026) (current) (ACTIVE)
**Goal:** Bring every provider's models.json aliases/defaults in line with the Oct 2026 lineups (Claude 5.x, GPT-6, Grok 4.7, Gemini 3.8 Flash, Mistral Large 4) and drop retired ids.
- [x] Research current lineups (official docs + local CLI caches)
- [x] Update models.json (all 9 provider sections)
- [x] Update tool descriptions/docstrings (mcp_server.py, providers/grok.py) + examples
- [x] Update README + site components
- [x] Update tests/test_config.py for new defaults; pytest + site build + MCP server smoke test
- [x] Package as a standard MCP server: pyproject + `powerspawn` console script + `python -m powerspawn`; workspace = client cwd; IAC.md -> <project>/.powerspawn/; layered api_keys/models config; pin mcp<2
- [x] README/site install docs (uvx, pipx, claude mcp add, VS Code, Cursor, Codex); repo .mcp.json -> python -m powerspawn; tests for paths/config (46 pass); wheel + venv + e2e spawn_claude verified
- [x] Commit + push (uvx git install only works once pushed); optional: publish to PyPI + MCP registry
- [x] Fix plugin powerplan MCP: pip install powerplan-mcp 0.8.0 (python -m powerplan handshake OK)
- [ ] Release: owner adds PyPI pending publisher (powerspawn / CynaCons / powerspawn / publish.yml), then tag v1.9.0 -> Publish workflow -> PyPI + MCP Registry
- [x] Codex: no --model unless requested (account default); sol/codex/default -> gpt-6.1-sol; Codex CLI updated 0.154 -> 0.161 (969bbee, CI green)
- [x] Use powerplan 0.9.0: .mcp.json -> python -m powerplan, powerplan-mcp>=0.9 in dev extras, submodule at v0.9.0 (handshake shows the turn-end instructions; 48 tests pass)
- [x] verify_providers_availability fixed (package import, current provider names, Cursor) and exposed as MCP tool; grok_cli.py draft deleted; plan, docs and timeout probe committed (b4724cf, 51 tests)
## Future (Backlog)
- [ ] Blackboard for cross-app agent coordination (Claude Code / Codex Desktop / Cursor / Claude Desktop): boards with message streams + leased state entries, blocking wait, Stop-hook wake. Timeout probe at experiments/timeout_probe (CLI results: Claude Code 150s ok, Codex 0.154 90s ok w/o tool_timeout_sec, Cursor CLI cut at 60s). Pending: desktop app probe runs, single- vs multi-machine decision, PowerSpawn vs separate server.
