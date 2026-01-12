"""
Gemini API Provider (Google)
"""

import time
from typing import Optional

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from .types import AgentResult

_genai_client = None
_client_timeout = None

def _get_client(timeout: Optional[int] = None):
    global _genai_client, _client_timeout
    if _genai_client is None or _client_timeout != timeout:
        from google import genai
        api_key = settings.get_api_key("gemini")
        if not api_key:
            raise ValueError("Gemini API key not found.")
        
        http_options = None
        if timeout:
            from google.genai import types
            http_options = types.HttpOptions(timeout=timeout)
        
        _genai_client = genai.Client(api_key=api_key, http_options=http_options)
        _client_timeout = timeout
    return _genai_client

def spawn_gemini(
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
    Spawn a Gemini agent via Google GenAI SDK.
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("gemini", model)
    
    spawn_id = log_spawn_start(
        agent="Gemini",
        model=resolved_model,
        prompt=prompt,
        tools=["api"] + (["search"] if enable_search else []),
        task_summary=task_summary,
        agent_type="API"
    )
    
    try:
        client = _get_client(timeout=timeout)
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
        from google.genai import types
        
        tools = []
        if enable_search:
            tools.append(types.Tool(google_search=types.GoogleSearch()))
            
        config = types.GenerateContentConfig(
            temperature=temperature,
            tools=tools if tools else None
        )
        
        # Use Chat to support multi-turn automatic tool calling
        chat = client.chats.create(model=resolved_model, config=config)
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
        response = chat.send_message(full_prompt)
        
        duration = time.time() - start_time
        output_text = response.text if response.text else ""
        
        usage = {}
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
             usage = {
                "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0),
            }
            
        log_spawn_complete(spawn_id, True, output_text, duration, 0.0)
        
        return AgentResult(
            success=True,
            text=output_text,
            spawn_id=spawn_id,
            duration_ms=int(duration * 1000),
            usage=usage,
            model=resolved_model,
            provider="gemini"
        )
        
    except Exception as e:
        duration = time.time() - start_time
        log_spawn_complete(spawn_id, False, "", duration, 0.0, str(e))
        return AgentResult(success=False, text="", spawn_id=spawn_id, error=str(e), provider="gemini")
