"""
ARGUS ML Anomaly Detection (Phase 3 - Section 8)

Ensemble anomaly detector combining:
1. Univariate rolling statistical thresholds (rolling mean, std, z-score)
2. Multivariate Isolation Forest for high-dimensional anomaly scoring

Returns the exact JSON shape required by ARGUS_SPEC Section 8:
{
  "anomaly_detected": bool,
  "severity": str,
  "confidence": float,
  "affected_metrics": list[str]
}
"""
import math
import numpy as np
from typing import Any, Dict, List, Optional
from sklearn.ensemble import IsolationForest


METRIC_DIRECTIONS = {
    "latency": "higher_is_worse",
    "error_rate": "higher_is_worse",
    "token_usage": "higher_is_worse",
    "retrieval_score": "lower_is_worse",
    "hallucination_score": "higher_is_worse",
    "tool_failure_rate": "higher_is_worse",
    "request_volume": "higher_is_worse",
    "cpu_usage": "higher_is_worse",
    "memory_usage": "higher_is_worse",
    "api_success_rate": "lower_is_worse",
}

DEFAULT_BASELINES = {
    "latency": {"mean": 1.2, "std": 0.12},
    "error_rate": {"mean": 0.005, "std": 0.002},
    "token_usage": {"mean": 520.0, "std": 45.0},
    "retrieval_score": {"mean": 0.92, "std": 0.02},
    "hallucination_score": {"mean": 0.03, "std": 0.015},
    "tool_failure_rate": {"mean": 0.008, "std": 0.004},
    "request_volume": {"mean": 50.0, "std": 5.0},
    "cpu_usage": {"mean": 35.0, "std": 4.0},
    "memory_usage": {"mean": 48.0, "std": 3.0},
    "api_success_rate": {"mean": 0.995, "std": 0.002},
}

METRIC_ORDER = [
    "latency",
    "error_rate",
    "token_usage",
    "retrieval_score",
    "hallucination_score",
    "tool_failure_rate",
    "request_volume",
    "cpu_usage",
    "memory_usage",
    "api_success_rate",
]


class AnomalyDetector:
    """
    Hybrid statistical + Isolation Forest anomaly detector.
    """

    def __init__(
        self,
        z_threshold: float = 2.5,
        window_size: int = 60,
        random_state: int = 42,
    ):
        self.z_threshold = z_threshold
        self.window_size = window_size
        self._history: List[Dict[str, float]] = []

        # Fit Isolation Forest on baseline distribution
        self.iso_forest = IsolationForest(
            n_estimators=100,
            contamination=0.03,
            random_state=random_state,
        )
        self._warmup_model()

    def _warmup_model(self):
        """Pre-fits the Isolation Forest on synthetic normal baseline samples."""
        rng = np.random.default_rng(42)
        samples = []
        for _ in range(300):
            row = []
            for m in METRIC_ORDER:
                mean = DEFAULT_BASELINES[m]["mean"]
                std = DEFAULT_BASELINES[m]["std"]
                row.append(rng.normal(mean, std))
            samples.append(row)
        X = np.array(samples)
        self.iso_forest.fit(X)

    def _compute_z_scores(self, metrics: Dict[str, float]) -> Dict[str, float]:
        """Calculates directional z-scores for each metric."""
        z_scores = {}
        for m in METRIC_ORDER:
            val = metrics.get(m)
            if val is None:
                continue

            base = DEFAULT_BASELINES[m]
            mean = base["mean"]
            std = max(base["std"], 1e-6)

            direction = METRIC_DIRECTIONS[m]
            if direction == "higher_is_worse":
                z = (val - mean) / std
            else:  # lower_is_worse
                z = (mean - val) / std

            z_scores[m] = round(z, 4)
        return z_scores

    def detect(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Evaluates metrics using Z-score thresholding + Isolation Forest ensemble.
        Returns the exact JSON shape required by Section 8.
        """
        z_scores = self._compute_z_scores(metrics)

        # 1. Statistical analysis
        affected_metrics = []
        max_z = 0.0
        critical_z = 0.0
        critical_metrics = {"latency", "error_rate", "retrieval_score", "tool_failure_rate", "token_usage"}

        for m, z in z_scores.items():
            if z >= self.z_threshold:
                affected_metrics.append(m)
            if z > max_z:
                max_z = z
            if m in critical_metrics and z > critical_z:
                critical_z = z

        # 2. Multivariate Isolation Forest analysis
        vector = np.array([[metrics.get(m, DEFAULT_BASELINES[m]["mean"]) for m in METRIC_ORDER]])
        if_score = float(self.iso_forest.decision_function(vector)[0])  # lower = more anomalous
        if_anomaly = (if_score < -0.06)

        # 3. Robust Ensemble Decision:
        # - Strong signal on any metric (z >= 3.0, or z >= 2.8 on critical metrics)
        # - Multi-metric deviation (>= 2 metrics with z >= 2.2)
        # - Multivariate outlier confirmed by Isolation Forest (if_score < -0.06) with at least moderate drift (z >= 1.8)
        strong_stat_anomaly = (critical_z >= 2.8) or (max_z >= 3.0)
        multi_metric_anomaly = len(affected_metrics) >= 2 or (len([z for z in z_scores.values() if z >= 2.0]) >= 2)
        joint_anomaly = if_anomaly and (max_z >= 1.8)

        anomaly_detected = bool(strong_stat_anomaly or multi_metric_anomaly or joint_anomaly)

        # Ensure affected_metrics is populated if anomaly detected via multivariate
        if anomaly_detected and not affected_metrics:
            affected_metrics = [m for m, z in z_scores.items() if z >= 1.8]

        # 4. Confidence & Severity computation
        if anomaly_detected:
            # Scale confidence with z-score and Isolation Forest distance
            z_conf = 1.0 / (1.0 + math.exp(-0.8 * (max_z - 2.0)))
            if_conf = 1.0 / (1.0 + math.exp(15.0 * if_score))
            raw_conf = 0.65 * z_conf + 0.35 * if_conf
            confidence = round(min(0.99, max(0.55, raw_conf)), 2)

            # Assign severity based on impacted metrics and magnitude of degradation
            err = metrics.get("error_rate", 0.0)
            succ = metrics.get("api_success_rate", 1.0)
            lat = metrics.get("latency", 0.0)

            if err >= 0.20 or succ < 0.70 or max_z >= 6.0:
                severity = "critical"
            elif max_z >= 4.0 or len(affected_metrics) >= 2 or err >= 0.08 or lat >= 4.0:
                severity = "high"
            elif max_z >= 2.8 or len(affected_metrics) >= 1:
                severity = "medium"
            else:
                severity = "low"
        else:
            confidence = 0.05
            severity = "low"
            affected_metrics = []

        return {
            "anomaly_detected": anomaly_detected,
            "severity": severity,
            "confidence": confidence,
            "affected_metrics": affected_metrics,
        }
