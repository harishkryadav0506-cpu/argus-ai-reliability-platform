"""
Phase 3 tests — ML Anomaly Detection & Failure Classification.

Tests:
1. Anomaly detection schema and sensitivity
2. 10-category failure classification with evidence
3. Benchmark evaluation for Precision and Recall on known normal/abnormal windows

Run with: pytest backend/tests/test_ml_detection.py -v -s
"""
import pytest
from app.ml.anomaly_detection import AnomalyDetector
from app.ml.failure_prediction import FailureClassifier, FailureCategory
from app.services.simulation_service import BASELINE_DISTRIBUTIONS, FAULT_DISTORTIONS, SimulationEngine


@pytest.fixture
def detector():
    return AnomalyDetector(z_threshold=2.5)


@pytest.fixture
def classifier():
    return FailureClassifier()


# --- 1. Anomaly Detector Unit Tests ---

def test_anomaly_detector_normal_metrics(detector):
    normal_metrics = {
        "latency": 1.22,
        "error_rate": 0.005,
        "token_usage": 510.0,
        "retrieval_score": 0.93,
        "hallucination_score": 0.02,
        "tool_failure_rate": 0.007,
        "request_volume": 49.0,
        "cpu_usage": 34.0,
        "memory_usage": 47.0,
        "api_success_rate": 0.996,
    }

    res = detector.detect(normal_metrics)

    # Check exact Section 8 schema
    assert "anomaly_detected" in res
    assert "severity" in res
    assert "confidence" in res
    assert "affected_metrics" in res

    assert res["anomaly_detected"] is False
    assert res["severity"] == "low"
    assert res["affected_metrics"] == []
    assert 0.0 <= res["confidence"] <= 1.0


def test_anomaly_detector_abnormal_metrics(detector):
    abnormal_metrics = {
        "latency": 8.8,
        "error_rate": 0.15,
        "token_usage": 2400.0,
        "retrieval_score": 0.50,
        "hallucination_score": 0.40,
        "tool_failure_rate": 0.01,
        "request_volume": 52.0,
        "cpu_usage": 78.0,
        "memory_usage": 60.0,
        "api_success_rate": 0.88,
    }

    res = detector.detect(abnormal_metrics)

    assert res["anomaly_detected"] is True
    assert res["severity"] in ["medium", "high", "critical"]
    assert res["confidence"] >= 0.70
    assert "latency" in res["affected_metrics"]
    assert "error_rate" in res["affected_metrics"]
    assert "retrieval_score" in res["affected_metrics"]


# --- 2. Failure Classifier Tests for 10 Canonical Categories ---

def test_classify_all_canonical_categories(classifier):
    # Test cases mapping metric signatures to categories
    test_cases = [
        (
            FailureCategory.LLM_FAILURE,
            {"error_rate": 0.32, "api_success_rate": 0.65, "latency": 4.5, "tool_failure_rate": 0.01},
        ),
        (
            FailureCategory.RAG_DEGRADATION,
            {"retrieval_score": 0.48, "hallucination_score": 0.52, "token_usage": 1450.0},
        ),
        (
            FailureCategory.RETRIEVAL_FAILURE,
            {"retrieval_score": 0.32, "hallucination_score": 0.04, "latency": 1.4},
        ),
        (
            FailureCategory.TOOL_FAILURE,
            {"tool_failure_rate": 0.45, "error_rate": 0.15, "api_success_rate": 0.82},
        ),
        (
            FailureCategory.API_FAILURE,
            {"api_success_rate": 0.72, "error_rate": 0.02, "tool_failure_rate": 0.005},
        ),
        (
            FailureCategory.LATENCY_SPIKE,
            {"latency": 8.9, "cpu_usage": 76.0, "token_usage": 550.0, "error_rate": 0.005},
        ),
        (
            FailureCategory.COST_SPIKE,
            {"token_usage": 3200.0, "request_volume": 185.0, "latency": 2.1},
        ),
        (
            FailureCategory.AGENT_LOOP,
            {"token_usage": 4100.0, "latency": 12.5, "cpu_usage": 94.0, "tool_failure_rate": 0.22},
        ),
        (
            FailureCategory.DATA_QUALITY,
            {"retrieval_score": 0.72, "hallucination_score": 0.15, "latency": 1.3},
        ),
        (
            FailureCategory.UNKNOWN,
            {"request_volume": 51.0, "cpu_usage": 36.0, "memory_usage": 49.0},
        ),
    ]

    for expected_category, metrics in test_cases:
        result = classifier.classify(metrics)
        assert result["category"] == expected_category, (
            f"Expected {expected_category}, got {result['category']} for metrics {metrics}"
        )
        assert "confidence" in result
        assert 0.50 <= result["confidence"] <= 1.0
        assert "evidence" in result
        assert isinstance(result["evidence"], list)
        assert len(result["evidence"]) > 0


# --- 3. Precision / Recall Benchmark Evaluation ---

def test_ml_detection_precision_and_recall(detector):
    """
    Evaluates detector across a balanced benchmark of 100 windows
    (50 normal baseline, 50 abnormal fault windows across all fault profiles).
    Computes confusion matrix and asserts Precision, Recall, and F1 >= 0.90.
    """
    engine = SimulationEngine()
    tp = 0
    fp = 0
    tn = 0
    fn = 0

    # 1. Evaluate 50 Normal Windows (Ground Truth: Negative)
    engine.reset_to_normal()
    for _ in range(50):
        metrics = engine.generate_metrics()
        res = detector.detect(metrics)
        if res["anomaly_detected"]:
            fp += 1
        else:
            tn += 1

    # 2. Evaluate 50 Abnormal Windows across the 6 simulated fault types (Ground Truth: Positive)
    fault_types = list(FAULT_DISTORTIONS.keys())
    for i in range(50):
        fault = fault_types[i % len(fault_types)]
        engine.inject_fault(fault, severity="high", duration_seconds=60)
        metrics = engine.generate_metrics()
        res = detector.detect(metrics)
        if res["anomaly_detected"]:
            tp += 1
        else:
            fn += 1

    engine.reset_to_normal()

    # Metrics calculation
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print("\n--- ML Anomaly Detector Benchmark Results ---")
    print(f"Total Samples: 100 (50 Normal, 50 Abnormal)")
    print(f"Confusion Matrix: TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")

    assert precision >= 0.90, f"Precision {precision:.4f} is below 0.90"
    assert recall >= 0.90, f"Recall {recall:.4f} is below 0.90"
    assert f1 >= 0.90, f"F1 score {f1:.4f} is below 0.90"
