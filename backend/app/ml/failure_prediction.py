"""
ARGUS ML Failure Classification (Phase 3 - Section 9)

Classifies detected anomalies into the 10 canonical categories from Section 9:
1. LLM_FAILURE
2. RAG_DEGRADATION
3. RETRIEVAL_FAILURE
4. TOOL_FAILURE
5. API_FAILURE
6. LATENCY_SPIKE
7. COST_SPIKE
8. AGENT_LOOP
9. DATA_QUALITY
10. UNKNOWN

Returns category + confidence + evidence list per Section 9.
Does NOT make LLM calls at this phase.
"""
from typing import Any, Dict, List, Optional


class FailureCategory:
    LLM_FAILURE = "LLM_FAILURE"
    RAG_DEGRADATION = "RAG_DEGRADATION"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    API_FAILURE = "API_FAILURE"
    LATENCY_SPIKE = "LATENCY_SPIKE"
    COST_SPIKE = "COST_SPIKE"
    AGENT_LOOP = "AGENT_LOOP"
    DATA_QUALITY = "DATA_QUALITY"
    UNKNOWN = "UNKNOWN"

    ALL = [
        LLM_FAILURE,
        RAG_DEGRADATION,
        RETRIEVAL_FAILURE,
        TOOL_FAILURE,
        API_FAILURE,
        LATENCY_SPIKE,
        COST_SPIKE,
        AGENT_LOOP,
        DATA_QUALITY,
        UNKNOWN,
    ]


class FailureClassifier:
    """
    Classifies system and agentic failures from metric anomalies using
    evidence-backed signature analysis.
    """

    def classify(
        self,
        metrics: Dict[str, float],
        anomaly_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Classifies the failure mode and gathers factual evidence.
        Returns:
            category: str (one of the 10 canonical categories)
            confidence: float
            evidence: list[str]
        """
        lat = metrics.get("latency", 1.2)
        err = metrics.get("error_rate", 0.005)
        tokens = metrics.get("token_usage", 520.0)
        retrieval = metrics.get("retrieval_score", 0.92)
        hallucination = metrics.get("hallucination_score", 0.03)
        tool_fail = metrics.get("tool_failure_rate", 0.008)
        req_vol = metrics.get("request_volume", 50.0)
        cpu = metrics.get("cpu_usage", 35.0)
        succ = metrics.get("api_success_rate", 0.995)

        evidence: List[str] = []
        candidate_scores: Dict[str, float] = {cat: 0.0 for cat in FailureCategory.ALL}

        # --- Rule Signatures ---

        # 1. AGENT_LOOP: high latency + extreme token usage + high CPU
        is_loop = (tokens >= 2400.0 and lat >= 6.5 and cpu >= 70.0)
        if is_loop:
            candidate_scores[FailureCategory.AGENT_LOOP] += 0.98
            evidence.append(f"High token usage ({tokens:.0f} tokens) combined with latency ({lat:.2f}s) and CPU load ({cpu:.1f}%) indicates iterative agent loop")

        # 2. TOOL_FAILURE: high tool failure rate (not dominated by agent loop)
        if tool_fail >= 0.15 and not is_loop:
            candidate_scores[FailureCategory.TOOL_FAILURE] += 0.90 + min(0.08, tool_fail * 0.1)
            evidence.append(f"Tool failure rate spiked to {tool_fail:.2%} (healthy baseline: <= 2.0%)")

        # 3. RAG_DEGRADATION vs RETRIEVAL_FAILURE
        if retrieval <= 0.65:
            if hallucination >= 0.25:
                candidate_scores[FailureCategory.RAG_DEGRADATION] += 0.91
                evidence.append(f"Retrieval score dropped to {retrieval:.2f} with elevated hallucination score {hallucination:.2f}")
            elif retrieval <= 0.40:
                candidate_scores[FailureCategory.RETRIEVAL_FAILURE] += 0.93
                evidence.append(f"Critical retrieval failure: retrieval score collapsed to {retrieval:.2f} (baseline: 0.92)")
            else:
                candidate_scores[FailureCategory.RAG_DEGRADATION] += 0.85
                evidence.append(f"Sub-optimal retrieval score {retrieval:.2f}")

        # 4. LLM_FAILURE: high error_rate from LLM timeouts/hallucinations/errors
        if err >= 0.10:
            candidate_scores[FailureCategory.LLM_FAILURE] += 0.90 + min(0.08, err * 0.2)
            evidence.append(f"LLM error rate elevated to {err:.2%} (healthy baseline: <= 1.0%)")

        # 5. API_FAILURE: external network/endpoint connectivity drops while internal errors are low
        if succ <= 0.88 and err < 0.10 and tool_fail < 0.10:
            candidate_scores[FailureCategory.API_FAILURE] += 0.92
            evidence.append(f"API success rate degraded to {succ:.2%} without associated internal model exceptions")

        # 6. LATENCY_SPIKE: latency > 4.0 without agent loop
        if lat >= 4.0 and tokens < 2400.0:
            candidate_scores[FailureCategory.LATENCY_SPIKE] += 0.89
            evidence.append(f"Latency surged to {lat:.2f}s (healthy SLA threshold: 4.0s, baseline: 1.2s)")

        # 7. COST_SPIKE: tokens > 1800 or high request volume without long latency
        if tokens >= 1800.0 and lat < 6.5:
            candidate_scores[FailureCategory.COST_SPIKE] += 0.88
            evidence.append(f"Token consumption spiked to {tokens:.0f} tokens/request (+{((tokens - 520.0)/520.0):.0%} above baseline)")
        if req_vol >= 130.0:
            candidate_scores[FailureCategory.COST_SPIKE] += 0.40
            evidence.append(f"Request volume surge: {req_vol:.0f} req/s (baseline: 50.0 req/s)")

        # 8. DATA_QUALITY: subtle degradation in retrieval without full outage, or hallucination in isolation
        if 0.65 < retrieval <= 0.78 and hallucination >= 0.10:
            candidate_scores[FailureCategory.DATA_QUALITY] += 0.82
            evidence.append(f"Data quality drift: retrieval score {retrieval:.2f}, hallucination {hallucination:.2f}")

        # Determine highest scoring candidate
        best_category, score = max(candidate_scores.items(), key=lambda x: x[1])

        if score < 0.50:
            best_category = FailureCategory.UNKNOWN
            score = 0.50
            if not evidence:
                evidence.append("Metrics exhibit unexpected distribution without matching known failure signatures")

        confidence = round(min(0.98, max(0.65, score)), 2)

        return {
            "category": best_category,
            "confidence": confidence,
            "evidence": evidence,
        }
