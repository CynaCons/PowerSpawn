"""
Mistral API Provider
"""

import time
from typing import Optional, Any

from ..logger import log_spawn_start, log_spawn_complete
from ..config import settings
from .types import AgentResult

_mistral_client = None
_client_timeout = None

def _get_client(timeout: Optional[int] = None):
    global _mistral_client, _client_timeout
    if _mistral_client is None or _client_timeout != timeout:
        from mistralai import Mistral
        api_key = settings.get_api_key("mistral")
        if not api_key:
            raise ValueError("Mistral API key not found.")
        
        # Convert timeout from seconds to milliseconds for Mistral
        timeout_ms = timeout * 1000 if timeout else None
        _mistral_client = Mistral(api_key=api_key, timeout_ms=timeout_ms)
        _client_timeout = timeout
    return _mistral_client

def extract_mistral_text(response: Any) -> str:
    """
    Pure function to extract text from Mistral response.
    Isolates complex parsing logic.
    """
    output_text = ""
    if not hasattr(response, 'outputs') or not response.outputs:
        return ""
        
    for output in response.outputs:
        # Check type safely
        output_type = getattr(output, 'type', '')
        if output_type != 'message.output':
            continue
            
        content = getattr(output, 'content', None)
        if content is None:
            continue
            
        if isinstance(content, str):
            output_text = content
        elif isinstance(content, list):
            # Handle list of content blocks
            text_parts = []
            for block in content:
                if hasattr(block, 'text'):
                    text_parts.append(block.text)
                elif hasattr(block, 'type') and getattr(block, 'type', '') == 'text':
                    text_parts.append(getattr(block, 'text', ''))
            output_text = "".join(text_parts)
        else:
            output_text = str(content)
        
        # Stop after finding the first message output
        break
        
    return output_text

def spawn_mistral(
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
    Spawn a Mistral agent via Mistral AI Agents API.
    """
    start_time = time.time()
    resolved_model = settings.get_model_alias("mistral", model)
    
    spawn_id = log_spawn_start(
        agent="Mistral",
        model=resolved_model,
        prompt=prompt,
        tools=["api"] + (["search"] if enable_search else []),
        task_summary=task_summary,
        agent_type="API"
    )
    
    try:
        client = _get_client(timeout=timeout)
        
        tools = []
        if enable_search:
            tools.append({"type": "web_search"})
            
        # Create ephemeral agent
        agent = client.beta.agents.create(
            model=resolved_model,
            name="PowerSpawn Agent",
            description="Agent",
            instructions=system_prompt or "You are a helpful assistant.",
            tools=tools if tools else None,
            completion_args={"temperature": temperature}
        )
        
        response = client.beta.conversations.start(
            agent_id=agent.id,
            inputs=prompt,
            store=False
        )
        
        duration = time.time() - start_time
        output_text = extract_mistral_text(response)
        
        usage = {}
        if hasattr(response, 'usage') and response.usage:
             usage = {
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0),
            }
            
        log_spawn_complete(spawn_id, True, output_text, duration, 0.0)
        
        return AgentResult(
            success=True,
            text=output_text,
            spawn_id=spawn_id,
            duration_ms=int(duration * 1000),
            usage=usage,
            model=resolved_model,
            provider="mistral"
        )
        
    except Exception as e:
        duration = time.time() - start_time
        log_spawn_complete(spawn_id, False, "", duration, 0.0, str(e))
        return AgentResult(success=False, text="", spawn_id=spawn_id, error=str(e), provider="mistral")
