"""
Codex CLI Provider
"""

import json
import subprocess
import time
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Iterator

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from .types import AgentResult

IS_WINDOWS = sys.platform == "win32"

def get_workspace_dir() -> Path:
    return Path(__file__).parent.parent.parent

@dataclass
class CodexEvent:
    type: str
    data: dict = field(default_factory=dict)
    
    @property
    def is_message(self) -> bool:
        return self.type == "item.completed" and self.data.get("item", {}).get("type") == "agent_message"
    
    @property
    def is_command(self) -> bool:
        return self.data.get("item", {}).get("type") == "command_execution"
        
    @property
    def text(self) -> Optional[str]:
        if self.is_message:
            return self.data.get("item", {}).get("text")
        return None
        
    @property
    def command_output(self) -> Optional[str]:
        if self.is_command:
            return self.data.get("item", {}).get("aggregated_output")
        return None

def _parse_codex_event(line: str) -> Optional[CodexEvent]:
    try:
        data = json.loads(line)
        return CodexEvent(type=data.get("type", "unknown"), data=data)
    except json.JSONDecodeError:
        return None

def _spawn_codex_stream(
    prompt: str,
    model: str,
    bypass_sandbox: bool,
    working_dir: Optional[str],
    timeout: int
) -> Iterator[CodexEvent]:
    cmd = ["codex", "exec", "--json"]
    if model:
        cmd.extend(["--model", model])
        
    if bypass_sandbox:
        cmd.append("--dangerously-bypass-approvals-and-sandbox")
    else:
        cmd.extend(["--sandbox", "read-only"])
        
    cwd = working_dir or str(get_workspace_dir())
    cmd.extend(["-C", cwd])
    
    # Use "-" to read prompt from stdin
    cmd.append("-")
    
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            shell=IS_WINDOWS,
            encoding='utf-8',
            errors='replace',
        )
        
        if proc.stdin:
            proc.stdin.write(prompt)
            proc.stdin.close()
            
        if proc.stdout:
            for line in proc.stdout:
                line = line.strip()
                if line:
                    event = _parse_codex_event(line)
                    if event:
                        yield event
                        
        proc.wait(timeout=timeout)
        
    except subprocess.TimeoutExpired:
        if proc: proc.kill()
        yield CodexEvent(type="error", data={"message": f"Timed out after {timeout}s"})
    except Exception as e:
        yield CodexEvent(type="error", data={"message": str(e)})
    finally:
        if proc and proc.poll() is None:
            proc.kill()

def spawn_codex(
    prompt: str,
    *,
    model: str = None,
    bypass_sandbox: bool = True,
    timeout: int = 300,
    task_summary: Optional[str] = None,
    working_dir: Optional[str] = None,
) -> AgentResult:
    """
    Spawn a Codex CLI agent.
    
    Context Handling:
        Codex CLI automatically loads AGENTS.md from the project root.
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("codex", model)
    
    sandbox_mode = "bypass" if bypass_sandbox else "read-only"
    spawn_id = log_spawn_start(
        agent="Codex",
        model=resolved_model,
        prompt=prompt,
        tools=[f"sandbox:{sandbox_mode}"],
        task_summary=task_summary,
        agent_type="CLI"
    )
    
    events = list(_spawn_codex_stream(prompt, resolved_model, bypass_sandbox, working_dir, timeout))
    
    duration = time.time() - start_time
    
    final_text = ""
    command_outputs = []
    usage = {}
    session_id = None
    error = None
    had_turn_completed = False
    
    for event in events:
        if event.type == "thread.started":
            session_id = event.data.get("thread_id")
        elif event.is_message:
            final_text = event.text or ""
        elif event.is_command:
            output = event.command_output
            if output:
                command_outputs.append(output)
        elif event.type == "turn.completed":
            usage = event.data.get("usage", {})
            had_turn_completed = True
        elif event.type == "error":
            error = event.data.get("message")
            
    # Success logic: no error AND (has message OR executed commands)
    success = error is None and (final_text != "" or (had_turn_completed and len(command_outputs) > 0))
    
    if not final_text and command_outputs:
        final_text = command_outputs[-1][:5000]
        
    log_spawn_complete(
        spawn_id=spawn_id,
        success=success,
        result_text=final_text,
        duration_seconds=duration,
        error=error
    )
    
    return AgentResult(
        success=success,
        text=final_text,
        spawn_id=spawn_id,
        session_id=session_id,
        usage=usage,
        error=error,
        model=resolved_model,
        provider="codex"
    )
