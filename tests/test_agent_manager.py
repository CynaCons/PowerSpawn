"""Test Agent Manager."""
import threading
import time
from PowerSpawn.agent_manager import AgentManager

def test_manager_lifecycle():
    mgr = AgentManager()
    
    # Start
    aid = mgr.register_start("test_agent", "model-1", "do task")
    assert aid in mgr._running
    assert mgr._running[aid]["task"] == "do task"
    
    # Complete
    mgr.register_complete(aid, {"result": "done", "success": True})
    
    assert aid not in mgr._running
    assert aid in mgr._completed
    assert mgr.get_result(aid)["result"] == "done"

def test_wait_for_all():
    mgr = AgentManager()
    
    aid1 = mgr.register_start("a1", "m1", "t1")
    aid2 = mgr.register_start("a2", "m2", "t2")
    
    def complete_later(aid, delay):
        time.sleep(delay)
        mgr.register_complete(aid, {"result": f"done_{aid}"})
        
    t1 = threading.Thread(target=complete_later, args=(aid1, 0.1))
    t2 = threading.Thread(target=complete_later, args=(aid2, 0.2))
    t1.start()
    t2.start()
    
    # Block until done
    res = mgr.wait_for_all(timeout=1.0)
    
    assert res["status"] == "all_completed"
    assert len(res["results"]) == 2
    
    t1.join()
    t2.join()
