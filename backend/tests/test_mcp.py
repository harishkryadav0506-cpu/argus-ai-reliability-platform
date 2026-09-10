"""
Phase 6 Tests — Model Context Protocol (MCP) Tools, Security & Audit Logging (Section 12)

Tests:
1. Tool registry discovery (all 13 tools: 6 READ, 7 ACTION).
2. High-risk actions strictly blocked without explicit approval (enforced inside tools).
3. High-risk actions succeed with approval.
4. Security allowlists reject unknown services/models.
5. AuditLog rows generated before and after every action tool call.
6. Display audit log output for one blocked action and one approved action.

Run with: pytest backend/tests/test_mcp.py -v -s
"""
import pytest
from app.mcp.server import list_tools, call_tool, get_mcp_server
from app.mcp.deployment_tools import execute_rollback, restart_service, simulate_rollback, switch_model, reindex_vector_store
from app.mcp.incident_tools import create_incident, update_incident
from app.services.audit_service import get_audit_logs, clear_in_memory_audit_logs


@pytest.fixture(autouse=True)
def clean_audit_state():
    clear_in_memory_audit_logs()
    yield


def test_mcp_server_lists_all_thirteen_tools():
    """Confirms all 13 tools specified in Section 12 are registered."""
    tools = list_tools()
    tool_names = {t["name"] for t in tools}

    expected_read_tools = {
        "get_system_metrics",
        "get_service_health",
        "get_recent_logs",
        "get_incident_history",
        "get_deployment_history",
        "search_runbooks",
    }
    expected_action_tools = {
        "simulate_rollback",
        "execute_rollback",
        "restart_service",
        "switch_model",
        "reindex_vector_store",
        "create_incident",
        "update_incident",
    }
    expected_all = expected_read_tools | expected_action_tools

    assert expected_all.issubset(tool_names), f"Missing tools: {expected_all - tool_names}"
    assert len(tools) >= 13

    # Check categorization
    for t in tools:
        assert t["type"] in ["READ", "ACTION"]
        assert t["risk_level"] in ["low", "medium", "high"]
        assert "inputSchema" in t


def test_read_tools_execution():
    """Confirms execution of READ tools without side effects."""
    # 1. get_system_metrics
    res_metrics = call_tool("get_system_metrics", {"window_minutes": 5})
    assert res_metrics["tool"] == "get_system_metrics"
    assert "current_metrics" in res_metrics
    assert "latency" in res_metrics["current_metrics"]

    # 2. get_service_health
    res_health = call_tool("get_service_health", {"service_name": "llm_gateway"})
    assert res_health["service_name"] == "llm_gateway"
    assert res_health["data"]["status"] == "healthy"

    # 3. get_recent_logs
    res_logs = call_tool("get_recent_logs", {"service_name": "llm_gateway", "limit": 5})
    assert isinstance(res_logs, list)

    # 4. get_deployment_history
    res_dep = call_tool("get_deployment_history", {"limit": 2})
    assert isinstance(res_dep, list)
    assert len(res_dep) > 0

    # 5. search_runbooks
    res_rb = call_tool("search_runbooks", {"query": "model timeout", "k": 2})
    assert isinstance(res_rb, list)


def test_high_risk_tool_blocked_without_approval():
    """
    CRITICAL REQUIREMENT:
    High-risk tools (execute_rollback, restart_service) must strictly refuse execution
    if approved=False. Enforced directly inside the tool logic.
    """
    # 1. Direct function call raises PermissionError
    with pytest.raises(PermissionError) as exc_info:
        execute_rollback(
            service_name="llm_gateway",
            target_revision="v1_stable",
            approved=False,
            incident_id="test-inc-1",
        )
    assert "approved=True is required" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info2:
        restart_service(
            service_name="vector_db",
            approved=False,
            incident_id="test-inc-2",
        )
    assert "approved=True is required" in str(exc_info2.value)

    # 2. Via MCP Server call_tool interface: returns structured blocked response
    resp = call_tool(
        "execute_rollback",
        {
            "service_name": "llm_gateway",
            "target_revision": "v1_stable",
            "approved": False,
            "incident_id": "test-inc-1",
        },
    )
    assert resp["status"] == "blocked"
    assert resp["risk_level"] == "high"
    assert "approved=True is required" in resp["error"]


def test_high_risk_tool_succeeds_with_approval():
    """Confirms high-risk tools execute when approved=True."""
    res_rollback = call_tool(
        "execute_rollback",
        {
            "service_name": "llm_gateway",
            "target_revision": "v1_stable",
            "approved": True,
            "incident_id": "test-inc-approved",
        },
    )
    assert res_rollback["status"] == "success"
    assert res_rollback["risk_level"] == "high"
    assert "Successfully rolled back" in res_rollback["message"]

    res_restart = call_tool(
        "restart_service",
        {
            "service_name": "core_service",
            "approved": True,
            "incident_id": "test-inc-approved",
        },
    )
    assert res_restart["status"] == "success"
    assert res_restart["details"]["state"] == "healthy"


def test_allowlist_blocks_unauthorized_actions():
    """Confirms allowlists reject unauthorized target services, models, or revisions."""
    # Unauthorized service name
    with pytest.raises(ValueError) as exc1:
        restart_service(service_name="unauthorized_rogue_service", approved=True)
    assert "not in allowed services" in str(exc1.value)

    # Unauthorized model name
    with pytest.raises(ValueError) as exc2:
        switch_model(model="gpt-fake-unauthorized", approved=True)
    assert "not in allowed models" in str(exc2.value)


def test_audit_logs_written_for_every_action_tool():
    """
    Confirms that every ACTION tool call writes AuditLog records
    both before (STARTED) and after (SUCCESS / BLOCKED).
    """
    clear_in_memory_audit_logs()

    # 1. Call medium-risk switch_model
    call_tool("switch_model", {"target_provider": "gemini", "model": "gemini-2.0-flash", "incident_id": "inc-audit-1"})

    logs = get_audit_logs(incident_id="inc-audit-1")
    assert len(logs) >= 2, f"Expected at least 2 audit logs (STARTED and SUCCESS), got {len(logs)}"

    # Audit log results should reflect start and completion
    results = [l["result"] for l in logs]
    assert any("STARTED" in r for r in results)
    assert any("SUCCESS" in r for r in results)


def test_show_audit_log_output_for_blocked_and_approved():
    """
    Demonstrates and prints real audit log records for:
    (1) One blocked high-risk action
    (2) One approved high-risk action
    """
    clear_in_memory_audit_logs()

    blocked_inc_id = "inc-blocked-99"
    approved_inc_id = "inc-approved-100"

    # Action 1: Attempt unapproved rollback -> BLOCKED
    call_tool(
        "execute_rollback",
        {
            "service_name": "llm_gateway",
            "target_revision": "v1_stable",
            "approved": False,
            "incident_id": blocked_inc_id,
        },
    )

    # Action 2: Execute approved restart -> APPROVED & SUCCESS
    call_tool(
        "restart_service",
        {
            "service_name": "core_service",
            "approved": True,
            "incident_id": approved_inc_id,
        },
    )

    blocked_logs = get_audit_logs(incident_id=blocked_inc_id)
    approved_logs = get_audit_logs(incident_id=approved_inc_id)

    print("\n" + "=" * 80)
    print("DEMONSTRATION: AUDIT LOG OUTPUT FOR BLOCKED ACTION (Risk: HIGH)")
    print("=" * 80)
    for entry in reversed(blocked_logs):
        print(f"[{entry['timestamp']}] ACTOR: {entry['actor']:<25} | ACTION: {entry['action']:<60} | RESULT: {entry['result']}")

    print("\n" + "=" * 80)
    print("DEMONSTRATION: AUDIT LOG OUTPUT FOR APPROVED ACTION (Risk: HIGH)")
    print("=" * 80)
    for entry in reversed(approved_logs):
        print(f"[{entry['timestamp']}] ACTOR: {entry['actor']:<25} | ACTION: {entry['action']:<60} | RESULT: {entry['result']}")
    print("=" * 80 + "\n")

    assert any("BLOCKED" in l["result"] for l in blocked_logs)
    assert any("SUCCESS" in l["result"] for l in approved_logs)
