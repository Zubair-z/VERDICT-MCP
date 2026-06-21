"""Integration test for Verdict MCP server."""
import subprocess
import sys
import json
import time
import threading
import queue


def test():
    p = subprocess.Popen(
        [sys.executable, "-m", "verdict_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=r"E:\MCP\verdict_mcp",
    )

    stdout_queue = queue.Queue()
    def read_stdout():
        for line in iter(p.stdout.readline, b''):
            stdout_queue.put(line.decode().rstrip())
        stdout_queue.put(None)
    threading.Thread(target=read_stdout, daemon=True).start()

    nxt = 1
    def send(method, params=None):
        nonlocal nxt
        msg = {"jsonrpc": "2.0", "id": nxt, "method": method}
        if params:
            msg["params"] = params
        nxt += 1
        p.stdin.write((json.dumps(msg) + "\n").encode())
        p.stdin.flush()

    def recv(timeout=15):
        try:
            line = stdout_queue.get(timeout=timeout)
            return json.loads(line)
        except queue.Empty:
            raise TimeoutError(f"No response after {timeout}s")

    send("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0"}})
    resp = recv()
    assert resp["result"]["serverInfo"]["name"] == "Verdict"
    print(f"[PASS] Initialize: {resp['result']['serverInfo']['name']}")

    p.stdin.write((json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n").encode())
    p.stdin.flush()
    time.sleep(0.3)

    send("tools/list")
    resp = recv()
    tools = [t["name"] for t in resp["result"]["tools"]]
    expected = ["initialize_project_plan", "submit_task_for_audit", "enforce_ui_standards", "run_strict_test_suite", "invalidate_cache"]
    assert set(tools) == set(expected), f"Tools mismatch: {tools}"
    print(f"[PASS] Tools ({len(tools)}): {tools}")

    send("resources/list")
    resp = recv()
    resources = [r["uri"] for r in resp["result"]["resources"]]
    assert len(resources) == 3
    print(f"[PASS] Resources ({len(resources)}): {resources}")

    send("tools/call", {"name": "initialize_project_plan",
                        "arguments": {"plan_file_path": r"E:\MCP\verdict_mcp\plan.md"}})
    resp = recv()
    plan = resp["result"]["content"][0]["text"]
    pdata = json.loads(plan) if isinstance(plan, str) else plan
    pdata = pdata if isinstance(pdata, dict) else resp["result"].get("structuredContent", pdata)
    assert pdata.get("success") is True
    print(f"[PASS] Plan initialized: {pdata['task_count']} tasks")

    send("resources/read", {"uri": "project://master_plan"})
    resp = recv()
    master = json.loads(resp["result"]["contents"][0]["text"])
    assert master["initialized"] is True
    assert len(master["tasks"]) == 4
    print(f"[PASS] Master plan: {len(master['tasks'])} tasks")

    send("resources/read", {"uri": "project://task/TASK_001"})
    resp = recv()
    task = json.loads(resp["result"]["contents"][0]["text"])
    assert task["task_id"] == "TASK_001"
    assert task["state"] == "PENDING"
    print(f"[PASS] Task resource: {task['task_id']} = {task['title']}")

    send("resources/read", {"uri": "project://ui_style_guide"})
    resp = recv()
    guide = json.loads(resp["result"]["contents"][0]["text"])
    assert "design_tokens" in guide
    print(f"[PASS] UI style guide: {len(guide['design_tokens'])} token categories")

    send("resources/read", {"uri": "project://coverage_report"})
    resp = recv()
    print(f"[PASS] Coverage report accessible")

    send("tools/call", {"name": "submit_task_for_audit",
                        "arguments": {"task_id": "TASK_001", "file_paths": ["nope.py"]}})
    resp = recv()
    audit = resp["result"]["content"][0]["text"]
    adata = json.loads(audit) if isinstance(audit, str) else audit
    adata = adata if isinstance(adata, dict) else resp["result"].get("structuredContent", adata)
    assert adata.get("success") is False
    print(f"[PASS] Audit rejects nonexistent file")

    send("prompts/list")
    resp = recv()
    prompts = [p["name"] for p in resp["result"]["prompts"]]
    expected_pt = ["validation_lifecycle", "audit_requirements", "ui_standards_requirements", "test_requirements"]
    for ep in expected_pt:
        assert ep in prompts, f"Missing prompt: {ep}"
    print(f"[PASS] Prompts ({len(prompts)}): {prompts}")

    send("tools/call", {"name": "invalidate_cache", "arguments": {}})
    resp = recv()
    print(f"[PASS] Cache invalidated")

    p.terminate()
    p.wait()
    print("\n=== ALL TESTS PASSED ===")
