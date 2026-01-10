"""
Agent Manager

Singleton class to manage agent state and synchronization.
Replaces global state and locks with a cleaner encapsulated approach.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, List, Set, Any
from collections import OrderedDict

class AgentManager:
    def __init__(self, max_completed: int = 100):
        self._lock = threading.Lock()
        self._running: Dict[str, Dict[str, Any]] = {}
        self._completed: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._threads: Dict[str, threading.Thread] = {}
        self._events: Dict[str, threading.Event] = {}  # Events for sync
        self._max_completed = max_completed

    def register_start(self, agent_type: str, model: str, task: str) -> str:
        """Register a new agent start. Returns agent_id."""
        agent_id = uuid.uuid4().hex[:8]
        now_iso = datetime.now(timezone.utc).isoformat().split('.')[0]
        
        with self._lock:
            self._running[agent_id] = {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "model": model,
                "started_at": now_iso,
                "task": task[:100].replace('\n', ' ')
            }
            self._events[agent_id] = threading.Event()
            
        return agent_id
        
    def register_thread(self, agent_id: str, thread: threading.Thread):
        """Associate a background thread with an agent."""
        with self._lock:
            self._threads[agent_id] = thread
            
    def register_complete(self, agent_id: str, result_data: Dict[str, Any]):
        """Move agent from running to completed."""
        with self._lock:
            if agent_id in self._running:
                # Merge basic info with result data
                info = self._running.pop(agent_id)
                # Keep critical start info if not in result
                if "started_at" not in result_data:
                    result_data["started_at"] = info["started_at"]
                if "task" not in result_data:
                    result_data["task"] = info["task"]
            
            # Ensure ID matches
            result_data["agent_id"] = agent_id
            result_data["completed_at"] = datetime.now(timezone.utc).isoformat().split('.')[0]
            
            self._completed[agent_id] = result_data
            
            # Prune old history
            while len(self._completed) > self._max_completed:
                self._completed.popitem(last=False)
                
            # Clean up thread ref
            self._threads.pop(agent_id, None)
            
            # Signal completion
            if agent_id in self._events:
                self._events[agent_id].set()
                # Don't delete event yet, waiter might need it
                
    def get_running_list(self) -> List[Dict[str, Any]]:
        """Get snapshot of running agents."""
        now = datetime.now(timezone.utc)
        results = []
        with self._lock:
            for aid, info in self._running.items():
                elapsed = 0
                try:
                    start = datetime.fromisoformat(info["started_at"].replace("Z", "+00:00"))
                    elapsed = int((now - start).total_seconds())
                except Exception:
                    pass
                results.append({"id": aid, "sec": elapsed, "type": info.get("agent_type")})
        return results
        
    def get_recent_completed_ids(self, limit: int = 3) -> List[str]:
        with self._lock:
            keys = list(self._completed.keys())
            return keys[-limit:]
            
    def get_result(self, agent_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._completed.get(agent_id)
            
    def get_running_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._running.get(agent_id)

    def wait_for_all(self, timeout: float = 300) -> Dict[str, Any]:
        """
        Efficiently wait for all currently running agents.
        Returns result dict suitable for tool output.
        """
        # Snapshot current running IDs and their events
        with self._lock:
            waiting_ids = list(self._running.keys())
            events = [self._events[aid] for aid in waiting_ids if aid in self._events]
            
        if not waiting_ids:
            # Nothing running, return recent
            with self._lock:
                recent = list(self._completed.values())[-5:]
            return {
                "status": "no_agents_running",
                "recent_results": recent
            }
            
        # Wait for all events
        # Note: threading.Event.wait is blocking, but we need to wait for MULTIPLE.
        # Simple approach: wait for each sequentially with deadline
        start_time = datetime.now()
        remaining = timeout
        
        for evt in events:
            if remaining <= 0:
                break
            if evt.wait(timeout=remaining):
                # Recalculate remaining time
                elapsed = (datetime.now() - start_time).total_seconds()
                remaining = timeout - elapsed
            else:
                # Timeout happened on this event
                remaining = 0
                
        # Collection time
        with self._lock:
            results = []
            still_running = []
            
            for aid in waiting_ids:
                if aid in self._completed:
                    results.append(self._completed[aid])
                else:
                    still_running.append(aid)
                    
        if still_running:
            return {
                "status": "timeout",
                "still_running": still_running,
                "completed_results": results
            }
        else:
            return {
                "status": "all_completed",
                "results": results
            }

# Singleton
agent_manager = AgentManager()
