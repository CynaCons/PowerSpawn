"""
Agent Types and Common Definitions
"""

from dataclasses import dataclass, field
from typing import Optional, Any

@dataclass
class AgentResult:
    """Unified result from any agent invocation (CLI or API)."""
    success: bool
    text: str
    spawn_id: Optional[str] = None
    structured_output: Optional[dict] = None
    session_id: Optional[str] = None
    duration_ms: int = 0
    cost_usd: float = 0.0
    usage: dict = field(default_factory=dict)
    error: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    raw_response: Optional[Any] = None
