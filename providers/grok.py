"""
Grok API Provider (X.AI)
"""

import time
from typing import Optional

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from .types import AgentResult

_openai_client = None

def _get_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        api_key = settings.get_api_key("grok")
        if not api_key:
            raise ValueError("Grok API key not found.")
        _openai_client = OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=api_key
        )
    return _openai_client

def spawn_grok(
    prompt: str,
    *,
    model: str = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    timeout: int = 300,
    task_summary: Optional[str] = None,
    enable_search: bool = True,
) -> AgentResult:
    """
    Spawn a Grok agent via X.ai API.
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("grok", model)
    
    spawn_id = log_spawn_start(
        agent="Grok",
        model=resolved_model,
        prompt=prompt,
        tools=["api"] + (["search"] if enable_search else []),
        task_summary=task_summary,
        agent_type="API"
    )
    
    try:
        client = _get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        request_kwargs = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "timeout": timeout,
        }
        
        if enable_search:
            request_kwargs["extra_body"] = {
                "search_parameters": {
                    "mode": "auto",
                    "return_citations": True
                }
            }
            
        response = client.chat.completions.create(**request_kwargs)
        duration = time.time() - start_time
        
        output_text = response.choices[0].message.content if response.choices else ""
        
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
        log_spawn_complete(spawn_id, True, output_text, duration, 0.0)
        
        return AgentResult(
            success=True,
            text=output_text,
            spawn_id=spawn_id,
            duration_ms=int(duration * 1000),
            usage=usage,
            model=resolved_model,
            provider="grok"
        )
        
    except Exception as e:
        duration = time.time() - start_time
        log_spawn_complete(spawn_id, False, "", duration, 0.0, str(e))
        return AgentResult(success=False, text="", spawn_id=spawn_id, error=str(e), provider="grok")
