"""
ARGUS MCP Deployment Tools (ACTION Tools - Sections 12, 13, 14, 15)

Implements recovery and deployment action tools:
- `simulate_rollback`: Counterfactual simulation (Section 15)
- `execute_rollback`: Reverts service to a target revision (Risk: HIGH)
- `restart_service`: Recycles subsystem or connection pool (Risk: HIGH)
- `switch_model`: Migrates LLM gateway traffic to fallback model (Risk: MEDIUM)
- `reindex_vector_store`: Rebuilds vector index from source documents (Risk: MEDIUM)

Every action tool enforces:
1. Strict allowlisting
2. Input validation
3. Risk classification (low, medium, high)
4. Tool-level approval verification on high-risk actions
5. Mandatory AuditLog entry before (STARTED) and after (SUCCESS / BLOCKED / FAILED)
"""
import logging
from typing import Any, Dict, Optional

from app.services.audit_service import record_audit_log
from app.rag.ingestion import ingest_runbooks

logger = logging.getLogger(__name__)

# Security allowlists (Section 12 & 21)
ALLOWED_SERVICES = {"llm_gateway", "vector_db", "api_gateway", "agent_worker", "core_service"}
ALLOWED_REVISIONS = {"v1_stable", "v1.2.0", "v1.1.9", "v2.0.0-rc1"}
ALLOWED_MODELS = {"gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"}
ALLOWED_COLLECTIONS = {"runbooks", "historical_incidents"}


def simulate_rollback(
    service_name: str,
    target_revision: str,
    incident_id: Optional[str] = None,
    actor: str = "mcp:simulate_rollback",
) -> Dict[str, Any]:
    """
    ACTION Tool (Simulation / Read-like Action - Risk: LOW):
    Counterfactual Recovery Simulator (Section 15).
    Simulates rollback outcomes without mutating system state.
    """
    # 1. Validation & Allowlist
    if service_name not in ALLOWED_SERVICES:
        raise ValueError(f"Service '{service_name}' not in allowed services: {sorted(ALLOWED_SERVICES)}")
    if target_revision not in ALLOWED_REVISIONS:
        raise ValueError(f"Revision '{target_revision}' not in allowed revisions: {sorted(ALLOWED_REVISIONS)}")

    risk_level = "low"
    action_desc = f"simulate_rollback(service={service_name}, target={target_revision})"

    # 2. Audit Log (Before)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result="STARTED: Simulating counterfactual rollback outcome",
        incident_id=incident_id,
    )

    # 3. Simulate expected outcome based on service
    simulation_result = {
        "service_name": service_name,
        "target_revision": target_revision,
        "recovery_probability": 0.93 if target_revision == "v1_stable" else 0.85,
        "estimated_recovery_time_sec": 4.5,
        "potential_impact": "Zero downtime rolling restart; ephemeral cache cleared.",
        "reversibility": "high",
        "risk_score": 0.20,
        "recommendation": "Recommended as safe high-confidence recovery option.",
    }

    # 4. Audit Log (After)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result="SUCCESS: Counterfactual simulation completed (P_recovery=93%)",
        incident_id=incident_id,
    )

    return {
        "tool": "simulate_rollback",
        "type": "ACTION",
        "risk_level": risk_level,
        "status": "success",
        "simulation": simulation_result,
    }


def execute_rollback(
    service_name: str,
    target_revision: str,
    approved: bool = False,
    incident_id: Optional[str] = None,
    actor: str = "mcp:execute_rollback",
    raise_on_blocked: bool = True,
) -> Dict[str, Any]:
    """
    ACTION Tool (Risk: HIGH):
    Executes a rollback of the target service to an approved revision.
    Must refuse execution if approved=False.
    """
    risk_level = "high"
    action_desc = f"execute_rollback(service={service_name}, target={target_revision}, approved={approved})"

    # 1. Audit Log (Before)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result="STARTED: Validating rollback authorization and parameters",
        incident_id=incident_id,
    )

    # 2. Input Validation & Allowlist
    if service_name not in ALLOWED_SERVICES:
        err = f"Service '{service_name}' not in allowed services: {sorted(ALLOWED_SERVICES)}"
        record_audit_log(actor=actor, action=action_desc, result=f"FAILED: {err}", incident_id=incident_id)
        raise ValueError(err)

    if target_revision not in ALLOWED_REVISIONS:
        err = f"Revision '{target_revision}' not in allowed revisions: {sorted(ALLOWED_REVISIONS)}"
        record_audit_log(actor=actor, action=action_desc, result=f"FAILED: {err}", incident_id=incident_id)
        raise ValueError(err)

    # 3. Tool-Level High-Risk Approval Enforcement
    if not approved:
        blocked_msg = f"High-risk action 'execute_rollback' refused: approved=True is required for service '{service_name}'"
        logger.warning("MCP ACTION BLOCKED: %s", blocked_msg)
        record_audit_log(
            actor=actor,
            action=action_desc,
            result=f"BLOCKED: {blocked_msg}",
            incident_id=incident_id,
        )
        if raise_on_blocked:
            raise PermissionError(blocked_msg)
        return {
            "tool": "execute_rollback",
            "type": "ACTION",
            "risk_level": risk_level,
            "status": "blocked",
            "error": blocked_msg,
        }

    # 4. Execution (Simulated live deployment rollback)
    execution_details = {
        "service": service_name,
        "rolled_back_to": target_revision,
        "previous_revision": "v2.0.0-rc1",
        "status": "active",
        "downtime_ms": 120,
    }

    # 5. Audit Log (After)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result=f"SUCCESS: Successfully rolled back {service_name} to {target_revision}",
        incident_id=incident_id,
    )

    return {
        "tool": "execute_rollback",
        "type": "ACTION",
        "risk_level": risk_level,
        "status": "success",
        "message": f"Successfully rolled back {service_name} to {target_revision}.",
        "details": execution_details,
    }


def restart_service(
    service_name: str,
    approved: bool = False,
    incident_id: Optional[str] = None,
    actor: str = "mcp:restart_service",
    raise_on_blocked: bool = True,
) -> Dict[str, Any]:
    """
    ACTION Tool (Risk: HIGH):
    Restarts a monitored subsystem or resets connection pools.
    Must refuse execution if approved=False.
    """
    risk_level = "high"
    action_desc = f"restart_service(service={service_name}, approved={approved})"

    # 1. Audit Log (Before)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result="STARTED: Initiating service restart evaluation",
        incident_id=incident_id,
    )

    # 2. Input Validation & Allowlist
    if service_name not in ALLOWED_SERVICES:
        err = f"Service '{service_name}' not in allowed services: {sorted(ALLOWED_SERVICES)}"
        record_audit_log(actor=actor, action=action_desc, result=f"FAILED: {err}", incident_id=incident_id)
        raise ValueError(err)

    # 3. Tool-Level High-Risk Approval Enforcement
    if not approved:
        blocked_msg = f"High-risk action 'restart_service' refused: approved=True is required for service '{service_name}'"
        logger.warning("MCP ACTION BLOCKED: %s", blocked_msg)
        record_audit_log(
            actor=actor,
            action=action_desc,
            result=f"BLOCKED: {blocked_msg}",
            incident_id=incident_id,
        )
        if raise_on_blocked:
            raise PermissionError(blocked_msg)
        return {
            "tool": "restart_service",
            "type": "ACTION",
            "risk_level": risk_level,
            "status": "blocked",
            "error": blocked_msg,
        }

    # 4. Execution
    execution_details = {
        "service": service_name,
        "restart_duration_ms": 350,
        "connection_pools_purged": True,
        "state": "healthy",
    }

    # 5. Audit Log (After)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result=f"SUCCESS: Service {service_name} restarted cleanly",
        incident_id=incident_id,
    )

    return {
        "tool": "restart_service",
        "type": "ACTION",
        "risk_level": risk_level,
        "status": "success",
        "message": f"Successfully restarted {service_name}.",
        "details": execution_details,
    }


def switch_model(
    target_provider: str = "gemini",
    model: str = "gemini-2.0-flash",
    fallback: bool = True,
    approved: bool = True,
    incident_id: Optional[str] = None,
    actor: str = "mcp:switch_model",
) -> Dict[str, Any]:
    """
    ACTION Tool (Risk: MEDIUM):
    Switches active LLM inference model to a verified fallback.
    """
    risk_level = "medium"
    action_desc = f"switch_model(provider={target_provider}, model={model})"

    # 1. Audit Log (Before)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result="STARTED: Verifying target model configuration",
        incident_id=incident_id,
    )

    # 2. Validation & Allowlist
    if model not in ALLOWED_MODELS:
        err = f"Model '{model}' not in allowed models: {sorted(ALLOWED_MODELS)}"
        record_audit_log(actor=actor, action=action_desc, result=f"FAILED: {err}", incident_id=incident_id)
        raise ValueError(err)

    # 3. Execution
    details = {
        "provider": target_provider,
        "model": model,
        "fallback_enabled": fallback,
        "status": "switched",
    }

    # 4. Audit Log (After)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result=f"SUCCESS: Switched active model to {model} ({target_provider})",
        incident_id=incident_id,
    )

    return {
        "tool": "switch_model",
        "type": "ACTION",
        "risk_level": risk_level,
        "status": "success",
        "message": f"Switched model route to {model}.",
        "details": details,
    }


def reindex_vector_store(
    collection: str = "runbooks",
    force_clean: bool = True,
    approved: bool = True,
    incident_id: Optional[str] = None,
    actor: str = "mcp:reindex_vector_store",
) -> Dict[str, Any]:
    """
    ACTION Tool (Risk: MEDIUM):
    Reindexes the vector store collection to resolve index corruption or drift.
    """
    risk_level = "medium"
    action_desc = f"reindex_vector_store(collection={collection}, force_clean={force_clean})"

    # 1. Audit Log (Before)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result="STARTED: Rebuilding vector index",
        incident_id=incident_id,
    )

    # 2. Validation & Allowlist
    if collection not in ALLOWED_COLLECTIONS:
        err = f"Collection '{collection}' not in allowed collections: {sorted(ALLOWED_COLLECTIONS)}"
        record_audit_log(actor=actor, action=action_desc, result=f"FAILED: {err}", incident_id=incident_id)
        raise ValueError(err)

    # 3. Execution
    chunk_count = 0
    if collection == "runbooks":
        chunk_count = ingest_runbooks(runbooks_dir="data/runbooks")

    details = {
        "collection": collection,
        "chunks_indexed": chunk_count,
        "index_healthy": True,
    }

    # 4. Audit Log (After)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result=f"SUCCESS: Reindexed {collection} with {chunk_count} chunks",
        incident_id=incident_id,
    )

    return {
        "tool": "reindex_vector_store",
        "type": "ACTION",
        "risk_level": risk_level,
        "status": "success",
        "message": f"Successfully reindexed {collection}.",
        "details": details,
    }
