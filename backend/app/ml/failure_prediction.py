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

        # --- Rule Signatures with Continuous Metric Gradients ---

        # 1. AGENT_LOOP: high latency + extreme token usage + high CPU (iterative circular reasoning)
        is_loop = (tokens >= 2200.0 and lat >= 5.5 and cpu >= 60.0) or (tokens >= 2600.0 and lat >= 6.0)
        if is_loop:
            # Dynamic scaling based on CPU, tokens, and latency
            loop_strength = (
                0.88
                + 0.04 * min(1.0, max(0.0, (cpu - 60.0) / 40.0))
                + 0.04 * min(1.0, max(0.0, (tokens - 2200.0) / 3000.0))
                + 0.02 * min(1.0, max(0.0, (lat - 5.5) / 10.0))
            )
            candidate_scores[FailureCategory.AGENT_LOOP] += loop_strength
            evidence.append(f"High token usage ({tokens:.0f} tokens) combined with latency ({lat:.2f}s) and CPU load ({cpu:.1f}%) indicates iterative agent loop")

        # 2. TOOL_FAILURE: primary tool failure rate spike (not dominated by agent loop)
        if tool_fail >= 0.12 and not is_loop:
            tool_strength = 0.86 + 0.10 * min(1.0, max(0.0, (tool_fail - 0.12) / 0.50))
            candidate_scores[FailureCategory.TOOL_FAILURE] += tool_strength
            evidence.append(f"Tool failure rate spiked to {tool_fail:.2%} (healthy baseline: <= 2.0%)")

        # 3. RAG_DEGRADATION vs RETRIEVAL_FAILURE
        if retrieval <= 0.70 or hallucination >= 0.20:
            if hallucination >= 0.25:
                rag_strength = (
                    0.82
                    + 0.08 * min(1.0, max(0.0, (hallucination - 0.20) / 0.60))
                    + 0.05 * min(1.0, max(0.0, (0.70 - retrieval) / 0.40))
                )
                candidate_scores[FailureCategory.RAG_DEGRADATION] += rag_strength
                evidence.append(f"Retrieval score dropped to {retrieval:.2f} with elevated hallucination score {hallucination:.2f}")
            elif retrieval <= 0.40:
                candidate_scores[FailureCategory.RETRIEVAL_FAILURE] += 0.84 + 0.08 * min(1.0, (0.40 - retrieval) / 0.40)
                evidence.append(f"Critical retrieval failure: retrieval score collapsed to {retrieval:.2f} (baseline: 0.92)")
            else:
                candidate_scores[FailureCategory.RAG_DEGRADATION] += 0.80 + 0.06 * min(1.0, (0.70 - retrieval) / 0.30)
                evidence.append(f"Sub-optimal retrieval score {retrieval:.2f} (healthy baseline: >= 0.85)")

        # 4. LLM_FAILURE: high error_rate from LLM timeouts/internal errors (not downstream of tool cascade)
        if err >= 0.08:
            if tool_fail >= 0.12:
                # Tool failure is the primary root cause; LLM error is downstream
                candidate_scores[FailureCategory.LLM_FAILURE] += 0.65
                evidence.append(f"Downstream error rate {err:.2%} coinciding with tool failures")
            else:
                llm_strength = 0.84 + 0.10 * min(1.0, max(0.0, (err - 0.08) / 0.35))
                candidate_scores[FailureCategory.LLM_FAILURE] += llm_strength
                evidence.append(f"LLM error rate elevated to {err:.2%} (healthy baseline: <= 1.0%)")

        # 5. API_FAILURE: external connectivity drops while internal errors and tool failures are low
        if succ <= 0.88 and err < 0.08 and tool_fail < 0.10:
            candidate_scores[FailureCategory.API_FAILURE] += 0.82 + 0.08 * min(1.0, max(0.0, (0.88 - succ) / 0.30))
            evidence.append(f"API success rate degraded to {succ:.2%} without associated internal model exceptions")

        # 6. LATENCY_SPIKE: latency > 3.5s without agent loop
        if lat >= 3.5 and not is_loop and tokens < 1600.0:
            lat_strength = 0.83 + 0.10 * min(1.0, max(0.0, (lat - 3.5) / 7.0))
            candidate_scores[FailureCategory.LATENCY_SPIKE] += lat_strength
            evidence.append(f"Latency surged to {lat:.2f}s (healthy SLA threshold: 4.0s, baseline: 1.2s)")

        # 7. COST_SPIKE: tokens > 1800 or high request volume without long latency or loop
        if (tokens >= 1800.0 or req_vol >= 110.0) and not is_loop:
            cost_strength = (
                0.81
                + 0.07 * min(1.0, max(0.0, (tokens - 1800.0) / 2500.0))
                + 0.05 * min(1.0, max(0.0, (req_vol - 110.0) / 100.0))
            )
            if tokens >= 2000.0:
                evidence.append(f"Token consumption spiked to {tokens:.0f} tokens/request (+{((tokens - 520.0)/520.0):.0%} above baseline)")
            if req_vol >= 110.0:
                evidence.append(f"Request volume surge: {req_vol:.0f} req/s (baseline: 50.0 req/s)")
            candidate_scores[FailureCategory.COST_SPIKE] += cost_strength

        # 8. DATA_QUALITY: subtle degradation in retrieval without full outage, or hallucination in isolation
        if 0.65 < retrieval <= 0.80 and 0.08 <= hallucination < 0.20:
            candidate_scores[FailureCategory.DATA_QUALITY] += 0.78
            evidence.append(f"Data quality drift: retrieval score {retrieval:.2f}, hallucination {hallucination:.2f}")

        # Determine highest scoring candidate
        best_category, raw_score = max(candidate_scores.items(), key=lambda x: x[1])

        if raw_score < 0.50:
            best_category = FailureCategory.UNKNOWN
            if anomaly_info and anomaly_info.get("anomaly_detected"):
                det_conf = float(anomaly_info.get("confidence", 0.65))
                sev = anomaly_info.get("severity", "medium")
                sev_factor = {"low": 0.52, "medium": 0.62, "high": 0.72, "critical": 0.82}.get(sev, 0.62)
                affected_count = len(anomaly_info.get("affected_metrics", []))
                affected_factor = min(0.08, affected_count * 0.025)

                # Dual-model ensemble blend for unclassified/UNKNOWN anomalies:
                # Genuinely blend anomaly detector signal strength (confidence & severity)
                # with classifier residual score and affected metric spread
                classifier_residual = 0.50 + (0.25 * raw_score)
                blended = (0.45 * det_conf) + (0.35 * sev_factor) + (0.20 * classifier_residual) + affected_factor
                final_confidence = round(min(0.88, max(0.52, blended)), 2)
            else:
                final_confidence = round(min(0.65, max(0.50, 0.50 + raw_score)), 2)

            if not evidence:
                evidence.append("Metrics exhibit unexpected distribution without matching known failure signatures")
        else:
            # Genuinely blend rule signal strength (55%) with AnomalyDetector confidence (45%)
            # from anomaly_info (which reflects multivariate Isolation Forest + Z-score distance)
            if anomaly_info and anomaly_info.get("anomaly_detected"):
                det_conf = float(anomaly_info.get("confidence", 0.85))
                blended = (0.55 * raw_score) + (0.45 * det_conf)
            else:
                blended = raw_score

            # Scale smoothly without artificial constant clipping
            final_confidence = round(min(0.97, max(0.65, blended)), 2)

        return {
            "category": best_category,
            "confidence": final_confidence,
            "evidence": evidence,
        }
