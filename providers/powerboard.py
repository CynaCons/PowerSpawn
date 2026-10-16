"""
PowerBoard board reporting for spawned agents.

A spawned agent gets a card on a board, so the owner watches the work happen.
PowerSpawn does the bookends itself (card created + claimed when the agent
starts, a result note and the move to done/waiting when it exits) instead of
trusting the model to: free models do not reliably follow board instructions.
The agent adds checklist items, ticks and notes in between through its own
powerboard MCP server.

PowerBoard runs standalone (PowerBoard.html, served by the powerboard-mcp
server on port 41778) or embedded in a PowerScroll notebook (served by
powerscroll-mcp); both expose the same board tools, so only the configuration
changes. Board traffic goes through that MCP server (stdio), which joins the
notebook hub as a peer, so this works next to any other agent already
connected. Every failure is reported, never raised: the board must never stop
a spawn.

Config (environment):
  POWERBOARD_MCP_COMMAND   server command line, or a JSON array
                           (default: npx -y powerboard-mcp)
  POWERBOARD_BOARD         board id or title (default: the first board)
  POWERSPAWN_BOARD=off     disable board reporting

  Legacy names still accepted: POWERSCROLL_MCP_COMMAND, POWERSCROLL_BOARD.
  The newer POWERBOARD_* names win when both are set.
"""

import asyncio
import json
import os
import re
import shlex
import time
from dataclasses import dataclass
from typing import Any, Optional

DEFAULT_COMMAND = "npx -y powerboard-mcp"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,39}$")
LOCK_RETRY_SECONDS = 45
CALL_TIMEOUT_SECONDS = 30
READ_TOOLS = {"board_list", "board_read", "card_get", "bridge_status"}


class BoardError(Exception):
    pass


def board_enabled() -> bool:
    return os.environ.get("POWERSPAWN_BOARD", "on").strip().lower() not in ("off", "0", "false", "no")


def agent_env(me: str) -> dict[str, str]:
    """Environment for the board MCP server: both names, so it works whether the
    host is the standalone powerboard-mcp or powerscroll-mcp."""
    return {**os.environ, "POWERBOARD_AGENT_NAME": me, "POWERNOTE_AGENT_NAME": me}


def server_command() -> list[str]:
    raw = (os.environ.get("POWERBOARD_MCP_COMMAND", "").strip()
           or os.environ.get("POWERSCROLL_MCP_COMMAND", "").strip()
           or DEFAULT_COMMAND)
    if raw.startswith("["):
        return [str(x) for x in json.loads(raw)]
    return [part.strip('"') for part in shlex.split(raw, posix=(os.name != "nt"))]


def agent_name(raw: str) -> str:
    """Coerce anything into a valid PowerBoard agent name."""
    name = re.sub(r"[^a-z0-9._-]+", "-", (raw or "").lower()).strip("-._")[:40]
    if not name or not NAME_RE.match(name):
        name = ("a" + name)[:40] if name else "agent"
    return name


def _payload(result) -> Any:
    text = "".join(getattr(c, "text", "") for c in (result.content or []))
    if getattr(result, "isError", False):
        raise BoardError(text or "tool error")
    try:
        return json.loads(text)
    except ValueError:
        return text


async def _run_calls(me: str, calls) -> list:
    """Run calls in one short-lived peer session. Disconnecting at the end
    releases the notebook lease at once, so the agent's own writes are free."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    cmd = server_command()
    params = StdioServerParameters(command=cmd[0], args=cmd[1:], env=agent_env(me))
    results = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), CALL_TIMEOUT_SECONDS)
            for item in calls:
                if callable(item):  # a step that depends on earlier results
                    item = item(results)
                    if item is None:
                        results.append(None)
                        continue
                name, args = item
                deadline = time.monotonic() + LOCK_RETRY_SECONDS
                while True:
                    try:
                        # Read tools reject unknown args, so only writes carry `me`.
                        call_args = args if name in READ_TOOLS else {"me": me, **args}
                        res = await asyncio.wait_for(session.call_tool(name, call_args), CALL_TIMEOUT_SECONDS)
                        results.append(_payload(res))
                        break
                    except BoardError as e:
                        # LOCKED: another agent holds the lease. "Not connected to
                        # the agent hub yet": the peer is still joining after start.
                        transient = str(e).startswith("LOCKED") or "Retry in a moment" in str(e)
                        if transient and time.monotonic() < deadline:
                            await asyncio.sleep(1 if "Retry in a moment" in str(e) else 3)
                            continue
                        raise BoardError(f"{name}: {e}") from None
    return results


def _call(me: str, calls) -> list:
    try:
        return asyncio.run(_run_calls(me, calls))
    except BaseExceptionGroup as group:  # anyio wraps errors raised inside the session
        while isinstance(group, BaseExceptionGroup) and len(group.exceptions) == 1:
            group = group.exceptions[0]
        raise BoardError(str(group)) from None


def _pick_board(boards: list, wanted: str) -> Optional[dict]:
    if not boards:
        return None
    if not wanted:
        return boards[0]
    for b in boards:
        if b.get("id") == wanted:
            return b
    for b in boards:
        if (b.get("title") or "").strip().lower() == wanted.strip().lower():
            return b
    return None


@dataclass
class BoardCard:
    me: str
    board_id: str
    board_title: str
    number: int

    @property
    def ref(self) -> str:
        return f"#{self.number}"


def start_card(me: str, title: str, description: str, labels: list[str],
               board: Optional[str] = None) -> tuple[Optional[BoardCard], Optional[str]]:
    """Create a card in doing, claim it and mark the agent active on it.
    Returns (card, None) or (None, reason)."""
    if not board_enabled():
        return None, "board reporting disabled (POWERSPAWN_BOARD=off)"
    wanted = (board or os.environ.get("POWERBOARD_BOARD", "")
              or os.environ.get("POWERSCROLL_BOARD", ""))
    try:
        boards = _call(me, [("board_list", {})])[0]
        picked = _pick_board((boards or {}).get("boards", []), wanted)
        if picked is None:
            if wanted:
                return None, f"no board named or with id '{wanted}' in the open notebook"
            return None, "the open board host has no board: create one in PowerBoard"
        bid = picked["id"]
        created = _call(me, [
            ("card_create", {"boardId": bid, "title": title[:120], "description": description,
                             "column": "doing", "labels": labels}),
            lambda r: ("card_claim", {"boardId": bid, "card": _number(r[0])}),
            lambda r: ("agent_status", {"boardId": bid, "card": _number(r[0]),
                                        "text": f"Starting: {title[:80]}"}),
        ])
        return BoardCard(me, bid, picked.get("title", ""), _number(created[0])), None
    except Exception as e:  # never let the board stop a spawn
        return None, f"PowerBoard board unavailable: {e}"


def _number(card_result: Any) -> int:
    card = card_result.get("card", card_result) if isinstance(card_result, dict) else {}
    num = card.get("number")
    if num is None:
        raise BoardError(f"card_create returned no number: {str(card_result)[:200]}")
    return int(num)


def finish_card(card: BoardCard, success: bool, summary: str, duration_s: float) -> Optional[str]:
    """Post the result note, move the card to done (or waiting on failure) and
    sign the agent off. Returns a warning string on failure, else None."""
    mins = f"{duration_s / 60:.1f} min" if duration_s >= 90 else f"{duration_s:.0f}s"
    head = "Finished" if success else "Failed"
    note = f"{head} after {mins}.\n\n{(summary or '(no output)').strip()[:1800]}"
    move = {"boardId": card.board_id, "card": card.number, "to": "done"}
    if not success:
        move = {**move, "to": "waiting",
                "question": f"{card.me} failed: {(summary or 'no output').strip()[:200]} — coordinator to review."}
    try:
        _call(card.me, [
            ("card_note", {"boardId": card.board_id, "card": card.number, "text": note}),
            ("card_move", move),
            ("agent_leave", {"boardId": card.board_id, "note": f"{head.lower()} {card.ref}"}),
        ])
        return None
    except Exception as e:
        return f"PowerBoard board update failed: {e}"


def agent_brief(card: BoardCard) -> str:
    """The board protocol, prepended to the agent's prompt."""
    return (
        "## PowerBoard board — report your progress (required)\n"
        f"You are agent `{card.me}`. The owner watches your work live on card {card.ref} of the "
        f"PowerBoard board \"{card.board_title}\". Use the `powerboard` MCP tools and pass these "
        f"arguments on every call: me=\"{card.me}\", boardId=\"{card.board_id}\", card={card.number}.\n"
        "1. First, before any other work: `card_checklist_add` once per step of your plan (3-7 short steps).\n"
        "2. While working: `card_check` (item = 1-based index, done=true) as each step completes, "
        "`agent_status` with a one-line text of what you are doing now, and `card_note` for decisions "
        "or findings worth keeping (one or two lines each).\n"
        "3. If a board call returns LOCKED, wait about 10 seconds and retry once. Board trouble must "
        "never stop the real task.\n"
        "4. Do NOT move the card or call agent_leave: PowerSpawn closes the card with your final answer.\n"
        "Use only the board tools above in the notebook: do not edit notebook pages.\n\n"
        "## Your task\n"
    )
