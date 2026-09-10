"""
ARGUS Simulation Engine (Phase 2)

Generates synthetic metrics for an AI application under normal traffic and simulated
fault conditions per docs/ARGUS_SPEC.md Sections 7 and 37.2.
Detects threshold violations and triggers incident creation via incident_service.
"""
import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.simulation import FaultType
from app.services import incident_service
from app.ml.anomaly_detection import AnomalyDetector
from app.ml.failure_prediction import FailureClassifier

logger = logging.getLogger(__name__)

# Baseline target distributions for the 10 monitored metrics
BASELINE_DISTRIBUTIONS = {
    "latency": {"mean": 1.2, "std": 0.12, "min": 0.6, "max": 2.2},
    "error_rate": {"mean": 0.005, "std": 0.002, "min": 0.0, "max": 0.02},
    "token_usage": {"mean": 520.0, "std": 45.0, "min": 350.0, "max": 750.0},
    "retrieval_score": {"mean": 0.92, "std": 0.02, "min": 0.82, "max": 0.99},
    "hallucination_score": {"mean": 0.03, "std": 0.015, "min": 0.0, "max": 0.08},
    "tool_failure_rate": {"mean": 0.008, "std": 0.004, "min": 0.0, "max": 0.03},
    "request_volume": {"mean": 50.0, "std": 5.0, "min": 25.0, "max": 75.0},
    "cpu_usage": {"mean": 35.0, "std": 4.0, "min": 20.0, "max": 50.0},
    "memory_usage": {"mean": 48.0, "std": 3.0, "min": 35.0, "max": 60.0},
    "api_success_rate": {"mean": 0.995, "std": 0.002, "min": 0.98, "max": 1.0},
}

# Fault injection metric distortions modeled on real failure modes (Section 37.2)
FAULT_DISTORTIONS = {
    FaultType.LATENCY_SPIKE: {
        "latency": {"mean": 8.5, "std": 1.2, "min": 5.0, "max": 14.0},
        "cpu_usage": {"mean": 75.0, "std": 6.0, "min": 60.0, "max": 90.0},
        "api_success_rate": {"mean": 0.91, "std": 0.03, "min": 0.85, "max": 0.96},
    },
    FaultType.LLM_FAILURE: {
        "error_rate": {"mean": 0.28, "std": 0.06, "min": 0.15, "max": 0.45},
        "api_success_rate": {"mean": 0.70, "std": 0.06, "min": 0.55, "max": 0.82},
        "latency": {"mean": 4.8, "std": 0.8, "min": 3.0, "max": 7.5},
    },
    FaultType.RAG_DEGRADATION: {
        "retrieval_score": {"mean": 0.48, "std": 0.05, "min": 0.35, "max": 0.60},
        "hallucination_score": {"mean": 0.55, "std": 0.08, "min": 0.38, "max": 0.75},
        "token_usage": {"mean": 1450.0, "std": 180.0, "min": 1100.0, "max": 2100.0},
    },
    FaultType.TOOL_FAILURE: {
        "tool_failure_rate": {"mean": 0.42, "std": 0.07, "min": 0.25, "max": 0.65},
        "error_rate": {"mean": 0.18, "std": 0.04, "min": 0.10, "max": 0.30},
        "api_success_rate": {"mean": 0.80, "std": 0.05, "min": 0.70, "max": 0.90},
    },
    FaultType.COST_SPIKE: {
        "token_usage": {"mean": 2900.0, "std": 320.0, "min": 2200.0, "max": 4200.0},
        "request_volume": {"mean": 190.0, "std": 25.0, "min": 140.0, "max": 280.0},
    },
    FaultType.AGENT_LOOP: {
        "token_usage": {"mean": 3800.0, "std": 450.0, "min": 2800.0, "max": 5500.0},
        "latency": {"mean": 11.5, "std": 2.0, "min": 7.5, "max": 18.0},
        "cpu_usage": {"mean": 92.0, "std": 4.0, "min": 82.0, "max": 99.0},
        "tool_failure_rate": {"mean": 0.25, "std": 0.05, "min": 0.12, "max": 0.40},
    },
}

# Thresholds that indicate an anomaly requiring incident creation
SLA_THRESHOLDS = [
    {"metric": "latency", "operator": ">", "value": 4.0, "fault_type": FaultType.LATENCY_SPIKE, "severity": "high"},
    {"metric": "error_rate", "operator": ">", "value": 0.08, "fault_type": FaultType.LLM_FAILURE, "severity": "critical"},
    {"metric": "retrieval_score", "operator": "<", "value": 0.65, "fault_type": FaultType.RAG_DEGRADATION, "severity": "high"},
    {"metric": "hallucination_score", "operator": ">", "value": 0.30, "fault_type": FaultType.RAG_DEGRADATION, "severity": "high"},
    {"metric": "tool_failure_rate", "operator": ">", "value": 0.15, "fault_type": FaultType.TOOL_FAILURE, "severity": "high"},
    {"metric": "token_usage", "operator": ">", "value": 2000.0, "fault_type": FaultType.COST_SPIKE, "severity": "medium"},
]


class SimulationEngine:
    """
    Simulation Engine simulating AI application metrics and faults.
    """

    def __init__(self, history_size: int = 120):
        self.history_size = history_size
        self._history: List[Dict[str, Any]] = []
        self._ticks_generated: int = 0

        # Fault state
        self._active_fault: Optional[str] = None
        self._fault_severity: Optional[str] = None
        self._fault_expires_at: Optional[datetime] = None
        self._incident_triggered_for_current_fault: bool = False

        # Background runner state
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

        # ML Detection and Classification Layer (Phase 3)
        self.detector = AnomalyDetector()
        self.classifier = FailureClassifier()

        # Seed with initial normal tick
        self.tick()

    @property
    def is_fault_active(self) -> bool:
        if not self._active_fault:
            return False
        if self._fault_expires_at and datetime.now(timezone.utc) > self._fault_expires_at:
            self.reset_to_normal()
            return False
        return True

    def inject_fault(
        self,
        fault_type: str,
        severity: str = "high",
        duration_seconds: int = 60,
    ) -> Dict[str, Any]:
        """Injects a specific fault mode into the simulation."""
        if fault_type not in FAULT_DISTORTIONS:
            raise ValueError(f"Unknown fault type: {fault_type}. Must be one of {list(FAULT_DISTORTIONS.keys())}")

        now = datetime.now(timezone.utc)
        self._active_fault = fault_type
        self._fault_severity = severity
        self._fault_expires_at = datetime.fromtimestamp(now.timestamp() + duration_seconds, tz=timezone.utc)
        self._incident_triggered_for_current_fault = False

        logger.info(
            "Fault %s injected with severity %s for %ds.",
            fault_type,
            severity,
            duration_seconds,
        )
        return self.get_status()

    def reset_to_normal(self) -> Dict[str, Any]:
        """Resets simulation to normal traffic conditions."""
        self._active_fault = None
        self._fault_severity = None
        self._fault_expires_at = None
        self._incident_triggered_for_current_fault = False
        logger.info("Simulation reset to normal traffic mode.")
        return self.get_status()

    def _sample_metric(self, spec: Dict[str, float]) -> float:
        val = random.gauss(spec["mean"], spec["std"])
        val = max(spec["min"], min(spec["max"], val))
        return round(val, 4)

    def generate_metrics(self) -> Dict[str, float]:
        """Generates a single tick of the 10 monitored metrics."""
        metrics: Dict[str, float] = {}

        # 1. Base normal metrics
        for name, spec in BASELINE_DISTRIBUTIONS.items():
            metrics[name] = self._sample_metric(spec)

        # 2. Apply fault distortions if fault is active
        if self.is_fault_active and self._active_fault in FAULT_DISTORTIONS:
            distortions = FAULT_DISTORTIONS[self._active_fault]
            for name, spec in distortions.items():
                metrics[name] = self._sample_metric(spec)

        return metrics

    def check_thresholds(self, metrics: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        Evaluates SLA thresholds against generated metrics.
        Returns the primary violating threshold rule if breached.
        """
        for rule in SLA_THRESHOLDS:
            val = metrics.get(rule["metric"])
            if val is None:
                continue

            breached = False
            if rule["operator"] == ">" and val > rule["value"]:
                breached = True
            elif rule["operator"] == "<" and val < rule["value"]:
                breached = True

            if breached:
                return rule
        return None

    def tick(self) -> Dict[str, Any]:
        """Advances the simulation by one tick, evaluates SLA, and logs history."""
        now = datetime.now(timezone.utc)

        # Auto-expire fault if duration has elapsed
        if self._fault_expires_at and now > self._fault_expires_at:
            self.reset_to_normal()

        metrics = self.generate_metrics()
        point = {
            "timestamp": now,
            "metrics": metrics,
        }

        self._history.append(point)
        if len(self._history) > self.history_size:
            self._history.pop(0)

        self._ticks_generated += 1

        # Check for anomalies using ML detector (Z-score + Isolation Forest ensemble)
        anomaly_res = self.detector.detect(metrics)
        violation = self.check_thresholds(metrics)

        # Trigger incident if anomaly is detected by ML model or threshold breached
        is_anomalous = anomaly_res["anomaly_detected"] or (violation is not None)
        if is_anomalous and not self._incident_triggered_for_current_fault:
            classification = self.classifier.classify(metrics, anomaly_res)
            fault_type = self._active_fault or classification["category"]
            severity = self._fault_severity or anomaly_res["severity"]

            affected_str = ", ".join(anomaly_res["affected_metrics"]) if anomaly_res["affected_metrics"] else "multivariate anomaly"
            title = f"{fault_type} Anomaly Detected: {affected_str}"
            evidence_summary = "; ".join(classification["evidence"]) if classification["evidence"] else "statistical divergence detected"
            desc = (
                f"ML Anomaly Detector identified {severity} severity condition with {anomaly_res['confidence']:.0%} confidence. "
                f"Evidence: {evidence_summary}"
            )

            try:
                incident_service.create_incident(
                    title=title,
                    description=desc,
                    severity=severity,
                    failure_type=fault_type,
                    confidence=classification["confidence"],
                    metrics=metrics,
                )
                self._incident_triggered_for_current_fault = True
                logger.warning("Incident automatically triggered via ML detection: %s", title)
            except Exception as e:
                logger.error("Failed to create incident on anomaly detection: %s", e)

        return point

    def get_current_metrics(self) -> Dict[str, float]:
        if not self._history:
            self.tick()
        return self._history[-1]["metrics"]

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._history[-limit:]

    def get_status(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        active = self.is_fault_active
        remaining_sec = None
        if active and self._fault_expires_at:
            remaining_sec = max(0, int((self._fault_expires_at - now).total_seconds()))

        return {
            "mode": "fault_active" if active else "normal",
            "active_fault": self._active_fault if active else None,
            "severity": self._fault_severity if active else None,
            "remaining_seconds": remaining_sec,
            "ticks_generated": self._ticks_generated,
            "current_metrics": self.get_current_metrics(),
        }

    async def _background_loop(self, interval: float = 2.0):
        logger.info("Simulation background loop started with %ss interval.", interval)
        try:
            while self._running:
                self.tick()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Simulation background loop cancelled.")
        except Exception as e:
            logger.exception("Unexpected error in simulation background loop: %s", e)

    def start_background_task(self, interval: float = 2.0):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._background_loop(interval))

    def stop_background_task(self):
        if self._running:
            self._running = False
            if self._task and not self._task.done():
                self._task.cancel()


# Global singleton simulation engine
simulation_engine = SimulationEngine()


def get_simulation_engine() -> SimulationEngine:
    return simulation_engine
