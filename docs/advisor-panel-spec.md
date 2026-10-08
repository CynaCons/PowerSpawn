# PowerSpawn Advisor Panel — Design Spec

**Status:** Draft (implementation-ready)  
**Author intent:** Constantin / CynaCons  
**Depends on:** PowerSpawn ≥ 1.8.x (`spawn_*`, `IAC.md`, `wait_for_agents`, CLI + API providers)  
**Companion:** optional [powerplan](https://github.com/CynaCons/powerplan) for plan-backed dogfood work  
**Product angle:** “AI Panel Advisor” — novelty is **turn-based checkpoints + shared criteria convergence**, not multi-model chat

---

## 1. Goals / Non-goals

### 1.1 Goals

1. **Subscription awareness** — Before spending quota, PowerSpawn knows which local CLI sessions / API providers are available (Claude Max / Claude Code, Codex / ChatGPT, Cursor, Copilot, Grok CLI/API, Gemini CLI/API). Prefer **local probes + config**; never put secrets in `PANEL.md` or `IAC.md`.
2. **Advisor personalities with durable memory** — Named personas (role lens + system prompt + memory store) that persist across panel runs and projects (or per-project, configurable).
3. **Multi-turn checkpointed panel protocol** — A deterministic 4-turn state machine:
   - **Turn 1 — Criteria:** each advisor lists key aspects/criteria for the consultation.
   - **Turn 2 — Converge:** advisors review/improve each others’ criteria and converge on a **shared consideration list**.
   - **Turn 3 — Independent answers:** each advisor answers using that shared list (no peeking at peers’ Turn-3 drafts until the turn closes).
   - **Turn 4 — Merge:** review all answers and produce a comprehensive **panel workproduct**.
4. **Deterministic orchestration** — Same philosophy as existing PowerSpawn: the MCP server (Python) owns state transitions, artifact writes, and IAC logging. Advisors must not be trusted to “remember” to advance the panel.
5. **Reuse existing spawn surface** — Panel turns call through `spawn_claude` / `spawn_codex` / `spawn_copilot` / `spawn_grok` / `spawn_grok_api` / `spawn_gemini` / `spawn_gemini_cli` / `spawn_mistral` (as available), plus `wait_for_agents` / `list` / `result`.
6. **Human-auditable paper trail** — Every turn leaves markdown artifacts under `.powerspawn/panel/<id>/` and summary entries in `IAC.md` (and a dedicated `PANEL.md` index).

### 1.2 Non-goals (MVP)

- Not a real-time multiplayer chat UI or streaming WebSocket panel.
- Not automatic billing / spend optimization across vendors (beyond inventory + soft warnings).
- Not replacing powerplan’s `PLAN.md` lifecycle — panels may *inform* plans; they do not own task checkboxes.
- Not storing or forwarding API keys, OAuth tokens, or CLI session cookies in panel artifacts.
- Not cross-user shared memory clouds (memory is local filesystem).
- Not guaranteeing identical answers across models — independence of Turn 3 is intentional.
- Not a full product website for “AI Panel Advisor” in the 1-week MVP (productization is later).

---

## 2. Subscription inventory model

PowerSpawn already markets “uses your existing CLI subscriptions.” The Advisor Panel makes that **queryable**.

### 2.1 Conceptual model

```text
SubscriptionInventory
  providers[]:
    id            # claude | codex | copilot | cursor | grok_cli | grok_api | gemini_cli | gemini_api | mistral
    kind          # cli | api
    available     # bool
    probe         # how we found it
    detail        # version, account hint (non-secret), rate-limit hints if any
    spawn_tool    # spawn_claude | spawn_codex | …
    notes         # human-readable caveats
```

**Hard rule:** Inventory records may store **paths to config files**, **binary versions**, **login presence booleans**, and **redacted account labels**. They must **never** store API keys, tokens, cookies, or full `api_keys.json` contents. `PANEL.md` may only reference provider *ids* and availability flags.

### 2.2 Discovery order (prefer local CLI probes + config)

| Provider | Preferred probes (read-only) | Config / signals (no secrets written to PANEL) | Maps to spawn tool |
|----------|------------------------------|--------------------------------------------------|--------------------|
| **Claude Max / Claude Code** | `which claude`; `claude --version`; optional `claude auth status` if available | Presence of Claude Code install; project `.mcp.json` / `.claude/` does not prove Max | `spawn_claude` |
| **Codex / ChatGPT** | `which codex`; `codex --version`; optional models cache `~/.codex/models_cache.json` (existence + model names only) | Login session presence via CLI status if exposed; **do not** read auth token files into inventory JSON | `spawn_codex` |
| **GitHub Copilot CLI** | `which copilot`; `copilot --version` | Copilot subscription implied by working CLI auth; Windows note: `pwsh` required for shell | `spawn_copilot` |
| **Cursor** | `which cursor` / Cursor CLI if present; optional Cursor Grok bridge notes | Cursor is often the *host* for Grok CLI (`grok` / Grok Build). Inventory may mark `cursor` as host IDE, not a spawn target itself unless a Cursor agent CLI exists | (routing hint only unless spawn path exists) |
| **Grok CLI** | `which grok`; `grok models` / `grok --version`; login via `grok login` session (probe status, not credentials) | Prefer CLI over API when logged in | `spawn_grok` |
| **Grok API** | Env or `api_keys.json` **key presence** (`XAI_API_KEY` / aliases) — boolean only | Keys stay in env / `api_keys.json` (existing PowerSpawn pattern) | `spawn_grok_api` |
| **Gemini CLI** | `which gemini` or documented Gemini CLI binary if installed | — | `spawn_gemini_cli` |
| **Gemini API** | Key presence (`GEMINI_API_KEY` / `GOOGLE_API_KEY`) — boolean only | Same as today | `spawn_gemini` |
| **Mistral API** | Key presence (`MISTRAL_API_KEY`) — boolean only | Same as today | `spawn_mistral` |

### 2.3 Probe implementation notes

- Run probes from the MCP server process with short timeouts (e.g. 3–5s per binary).
- Cache inventory in memory + optional `.powerspawn/subs_inventory.json` (gitignored) with `probed_at` timestamp; refresh on `subs_inventory(force=true)` or after TTL (e.g. 15 min).
- **Never** dump env vars or `api_keys.json` into IAC/PANEL. Only: `{"gemini_api": {"available": true, "probe": "env:GEMINI_API_KEY"}}`.
- If a CLI is on PATH but auth fails, mark `available: false` with `detail: "auth_required"`.
- Coordinator guidance: when Claude is rate-limited, prefer Codex / Copilot / Grok for remaining panel seats (existing “distribute load” value prop).

### 2.4 Panel seat binding

On `panel_create`, each advisor persona is bound to a **provider preference list**. Resolution:

1. First preferred provider with `available: true`.
2. Else next preference.
3. Else fail seat with `error: no_provider` (panel can still run with fewer advisors if `allow_partial_seats: true`).

---

## 3. Persona schema

Personas are durable advisor identities. Stored as YAML/JSON under a personas root (default user-level, overridable per project).

### 3.1 Schema

```yaml
# .powerspawn/personas/<persona_id>.yaml   (project)
# or ~/.powerspawn/personas/<persona_id>.yaml (user)

id: skeptic          # slug, unique within store
display_name: "The Skeptic"
role_lens: |
  Challenge assumptions, surface failure modes, demand evidence.
  Prefer falsification over affirmation.
system_prompt: |
  You are the Skeptic on an AI Advisor Panel.
  Be concise, structured, and adversarial-but-fair.
  Never invent facts; mark uncertainty explicitly.
memory_store_path: .powerspawn/memory/skeptic/   # relative to project, or absolute under ~/.powerspawn
providers:                 # ordered preference
  - claude                 # → spawn_claude
  - copilot
  - gemini_api
default_model:             # optional per provider
  claude: sonnet
  copilot: claude-sonnet-5
  gemini_api: gemini-2.0-flash
temperature_hint: low      # advisory only; mapped if spawn supports it
tags: [risk, critique]
version: 1
```

### 3.2 Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Stable slug used in PANEL.md and tool args |
| `display_name` | yes | Human label |
| `role_lens` | yes | Short lens injected into every turn prompt |
| `system_prompt` | yes | Full persona instructions (passed as `system_prompt` where spawn supports it; otherwise prepended to prompt) |
| `memory_store_path` | yes | Directory for durable memory files |
| `providers` | yes | Ordered provider ids from inventory |
| `default_model` | no | Per-provider model overrides |
| `temperature_hint` | no | Soft preference |
| `tags` | no | Filtering / presets |
| `version` | yes | Schema version for migrations |

### 3.3 Built-in MVP personas (ship as defaults)

| id | Role lens | Typical providers |
|----|-----------|-------------------|
| `strategist` | Options, tradeoffs, sequencing | claude, codex |
| `skeptic` | Risks, unknowns, disconfirming evidence | claude, gemini_api, grok |
| `operator` | Feasibility, ops cost, execution path | codex, copilot, grok_cli |
| `customer` | User value, messaging, adoption | gemini_api, claude, copilot |

Users can add custom personas without code changes (drop a YAML file).

### 3.4 Memory store layout

```text
.powerspawn/memory/<persona_id>/
  MEMORY.md           # curated long-term notes (human + tool editable)
  episodes/
    <YYYYMMDD>-<panel_id>.md   # append-only episode summaries after each panel
  index.json          # optional: {entries: [{id, title, path, tags, updated_at}]}
```

**Memory rules:**

- `advisor_memory_get` returns a **budgeted** excerpt (e.g. last N chars of `MEMORY.md` + last K episode titles), not the entire history by default.
- `advisor_memory_set` writes only through the MCP server (single writer), appending or replacing named sections — same determinism principle as `logger.py` for IAC.md.
- After Turn 4, the orchestrator may auto-append a short episode: question, shared criteria hash, workproduct path, and 3–5 bullets the persona should remember.

---

## 4. Panel run state machine

### 4.1 States

```text
                    panel_create
                         │
                         ▼
                   ┌───────────┐
                   │  created  │
                   └─────┬─────┘
                         │ panel_turn(1)  [or panel_run auto]
                         ▼
                   ┌───────────┐
          ┌───────►│  turn_1   │──spawn all advisors (criteria)──► wait_for_agents
          │        └─────┬─────┘
          │              │ artifacts OK / retries exhausted
          │              ▼
          │        ┌───────────┐
          │        │checkpoint1│  (human or auto-advance)
          │        └─────┬─────┘
          │              │ panel_turn(2)
          │              ▼
          │        ┌───────────┐
          │        │  turn_2   │──spawn all (review + converge)──► wait
          │        └─────┬─────┘
          │              ▼
          │        ┌───────────┐
          │        │checkpoint2│  shared consideration list frozen
          │        └─────┬─────┘
          │              │ panel_turn(3)
          │              ▼
          │        ┌───────────┐
          │        │  turn_3   │──spawn all (independent answers; isolated prompts)
          │        └─────┬─────┘
          │              ▼
          │        ┌───────────┐
          │        │checkpoint3│
          │        └─────┬─────┘
          │              │ panel_turn(4)
          │              ▼
          │        ┌───────────┐
          │        │  turn_4   │──spawn merge advisor(s) or all-review-then-merge
          │        └─────┬─────┘
          │              ▼
          │        ┌───────────┐
          │        │ completed │──► update memories, PANEL.md index
          │        └───────────┘
          │
          │        ┌───────────┐
          └────────┤  failed   │  (unrecoverable; partial artifacts kept)
                   └───────────┘
                   ┌───────────┐
                   │ cancelled │
                   └───────────┘
```

**Checkpoints:** After each turn, state is persisted to disk *before* the next turn starts. MVP can auto-advance (`auto_advance: true`). Pro may pause for human edit of the shared criteria between Turn 2 and Turn 3.

### 4.2 Artifacts per turn

| Turn | Per-advisor artifact | Shared artifact | Purpose |
|------|----------------------|-----------------|---------|
| 1 | `turns/01-criteria/<persona_id>.md` | `turns/01-criteria/_index.md` | Raw criteria lists |
| 2 | `turns/02-converge/<persona_id>.md` | `turns/02-converge/SHARED_CRITERIA.md` | Frozen consideration list |
| 3 | `turns/03-answers/<persona_id>.md` | `turns/03-answers/_index.md` | Independent answers |
| 4 | `turns/04-merge/<persona_id>.md` (optional review notes) | `WORKPRODUCT.md` | Final panel deliverable |

Also always:

- `PANEL.md` — panel metadata + state (see §4.4)
- `prompt_snapshots/` — exact prompts sent (for audit; gitignore-able if noisy)
- Linkage: each spawn logged in project `IAC.md` via existing `logger.py` path

### 4.3 Turn prompt contracts (implementation-ready)

**Turn 1 — Criteria**  
Input: consultation question + persona lens + memory excerpt.  
Output (markdown, required sections):

```markdown
## Criteria
1. ...
2. ...

## Notes
- ...
```

**Turn 2 — Converge**  
Input: question + **all** Turn-1 criteria files + persona lens.  
Output:

```markdown
## Critique of peers
...

## Proposed shared list
1. ...
2. ...
```

Server-side **merge of Turn 2**: deterministic reducer (see §4.5) writes `SHARED_CRITERIA.md`. Optional Pro: second micro-pass if lists diverge heavily.

**Turn 3 — Independent answers**  
Input: question + `SHARED_CRITERIA.md` only (not peer Turn-3 drafts) + persona lens + memory.  
Output:

```markdown
## Answer
...

## Per-criterion notes
### 1. <criterion>
...
```

**Turn 4 — Merge**  
Input: question + shared criteria + all Turn-3 answers.  
Default: spawn one **synthesizer** seat (often `strategist` or a dedicated `chair` persona) to produce `WORKPRODUCT.md`. Optional: all advisors submit merge notes, then chair synthesizes.

`WORKPRODUCT.md` required sections:

```markdown
# Panel Workproduct: <title>
## Question
## Shared criteria
## Synthesis
## Dissent / minority views
## Recommendations
## Open questions
## Sources / assumptions
```

### 4.4 `PANEL.md` layout (per panel)

Path: `.powerspawn/panel/<panel_id>/PANEL.md`

```markdown
# Panel: <panel_id>

| Field | Value |
|-------|-------|
| Status | turn_3 |
| Created | 2026-09-16T14:30:00+02:00 |
| Question | Should PowerTimeline prioritize X over Y? |
| Auto-advance | true |
| Advisors | strategist@claude, skeptic@gemini_api, operator@codex, customer@copilot |
| Shared criteria | turns/02-converge/SHARED_CRITERIA.md |
| Workproduct | (pending) |

## Seats

| Persona | Provider | Model | Status | Last spawn_id |
|---------|----------|-------|--------|---------------|
| strategist | claude | sonnet | ok | abc123 |
| skeptic | gemini_api | gemini-2.0-flash | ok | def456 |
| ... | ... | ... | ... | ... |

## Turn log

- turn_1 completed — 4/4 seats
- turn_2 completed — SHARED_CRITERIA.md frozen (7 items)
- turn_3 in_progress — waiting on operator
```

**Never** include API keys or raw env in this file.

### 4.5 Shared criteria reducer (Turn 2 → freeze)

Deterministic Python merge (not an LLM) for MVP reliability:

1. Collect each advisor’s `## Proposed shared list` items.
2. Normalize (lowercase, strip punctuation, light synonym map optional).
3. Cluster near-duplicates (simple fuzzy / token Jaccard).
4. Rank by: number of advisors mentioning + optional chair weights.
5. Cap at `max_criteria` (default 7–9).
6. Write `SHARED_CRITERIA.md` with stable IDs `C1…Cn`.

Pro later: LLM-assisted cluster labels with human approve checkpoint.

### 4.6 Relationship to `IAC.md`

- Panel orchestration **does not replace** IAC.md.
- Each underlying `spawn_*` still appends to `IAC.md` (active agents table + history) via existing logger.
- `PANEL.md` is the **panel-level** index; `IAC.md` remains the **spawn-level** audit trail.
- Convention: panel prompts include `panel_id` + `turn` in the task summary so IAC grepping is easy.

---

## 5. MCP tool surface

Expose as PowerSpawn MCP tools (same server as `spawn_*`, or clearly namespaced). Suggested names:

### 5.1 `subs_inventory`

```json
{
  "force": false
}
```

Returns inventory JSON (§2). No secrets.

### 5.2 `panel_create`

```json
{
  "question": "…",
  "advisors": ["strategist", "skeptic", "operator", "customer"],
  "title": "optional short title",
  "auto_advance": true,
  "allow_partial_seats": false,
  "max_criteria": 8,
  "timeout_per_seat_sec": 600,
  "panel_id": "optional-slug"
}
```

Effects:

1. Resolve providers via inventory.
2. Create `.powerspawn/panel/<id>/` tree.
3. Write initial `PANEL.md` (`status: created`).
4. Return `{panel_id, seats, status}`.

### 5.3 `panel_turn`

```json
{
  "panel_id": "…",
  "turn": 1,
  "force": false
}
```

- Validates state machine (must be at expected turn unless `force`).
- Builds prompts, calls `spawn_*` in parallel for seats, uses `wait_for_agents`.
- Writes artifacts, updates `PANEL.md`, advances to checkpoint / next turn if `auto_advance`.
- Returns `{status, artifacts[], seat_errors[]}`.

Convenience: `panel_run` (Pro or thin wrapper) = create + turns 1–4.

### 5.4 `panel_status`

```json
{
  "panel_id": "…"
}
```

Returns status, seat table, paths to latest artifacts, unfinished spawn ids.

### 5.5 `advisor_memory_get` / `advisor_memory_set`

```json
// get
{ "persona_id": "skeptic", "budget_chars": 4000, "include_episodes": 3 }

// set
{
  "persona_id": "skeptic",
  "mode": "append_section",   // append_section | replace_section | append_episode
  "section": "Preferences",
  "content": "…"
}
```

Single-writer filesystem updates; returns new excerpt or confirmation.

### 5.6 Optional helpers (MVP-nice)

| Tool | Purpose |
|------|---------|
| `panel_list` | List panels under `.powerspawn/panel/` |
| `persona_list` / `persona_get` | Inspect persona YAML |
| `panel_cancel` | Mark cancelled; do not spawn further turns |

### 5.7 Coordinator usage pattern

```text
subs_inventory()
panel_create(question, advisors=[…])
panel_turn(panel_id, turn=1)
panel_turn(panel_id, turn=2)   # or auto
# optional: human edits SHARED_CRITERIA.md
panel_turn(panel_id, turn=3)
panel_turn(panel_id, turn=4)
# read WORKPRODUCT.md; optionally advisor_memory_set / auto episode write
```

---

## 6. File layout under a project

```text
<project>/
  IAC.md                          # existing PowerSpawn audit (gitignored today)
  api_keys.json                   # existing; NEVER copied into panel artifacts
  .powerspawn/
    subs_inventory.json           # cache; gitignore
    personas/                     # optional project overrides
      strategist.yaml
      skeptic.yaml
      …
    memory/
      strategist/
        MEMORY.md
        episodes/
      skeptic/
        …
    panel/
      <panel_id>/
        PANEL.md
        WORKPRODUCT.md            # after turn 4
        turns/
          01-criteria/
            _index.md
            strategist.md
            skeptic.md
            …
          02-converge/
            strategist.md
            …
            SHARED_CRITERIA.md
          03-answers/
            _index.md
            strategist.md
            …
          04-merge/
            chair.md              # optional
        prompt_snapshots/         # optional, gitignore recommended
          t1-strategist.txt
          …
  powerspawn/                     # existing submodule
```

**Gitignore recommendations:**

```gitignore
IAC.md
api_keys.json
.powerspawn/subs_inventory.json
.powerspawn/panel/**/prompt_snapshots/
# Optionally ignore all panel runs, or commit WORKPRODUCT.md only:
# .powerspawn/panel/
```

User-global defaults (optional):

```text
~/.powerspawn/personas/
~/.powerspawn/memory/
```

Project personas override user personas on same `id`.

---

## 7. Failure modes and retries

Align with PowerSpawn’s deterministic supervision: **Python decides retries**, not the advisor.

| Failure | Detection | Retry policy (MVP) | Outcome |
|---------|-----------|--------------------|---------|
| Provider binary missing / not in inventory | Pre-flight on `panel_create` / seat bind | No retry; rebind to next preferred provider if any | Seat error or partial panel |
| Auth required / expired CLI session | Non-zero exit + stderr patterns | 0 auto-retries; surface `auth_required` | Fail seat; coordinator told to re-login |
| Provider down / network (API) | Timeout, HTTP 5xx, connection error | Up to **2** retries with backoff (2s, 8s) | Then seat `failed` |
| Timeout | `timeout_per_seat_sec` exceeded | **1** retry with same prompt (fresh spawn id) | Then seat `failed` |
| Empty / truncated response | Empty stdout or missing required `##` sections | **1** repair spawn with “complete the template” prompt | Then accept partial + flag in PANEL.md |
| Malformed Turn-2 list | Reducer gets <2 items | Re-prompt that seat once; if still bad, exclude from cluster | Shared list from remaining seats |
| Partial Turn-3 (one advisor down) | Seat failed after retries | Continue if ≥ `min_answers` (default: `ceil(n_advisors*0.5)` or ≥2) | Turn 4 notes missing seats under Dissent |
| All seats fail a turn | — | Panel → `failed`; artifacts retained | `panel_status` explains |
| Concurrent `panel_turn` on same id | File lock on `PANEL.md` | Second call errors `locked` | Caller retries later |
| Disk / permission errors | OSError | No retry | Panel `failed` |

**IAC.md:** every failed spawn still logged (success/failure, duration) via existing logger — do not swallow failures.

**Idempotency:** `panel_turn(turn=N)` if turn N already completed returns existing artifacts unless `force: true` (re-run).

---

## 8. MVP vs later (1-week vs Pro)

### 8.1 MVP — ~1 week (dogfoodable)

- [ ] `subs_inventory` with CLI `which`/`--version` + API key *presence* probes  
- [ ] Persona YAML load (4 built-ins) + memory get/set (append section + episode)  
- [ ] `panel_create` / `panel_turn` / `panel_status` / `panel_list`  
- [ ] Full 4-turn state machine with auto-advance  
- [ ] Deterministic Turn-2 criteria reducer  
- [ ] Artifacts under `.powerspawn/panel/<id>/` + `PANEL.md`  
- [ ] Reuse `spawn_*` + `wait_for_agents`; log to `IAC.md`  
- [ ] Retries: timeout×1, empty×1, API backoff×2  
- [ ] Dogfood script / documented prompt for PowerTimeline decision (§9)  
- [ ] Tests: reducer unit tests + fake spawn harness for state machine  

### 8.2 Pro / productization (“AI Panel Advisor”)

- [ ] Human checkpoint UI / pause for editing `SHARED_CRITERIA.md`  
- [ ] `panel_run` one-shot + progress streaming events  
- [ ] LLM-assisted criteria clustering with approve step  
- [ ] Spend / rate-limit telemetry and smarter load balancing  
- [ ] Cursor-as-first-class inventory + any future Cursor agent spawn  
- [ ] Cross-project persona/memory sync (still local, multi-repo)  
- [ ] Packaged product landing + MCP registry listing  
- [ ] Weighted voting / dissent heatmaps in workproduct  
- [ ] Integration with powerplan: “panel recommends → create_iteration / add_task”  
- [ ] Multi-chair or debate modes (extra turns beyond 4)  

Novelty to market: **checkpointed turns with a frozen shared consideration list**, not “ask 4 models the same question.”

---

## 9. Dogfood plan — PowerTimeline election decision

**Goal:** Use Advisor Panel on a real CynaCons decision so the feature proves itself before product claims.

### 9.1 Consultation question (example)

> **PowerTimeline product election:** Given PowerTimeline v0.8.x (collaborative “GitHub for timelines”), which near-term bet should we elect for the next major push — (A) deeper collaboration/fork UX, (B) AI-assisted timeline authoring via PowerSpawn, (C) distribution/SEO/content growth, or (D) monetization experiments — and what criteria should decide?

(Adjust options to the actual decision Constantin is making; keep them mutually exclusive enough that Turn 3 forces a stance.)

### 9.2 Panel seating

| Persona | Lens for this dogfood | Preferred provider |
|---------|----------------------|--------------------|
| `strategist` | Portfolio bet, sequencing | `spawn_claude` (sonnet/opus) |
| `skeptic` | Kill criteria, opportunity cost | `spawn_gemini` or `spawn_grok` |
| `operator` | Eng cost vs PLAN.md reality | `spawn_codex` |
| `customer` | Historian / educator / hobbyist user value | `spawn_copilot` or Gemini |

### 9.3 Procedure

1. In `powertimeline` repo (with PowerSpawn submodule / MCP configured): run `subs_inventory`; confirm ≥3 providers.  
2. `panel_create` with the election question and four advisors.  
3. Run turns 1–4 (`auto_advance: true` for speed; optionally pause after Turn 2 to hand-edit criteria).  
4. Read `WORKPRODUCT.md`; paste Recommendations into a powerplan iteration or PRD note.  
5. Verify: `IAC.md` shows four waves of spawns; memories gained episode files; no secrets in `PANEL.md`.  
6. Capture dogfood notes: time wall-clock, which seats failed, whether shared criteria felt better than single-shot multi-model chat.

### 9.4 Success criteria for dogfood

- Shared criteria list is **reused** by all Turn-3 answers (observable in artifacts).  
- Workproduct includes explicit **dissent** (not fake consensus).  
- At least one provider failover or load-split occurs if a seat is unavailable.  
- Constantin would trust the artifact enough to influence the real roadmap choice.

---

## 10. Implementation sketch (for PowerSpawn contributors)

Suggested modules (names illustrative):

```text
powerspawn/
  mcp_server.py          # register new tools alongside spawn_*
  spawner.py             # unchanged spawn primitives
  logger.py              # IAC.md — reuse
  panel/
    inventory.py         # subs probes
    personas.py          # load YAML, resolve seats
    memory.py            # get/set single-writer
    state.py             # PANEL.md read/write + file lock
    turns.py             # prompt builders + artifact writers
    reducer.py           # Turn-2 shared criteria merge
    tools.py             # MCP handlers: panel_*, advisor_*, subs_*
```

**Determinism principle (from DESIGN.md / MCP_DESIGN.md):** the server writes `PANEL.md`, turn artifacts, and memory episodes. Advisors only return text; they do not advance the state machine.

**system_prompt wiring:**

- API spawns (`spawn_grok_api`, `spawn_gemini`, `spawn_mistral`): pass `system_prompt`.  
- `spawn_grok`: pass via existing `system_prompt` / `--rules` path.  
- CLI agents without system_prompt param: prepend persona block to `prompt` (and optionally write a transient `.powerspawn/panel/<id>/PERSONA_<id>.md` referenced in the prompt).

---

## 11. Security & privacy checklist

- [ ] No secrets in `PANEL.md`, turn markdown, or memory episodes.  
- [ ] Inventory only records key *presence*, never values.  
- [ ] Prompt snapshots gitignored by default.  
- [ ] Panel prompts for API agents should not dump entire private repos unless the consultation needs it — prefer summaries (existing context-window optimization ethos).  
- [ ] File locks on `PANEL.md` and memory writes.

---

## 12. Open questions

1. Should `panel_*` live in the core PowerSpawn MCP or a thin `powerpanel` companion server (cf. powerplan separation)? **Recommendation:** start in-core for spawn reuse; split only if tool surface bloats.  
2. Exact Cursor inventory semantics if no spawn target exists yet.  
3. Whether Turn 4 should always be a single chair vs. full N-advisor merge debate.  
4. Default git policy: commit `WORKPRODUCT.md` only vs. full panel tree.

---

## 13. Summary

Advisor Panel extends PowerSpawn from “spawn many agents” to a **checkpointed consultation protocol**: inventory-aware seating, durable personas, four turns with a frozen shared criteria list, and a merged workproduct — all on the same deterministic, file-audited foundation as `IAC.md` and `spawn_*`. MVP is a one-week vertical slice; product novelty (“AI Panel Advisor”) is the turn protocol, proven first on a PowerTimeline product election dogfood.
