"""
MCP tool-call timeout probe.

Register this stdio server in any MCP client and ask the agent to call
`probe_sleep` with e.g. 90, 300 or 900 seconds. Every call is logged to
~/.powerspawn-probe/probe.jsonl with a heartbeat every 5 s, so the log shows
exactly when (and how) the client gave up:

  done       - the call ran to completion and the result was returned
  cancelled  - the client sent notifications/cancelled (clean timeout)
  (no end)   - heartbeats just stop: the client killed the server process

`probe_results` prints a per-call summary from the log.
"""

import asyncio
import json
import os
import time
import uuid
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP

LOG = Path.home() / ".powerspawn-probe" / "probe.jsonl"
HEARTBEAT_SEC = 5

mcp = FastMCP("timeout-probe")


def _log(**event) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {"ts": round(time.time(), 1), "pid": os.getpid(), **event}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def _client(ctx: Context) -> str:
    try:
        info = ctx.session.client_params.clientInfo
        return f"{info.name} {info.version}"
    except Exception:
        return "unknown"


@mcp.tool()
async def probe_sleep(seconds: int, ctx: Context, progress: bool = True) -> str:
    """Sleep for `seconds` (logging a heartbeat every 5 s) to measure this client's tool-call timeout.

    progress=True also sends MCP progress notifications, which some clients use to extend the timeout.
    """
    call = uuid.uuid4().hex[:8]
    meta = ctx.request_context.meta
    token = getattr(meta, "progressToken", None) if meta else None
    _log(call=call, event="start", client=_client(ctx), seconds=seconds,
         progress=progress, client_sent_progress_token=token is not None)
    start = time.monotonic()
    try:
        while (elapsed := time.monotonic() - start) < seconds:
            await asyncio.sleep(min(HEARTBEAT_SEC, seconds - elapsed))
            elapsed = round(time.monotonic() - start)
            _log(call=call, event="heartbeat", elapsed=elapsed)
            if progress and token is not None:
                await ctx.report_progress(elapsed, seconds)
    except asyncio.CancelledError:
        _log(call=call, event="cancelled", elapsed=round(time.monotonic() - start, 1))
        raise
    _log(call=call, event="done", elapsed=round(time.monotonic() - start, 1))
    return f"probe {call}: slept {seconds}s without being cut off"


@mcp.tool()
def probe_results(last: int = 10) -> str:
    """Summarise the last `last` probe_sleep calls from the log (all clients)."""
    if not LOG.exists():
        return "no probe calls logged yet"
    calls: dict[str, dict] = {}
    for line in LOG.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        c = calls.setdefault(e["call"], {"call": e["call"]})
        if e["event"] == "start":
            c.update(client=e["client"], asked=e["seconds"], progress_token=e["client_sent_progress_token"])
        elif e["event"] == "heartbeat":
            c["last_heartbeat"] = e["elapsed"]
        else:
            c["outcome"], c["at"] = e["event"], e["elapsed"]
    rows = []
    for c in list(calls.values())[-last:]:
        outcome = c.get("outcome")
        if outcome is None:
            outcome = f"killed/abandoned after ~{c.get('last_heartbeat', 0)}s"
        else:
            outcome = f"{outcome} at {c['at']}s"
        rows.append(f"{c['call']}  {c.get('client', '?'):<32} asked {c.get('asked', '?'):>4}s  "
                    f"progress_token={c.get('progress_token')}  -> {outcome}")
    return "\n".join(rows)


if __name__ == "__main__":
    mcp.run()
