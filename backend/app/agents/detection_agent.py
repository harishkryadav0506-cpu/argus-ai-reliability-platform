"""
ARGUS Detection Agent (Phase 5 - Sections 8, 9, 10)

Wraps Phase 3 AnomalyDetector and FailureClassifier within the LangGraph workflow.
Inspects telemetry metrics, identifies anomalies, and classifies the failure type.
"""
import logging
from typing import Any, Dict

from app.graph.state import ArgusState
from app.ml.anomaly_detection import AnomalyDetector
from app.ml.failure_prediction import FailureClassifier

logger = logging.getLogger(__name__)

# Reusable detector and classifier instances
_detector = AnomalyDetector()
_classifier = FailureClassifier()


def detection_agent(state: ArgusState) -> Dict[str, Any]:
    """
    Executes failure detection and classification on the current metrics.
    """
    metrics = state.get("metrics", {})
    history_trace = list(state.get("history_trace", []))
    history_trace.append("DetectionAgent: analyzing metrics stream")

    # 1. Run ML anomaly detector
    anomaly_res = _detector.detect(metrics)

    # 2. Run failure classifier
    classification = _classifier.classify(metrics, anomaly_res)

    if not anomaly_res["anomaly_detected"]:
        category = "UNKNOWN"
        confidence = state.get("failure_confidence", 0.35)
    else:
        category = classification["category"]
        confidence = state.get("failure_confidence", classification["confidence"])

    logs = list(state.get("logs", []))
    logs.append(
        f"[DetectionAgent] Anomaly={anomaly_res['anomaly_detected']}, "
        f"Category={category}, "
        f"Confidence={confidence:.2f}, "
        f"Severity={anomaly_res['severity']}"
    )

    return {
        "failure_type": category,
        "failure_confidence": confidence,
        "evidence": classification["evidence"] if anomaly_res["anomaly_detected"] else [],
        "logs": logs,
        "history_trace": history_trace,
        "final_status": "investigating" if anomaly_res["anomaly_detected"] else "open",
    }
