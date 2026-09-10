"""
ARGUS Diagnosis Agent (Phase 5 - Sections 10, 11, 37.1)

Investigates root cause by synthesizing telemetry evidence with retrieved RAG runbooks.
Calls Google Gemini (ChatGoogleGenerativeAI) with structured output parsing when configured,
and falls back to rule-based runbook diagnosis per Section 32 when offline.
"""
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import get_settings
from app.graph.state import ArgusState
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)
settings = get_settings()


class DiagnosisSchema(BaseModel):
    """Structured output schema for LLM-based diagnosis."""
    root_cause: str = Field(
        ...,
        description="Detailed technical root cause citing specific evidence and runbook matches.",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Diagnostic confidence score.")
    cited_evidence: List[str] = Field(
        default_factory=list,
        description="List of specific metrics and retrieved runbook sections supporting the diagnosis.",
    )


def _llm_diagnose(
    failure_type: str,
    evidence: List[str],
    metrics: Dict[str, float],
    runbooks: List[Dict[str, Any]],
) -> Optional[DiagnosisSchema]:
    """
    Attempts LLM diagnosis via Google Gemini using structured output parsing.
    """
    if not (settings.GOOGLE_API_KEY and (settings.LLM_PROVIDER or "gemini") == "gemini"):
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.prompts import ChatPromptTemplate

        llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL or "gemini-3.6-flash",
            google_api_key=settings.GOOGLE_API_KEY,
        )

        structured_llm = llm.with_structured_output(DiagnosisSchema, method="json_mode")

        runbook_context = "\n\n".join(
            [f"--- Runbook Source: {rb['source']} ({rb['document']}) ---\n{rb['chunk']}" for rb in runbooks]
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are ARGUS Chief Reliability Engineer. Diagnose the root cause of the incident.\n"
                "CRITICAL RULES:\n"
                "1. You must cite specific retrieved evidence from the provided runbooks and telemetry.\n"
                "2. Never claim root causes unsupported by evidence.\n"
                "3. Return a structured diagnosis with root_cause, confidence, and cited_evidence.",
            ),
            (
                "user",
                "Incident Telemetry:\n"
                "Failure Type: {failure_type}\n"
                "Evidence: {evidence}\n"
                "Metrics: {metrics}\n\n"
                "Retrieved Knowledge Runbooks:\n{runbook_context}\n\n"
                "Provide your root cause diagnosis.",
            ),
        ])

        chain = prompt | structured_llm
        result = chain.invoke({
            "failure_type": failure_type,
            "evidence": "; ".join(evidence),
            "metrics": str(metrics),
            "runbook_context": runbook_context,
        })
        return result
    except Exception as e:
        logger.warning("LLM diagnosis invocation failed (%s); switching to fallback mode.", e)
        return None


def _fallback_diagnose(
    failure_type: str,
    evidence: List[str],
    runbooks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Rule-based deterministic fallback diagnosis grounded in retrieved RAG runbooks (Section 32).
    """
    if runbooks:
        top_rb = runbooks[0]
        # Look for the Root Cause section in the chunk or summarize
        root_cause = (
            f"Grounding from {top_rb['source']}: Primary failure mode identified as {failure_type}. "
            f"Observed evidence indicates {'; '.join(evidence[:3])}. "
            f"Reference runbook indicates root cause stems from: {top_rb['chunk'][:280]}..."
        )
        cited = evidence + [f"Runbook reference: {top_rb['source']} (relevance: {top_rb['relevance_score']:.2f})"]
    else:
        root_cause = (
            f"Diagnostic Fallback: System identified {failure_type} based on telemetry: {'; '.join(evidence)}. "
            f"No specific runbook match found."
        )
        cited = evidence

    return {
        "root_cause": root_cause,
        "confidence": 0.88,
        "cited_evidence": cited,
    }


def diagnosis_agent(state: ArgusState) -> Dict[str, Any]:
    """
    Executes root cause diagnosis grounded in RAG retrieval and LLM structured synthesis.
    """
    failure_type = state.get("failure_type", "UNKNOWN")
    evidence = state.get("evidence", [])
    metrics = state.get("metrics", {})
    history_trace = list(state.get("history_trace", []))
    history_trace.append("DiagnosisAgent: investigating root cause and querying RAG")

    # 1. Retrieve relevant operational runbooks from Phase 4 vector store
    query = f"{failure_type} {', '.join(evidence)}"
    retrieved_runbooks = retrieve(query=query, k=3, failure_type_filter=None)

    # 2. Attempt LLM diagnosis with Gemini, with graceful fallback to RAG runbook extraction
    llm_result = _llm_diagnose(failure_type, evidence, metrics, retrieved_runbooks)

    logs = list(state.get("logs", []))

    if llm_result:
        root_cause = llm_result.root_cause
        diag_conf = llm_result.confidence
        logs.append(f"[DiagnosisAgent] LLM Diagnosis completed with {diag_conf:.0%} confidence.")
    else:
        fallback = _fallback_diagnose(failure_type, evidence, retrieved_runbooks)
        root_cause = fallback["root_cause"]
        diag_conf = fallback["confidence"]
        logs.append(f"[DiagnosisAgent] Diagnostic completed via RAG runbook match ({diag_conf:.0%} confidence).")

    return {
        "root_cause": root_cause,
        "retrieved_runbooks": retrieved_runbooks,
        "failure_confidence": max(state.get("failure_confidence", 0.0), diag_conf),
        "logs": logs,
        "history_trace": history_trace,
    }
