from app.ml.anomaly_detection import AnomalyDetector
from app.ml.failure_prediction import FailureClassifier, FailureCategory

def main():
    detector = AnomalyDetector()
    classifier = FailureClassifier()

    unknown_test_cases = [
        ("Mild hallucination drift (inc 8d5eec21)", {"latency": 1.226, "error_rate": 0.003, "retrieval_score": 0.953, "hallucination_score": 0.0765, "cpu_usage": 28.3, "memory_usage": 51.2}),
        ("Moderate CPU surge", {"latency": 1.25, "error_rate": 0.004, "cpu_usage": 48.0, "memory_usage": 49.0, "request_volume": 55.0}),
        ("Severe CPU surge (inc 75c4d5dc)", {"latency": 1.25, "error_rate": 0.004, "cpu_usage": 68.5, "memory_usage": 49.0, "request_volume": 55.0}),
        ("Memory usage surge (inc 8e574d77)", {"latency": 1.18, "error_rate": 0.006, "cpu_usage": 34.0, "memory_usage": 62.5, "request_volume": 48.0}),
        ("Request surge + API drift (inc 64537d8e)", {"latency": 1.35, "error_rate": 0.008, "request_volume": 64.0, "api_success_rate": 0.988, "cpu_usage": 40.0}),
        ("Dual metric drift (inc ac7706ba)", {"latency": 1.21, "error_rate": 0.0095, "hallucination_score": 0.062, "cpu_usage": 38.0, "memory_usage": 52.0}),
        ("Triple multi-metric skew", {"latency": 1.45, "error_rate": 0.007, "token_usage": 620.0, "cpu_usage": 48.0, "memory_usage": 56.0, "api_success_rate": 0.989}),
    ]

    print("=" * 120)
    print(f"{'SCENARIO':<42} | {'CATEGORY':<10} | {'DET CONF':<9} | {'SEVERITY':<9} | {'PRED CONF':<10} | {'AFFECTED METRICS'}")
    print("=" * 120)

    confidences = []
    for name, metrics in unknown_test_cases:
        det_res = detector.detect(metrics)
        clf_res = classifier.classify(metrics, det_res)
        confidences.append(clf_res["confidence"])
        affected = ", ".join(det_res["affected_metrics"]) if det_res["affected_metrics"] else "none"
        print(f"{name:<42} | {clf_res['category']:<10} | {det_res['confidence']:<9.2f} | {det_res['severity']:<9} | {clf_res['confidence']:<10.2f} | {affected}")

    print("=" * 120)
    distinct = sorted(list(set(confidences)))
    print(f"Distinct confidence values: {len(distinct)}/{len(confidences)}: {distinct}")
    assert len(distinct) > 1, "Expected confidence values to vary, but all were identical!"
    assert all(c != 0.50 for c in confidences), "Found hardcoded 0.50 confidence!"
    print("ALL ASSERTIONS PASSED: UNKNOWN incidents now have genuinely varying confidence!")

if __name__ == "__main__":
    main()
