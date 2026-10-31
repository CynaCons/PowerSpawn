"""
Persistent Agent Module

Manages long-lived agents that can receive multiple messages
while maintaining conversation context.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from collections import OrderedDict


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PersistentAgent:
    """
    A long-lived agent that maintains conversation context.

    For CLI providers with native resume (Claude, Codex, Copilot, Gemini CLI),
    we store the session_id and use the provider's resume capability.

    For API providers (Grok, Gemini API, Mistral), we replay
    conversation history on each call.
    """
    id: str
    provider: str
    role: Optional[str] = None  # Human-readable role name
    personality: Optional[str] = None  # System prompt
    session_id: Optional[str] = None  # Provider's native session ID
    model: Optional[str] = None
    conversation_history: List[ConversationTurn] = field(default_factory=list)
    status: str = "idle"  # "idle", "busy", "terminated"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_cost_usd: float = 0.0
    total_turns: int = 0

    def is_terminated(self) -> bool:
        """Check if agent has been terminated."""
        return self.status == "terminated"

    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    def add_turn(self, role: str, content: str):
        """Add a conversation turn."""
        self.conversation_history.append(ConversationTurn(role=role, content=content))
        self.total_turns += 1
        self.touch()

    def get_history_for_replay(self) -> List[Dict[str, str]]:
        """Get conversation history in format suitable for API replay."""
        messages = []
        if self.personality:
            messages.append({"role": "system", "content": self.personality})
        for turn in self.conversation_history:
            messages.append({"role": turn.role, "content": turn.content})
        return messages

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for MCP response."""
        return {
            "id": self.id,
            "provider": self.provider,
            "role": self.role,
            "model": self.model,
            "status": self.status,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "total_turns": self.total_turns,
            "total_cost_usd": self.total_cost_usd,
            "history_length": len(self.conversation_history)
        }


class PersistentAgentRegistry:
    """
    Registry for persistent agents.

    Thread-safe singleton that manages agent lifecycle.
    """

    def __init__(self, max_agents: int = 20):
        self._lock = threading.Lock()
        self._agents: OrderedDict[str, PersistentAgent] = OrderedDict()
        self._max_agents = max_agents

    def create(
        self,
        provider: str,
        role: Optional[str] = None,
        personality: Optional[str] = None,
        model: Optional[str] = None,
    ) -> PersistentAgent:
        """Create a new persistent agent."""
        agent_id = f"pa_{uuid.uuid4().hex[:8]}"

        agent = PersistentAgent(
            id=agent_id,
            provider=provider,
            role=role,
            personality=personality,
            model=model,
        )

        with self._lock:
            # Enforce max agents limit (FIFO eviction)
            while len(self._agents) >= self._max_agents:
                oldest_id = next(iter(self._agents))
                del self._agents[oldest_id]

            self._agents[agent_id] = agent

        return agent

    def get(self, agent_id: str) -> Optional[PersistentAgent]:
        """Get an agent by ID."""
        with self._lock:
            return self._agents.get(agent_id)

    def update_session_id(self, agent_id: str, session_id: str):
        """Update the provider session ID for an agent."""
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].session_id = session_id
                self._agents[agent_id].touch()

    def set_status(self, agent_id: str, status: str):
        """Update agent status."""
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].status = status
                self._agents[agent_id].touch()

    def add_cost(self, agent_id: str, cost_usd: float):
        """Add to agent's total cost."""
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].total_cost_usd += cost_usd

    def terminate(self, agent_id: str) -> bool:
        """Terminate an agent."""
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].status = "terminated"
                return True
            return False

    def delete(self, agent_id: str) -> bool:
        """Permanently delete an agent."""
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                return True
            return False

    def list_all(self) -> List[Dict[str, Any]]:
        """List all agents."""
        with self._lock:
            return [agent.to_dict() for agent in self._agents.values()]

    def list_active(self) -> List[Dict[str, Any]]:
        """List only non-terminated agents."""
        with self._lock:
            return [
                agent.to_dict()
                for agent in self._agents.values()
                if agent.status != "terminated"
            ]


# Singleton instance
persistent_registry = PersistentAgentRegistry()
