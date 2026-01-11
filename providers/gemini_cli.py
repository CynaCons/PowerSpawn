"""
Gemini CLI Provider
"""

import subprocess
import time
import sys
from pathlib import Path
from typing import Optional

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from .types import AgentResult

IS_WINDOWS = sys.platform == "win32"

def get_workspace_dir() -> Path:
    return Path(__file__).parent.parent.parent

def spawn_gemini_cli(
    prompt: str,
    *,
    model: str = None,
    timeout: int = 300,
    task_summary: Optional[str] = None,
    working_dir: Optional[str] = None,
    yolo: bool = False,
) -> AgentResult:
    """
    Spawn a Gemini CLI agent.
    
    Assumes a 'gemini' executable is available in PATH.
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("gemini-cli", model)
    
    tools_list = ["all"]
    if yolo:
        tools_list.append("yolo")

    spawn_id = log_spawn_start(
        agent="Gemini",
        model=resolved_model,
        prompt=prompt,
        tools=tools_list,
        task_summary=task_summary,
        agent_type="CLI"
    )
    
    # gemini [query] --model <m> --yolo
    cmd = ["gemini", prompt]
    
    # Always use the resolved model (default or user-provided)
    cmd.extend(["--model", resolved_model])
        
    if yolo:
        cmd.append("--yolo")
        
    cwd = working_dir or str(get_workspace_dir())
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            shell=IS_WINDOWS,
            encoding='utf-8',
            errors='replace',
        )
        
        duration = time.time() - start_time
        
        output_text = result.stdout.strip() if result.stdout else ""
        error_text = result.stderr.strip() if result.stderr else ""
        
        success = result.returncode == 0 and output_text != ""
        
        if not success and not output_text:
            error_msg = error_text or f"Exit code {result.returncode}"
            log_spawn_complete(spawn_id, False, "", duration, 0.0, error_msg)
            return AgentResult(success=False, text="", spawn_id=spawn_id, error=error_msg, provider="gemini-cli")
            
        log_spawn_complete(
            spawn_id=spawn_id,
            success=success,
            result_text=output_text,
            duration_seconds=duration,
            cost_usd=0.0,
            error=error_text if not success else None
        )
        
        return AgentResult(
            success=success,
            text=output_text,
            spawn_id=spawn_id,
            duration_ms=int(duration * 1000),
            error=error_text if not success else None,
            model=resolved_model,
            provider="gemini-cli"
        )
        
    except Exception as e:
        duration = time.time() - start_time
        log_spawn_complete(spawn_id, False, "", duration, 0.0, str(e))
        return AgentResult(success=False, text="", spawn_id=spawn_id, error=str(e), provider="gemini-cli")