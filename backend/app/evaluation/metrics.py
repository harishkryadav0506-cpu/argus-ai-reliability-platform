"""
ARGUS Evaluation Metrics (Phase 8 - Sections 18 & 19)

Implements rigorous, mathematical evaluation metrics computed over actual incident
and recovery telemetry. NEVER FABRICATES NUMBERS (Sections 19 & 34).
"""
from dataclasses import dataclass
from typing import Any, Dict, List
from pydantic import BaseModel, Field


@dataclass
class DetectionMetrics:
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0


def calculate_detection_metrics(
    ground_truth_anomalies: List[bool],
    detected_anomalies: List[bool],
) -> DetectionMetrics:
    """
    Computes Confusion Matrix (TP, FP, TN, FN), Accuracy, Precision, Recall, and F1.
    All calculations are based strictly on evaluated samples.
    """
    if not ground_truth_anomalies or len(ground_truth_anomalies) != len(detected_anomalies):
        return DetectionMetrics()

    tp = sum(1 for gt, dt in zip(ground_truth_anomalies, detected_anomalies) if gt and dt)
    fp = sum(1 for gt, dt in zip(ground_truth_anomalies, detected_anomalies) if not gt and dt)
    tn = sum(1 for gt, dt in zip(ground_truth_anomalies, detected_anomalies) if not gt and not dt)
    fn = sum(1 for gt, dt in zip(ground_truth_anomalies, detected_anomalies) if gt and not dt)

    total = len(ground_truth_anomalies)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if tp == 0 and fp == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return DetectionMetrics(
        accuracy=round(accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
    )


def calculate_diagnosis_accuracy(
    diagnosed_types: List[str],
    ground_truth_types: List[str],
) -> float:
    """
    Computes diagnosis accuracy (exact classification match).
    """
    if not diagnosed_types or len(diagnosed_types) != len(ground_truth_types):
        return 0.0
    matches = sum(
        1 for d, g in zip(diagnosed_types, ground_truth_types)
        if d.strip().upper() == g.strip().upper()
    )
    return round(matches / len(diagnosed_types), 4)


def calculate_rag_retrieval_score(retrieval_scores: List[float]) -> float:
    """
    Computes average relevance score of top retrieved runbooks.
    """
    if not retrieval_scores:
        return 0.0
    return round(sum(retrieval_scores) / len(retrieval_scores), 4)


def calculate_groundedness_score(citations_list: List[List[Any]]) -> float:
    """
    Computes citation groundedness score based on evidence cited per diagnosis.
    """
    if not citations_list:
        return 0.0
    scores = [min(1.0, len(c) / 2.0) if c else 0.0 for c in citations_list]
    return round(sum(scores) / len(scores), 4)


def calculate_recovery_success_rate(verified_outcomes: List[bool]) -> float:
    """
    Computes ratio of verified recoveries to total recovery executions.
    """
    if not verified_outcomes:
        return 0.0
    successes = sum(1 for v in verified_outcomes if v is True)
    return round(successes / len(verified_outcomes), 4)


def calculate_unsafe_action_rate(
    total_actions: int,
    blocked_or_unsafe_actions: int,
) -> float:
    """
    Computes the rate of unsafe/blocked actions encountered.
    """
    if total_actions <= 0:
        return 0.0
    return round(blocked_or_unsafe_actions / total_actions, 4)


def calculate_mean_recovery_time(recovery_times_seconds: List[float]) -> float:
    """
    Computes Mean Recovery Time (MTTR) in seconds for resolved incidents.
    """
    if not recovery_times_seconds:
        return 0.0
    return round(sum(recovery_times_seconds) / len(recovery_times_seconds), 2)


def calculate_average_latency(latencies: List[float]) -> float:
    """
    Computes average system latency in seconds across evaluated windows.
    """
    if not latencies:
        return 0.0
    return round(sum(latencies) / len(latencies), 3)


class EvaluationReport(BaseModel):
    """
    Structured report conforming to docs/ARGUS_SPEC.md Section 19.
    """
    evaluation_id: str
    evaluated_at: str
    total_incidents: int
    detection_accuracy: float
    detection_precision: float
    detection_recall: float
    detection_f1: float
    diagnosis_accuracy: float
    rag_retrieval_score: float
    groundedness: float
    recovery_success_rate: float
    unsafe_action_rate: float
    mean_recovery_time_sec: float
    average_latency_sec: float
    average_token_cost_est: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_markdown_table(self) -> str:
        """
        Formats metrics into a clean markdown table matching Section 19.
        """
        lines = [
            f"### ARGUS Local Evaluation Report ({self.evaluated_at})",
            f"**Total Incidents Evaluated**: {self.total_incidents}",
            "",
            "| Metric | Value | Baseline / Target | Status |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Detection Accuracy** | `{self.detection_accuracy * 100:.1f}%` | `> 85.0%` | {'[PASS]' if self.detection_accuracy >= 0.85 else '[WARN]'} |",
            f"| **Detection Precision** | `{self.detection_precision * 100:.1f}%` | `> 85.0%` | {'[PASS]' if self.detection_precision >= 0.85 else '[WARN]'} |",
            f"| **Detection Recall** | `{self.detection_recall * 100:.1f}%` | `> 85.0%` | {'[PASS]' if self.detection_recall >= 0.85 else '[WARN]'} |",
            f"| **Detection F1 Score** | `{self.detection_f1:.4f}` | `> 0.8500` | {'[PASS]' if self.detection_f1 >= 0.85 else '[WARN]'} |",
            f"| **Diagnosis Accuracy** | `{self.diagnosis_accuracy * 100:.1f}%` | `> 80.0%` | {'[PASS]' if self.diagnosis_accuracy >= 0.80 else '[WARN]'} |",
            f"| **RAG Retrieval Score** | `{self.rag_retrieval_score:.4f}` | `> 0.6000` | {'[PASS]' if self.rag_retrieval_score >= 0.60 else '[WARN]'} |",
            f"| **Groundedness** | `{self.groundedness * 100:.1f}%` | `> 80.0%` | {'[PASS]' if self.groundedness >= 0.80 else '[WARN]'} |",
            f"| **Recovery Success Rate** | `{self.recovery_success_rate * 100:.1f}%` | `> 75.0%` | {'[PASS]' if self.recovery_success_rate >= 0.75 else '[WARN]'} |",
            f"| **Unsafe Action Rate** | `{self.unsafe_action_rate * 100:.1f}%` | `< 5.0%` | {'[PASS]' if self.unsafe_action_rate <= 0.05 else '[WARN]'} |",
            f"| **Mean Recovery Time** | `{self.mean_recovery_time_sec:.2f}s` | `< 120s` | {'[PASS]' if self.mean_recovery_time_sec <= 120 else '[WARN]'} |",
            f"| **Average Latency** | `{self.average_latency_sec:.3f}s` | `< 3.0s` | {'[PASS]' if self.average_latency_sec <= 3.0 else '[WARN]'} |",
        ]
        return "\n".join(lines)
