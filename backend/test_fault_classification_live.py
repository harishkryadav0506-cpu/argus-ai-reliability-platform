import time
from app.services.simulation_service import simulation_engine
from app.ml.anomaly_detection import AnomalyDetector
from app.ml.failure_prediction import FailureClassifier

fault_types = [
    "LATENCY_SPIKE",
    "LLM_FAILURE",
    "RAG_DEGRADATION",
    "TOOL_FAILURE",
    "COST_SPIKE",
    "AGENT_LOOP"
]

detector = AnomalyDetector()
classifier = FailureClassifier()

print("=" * 115)
print("%-18s | %-18s | %-9s | %-10s | %-9s | %s" % ("INJECTED FAULT", "CLASSIFICATION", "DET CONF", "PRED CONF", "ANOMALY?", "PRIMARY EVIDENCE"))
print("=" * 115)

results = []
for fault in fault_types:
    # 1. Reset simulation to baseline
    simulation_engine.reset_to_normal()
    simulation_engine.tick()

    # 2. Inject fault into simulation engine
    simulation_engine.inject_fault(fault_type=fault, severity="high", duration_seconds=60)
    simulation_engine.tick()
    metrics = simulation_engine.get_current_metrics()

    # 3. Detect anomaly & Classify
    det = detector.detect(metrics)
    pred = classifier.classify(metrics, anomaly_info=det)

    category = pred.get("category", "UNKNOWN")
    conf = pred.get("confidence", 0.0)
    det_conf = det.get("confidence", 0.0)
    evidence = pred.get("evidence", [])

    ev_str = "; ".join(evidence[:2])
    is_anomaly = str(det.get("anomaly_detected"))

    print("%-18s | %-18s | %-9.2f | %-10.2f | %-9s | %s" % (fault, category, det_conf, conf, is_anomaly, ev_str))
    results.append({
        "fault": fault,
        "category": category,
        "conf": conf,
        "det_conf": det_conf,
        "metrics": metrics,
        "evidence": evidence
    })
    time.sleep(0.3)

print("=" * 115)
conf_values = [r["conf"] for r in results]
unique_confs = len(set(conf_values))
matches = sum(1 for r in results if r["fault"] == r["category"])
print(f"Summary: {matches}/6 Classified Correctly | Distinct Confidence Values: {unique_confs}/6 ({conf_values})")
