# backend/tests/test_latency_agent.py
import time
import math
from backend.agents.latency_agent import LatencyAgent

def test_latency_agent_records_and_reports_ms():
    la = LatencyAgent(budget_ms=450)

    # record 0.2 sec (200 ms) and 0.5 sec (500 ms)
    la.record(0.2)
    la.record(0.5)

    snap = la.snapshot()
    assert snap.count == 2
    assert math.isclose(snap.p50_ms, 200.0, rel_tol=1e-2) or math.isclose(snap.p50_ms, 500.0, rel_tol=1e-2)
    assert 200.0 <= snap.p95_ms <= 500.0

    # Budget should fail only if p95 > 450 ms
    assert la.over_budget() is True  # p95 ~ 500 ms > 450 ms

def test_latency_agent_record_ms_helper():
    la = LatencyAgent(budget_ms=300)
    la.record_ms(150)  # store as 0.150 seconds
    la.record_ms(250)

    snap = la.snapshot()
    assert all(100.0 <= val <= 300.0 for val in (snap.p50_ms, snap.p95_ms))
    assert la.over_budget() is False

def test_latency_agent_timeit_context_manager():
    la = LatencyAgent()
    with la.timeit():
        time.sleep(0.05)  # ~50 ms

    snap = la.snapshot()
    assert snap.count == 1
    assert 40.0 <= snap.p50_ms <= 100.0  # allow jitter
