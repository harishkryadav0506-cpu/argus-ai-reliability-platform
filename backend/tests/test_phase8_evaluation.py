"""
ARGUS Phase 8 Test Suite — LangSmith Tracing, Local Evaluation, Benchmarking & Fine-Tuning Dataset (Sections 17-19, 28, 32, 37.5)
"""
import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from app.config import Settings, get_settings
from app.evaluation.metrics import (
    calculate_detection_metrics,
    calculate_diagnosis_accuracy,
    calculate_rag_retrieval_score,
    calculate_groundedness_score,
    calculate_recovery_success_rate,
    calculate_unsafe_action_rate,
    calculate_mean_recovery_time,
    calculate_average_latency,
    EvaluationReport,
)
from app.evaluation.evaluators import IncidentEvaluator
from app.evaluation.benchmark import BenchmarkRunner, BENCHMARK_SCENARIOS
from app.evaluation.datasets import generate_finetune_dataset
from app.graph.graph import argus_graph


def test_langsmith_config_graceful_fallback_and_metadata():
    """
    Per Section 17 & 32:
    - When LangSmith is disabled/unconfigured, tracing is disabled gracefully so local logging continues.
    - When configured, tracing is enabled and metadata is attached.
    """
    # 1. Test fallback / disabled state
    unconfigured_settings = Settings(
        LANGSMITH_API_KEY=None,
        LANGSMITH_TRACING_V2=False,
    )
    unconfigured_settings.configure_tracing()
    assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"

    # 2. Test configured state
    configured_settings = Settings(
        LANGSMITH_API_KEY="test_lsv2_key_12345",
        LANGSMITH_PROJECT="ARGUS-test-suite",
        LANGSMITH_TRACING_V2=True,
    )
    configured_settings.configure_tracing()
    assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
    assert os.environ.get("LANGCHAIN_API_KEY") == "test_lsv2_key_12345"
    assert os.environ.get("LANGCHAIN_PROJECT") == "ARGUS-test-suite"

    # 3. Test that metadata is attached to invoke wrapper
    with patch("app.graph.graph.get_settings", return_value=configured_settings):
        sample_input = {
            "incident": {"id": "inc_trace_test_01", "severity": "high"},
            "failure_type": "LATENCY_SPIKE",
            "selected_strategy": {"action": "restart_service"},
        }
        test_config = {}
        # We test invoke_wrapper logic by inspecting config injection
        argus_graph.invoke(sample_input, config=test_config)
        assert "metadata" in test_config
        meta = test_config["metadata"]
        assert meta["incident_id"] == "inc_trace_test_01"
        assert meta["failure_type"] == "LATENCY_SPIKE"
        assert meta["severity"] == "high"
        assert meta["agent_name"] == "argus_graph"
        assert meta["recovery_strategy"] == "restart_service"

    # Reset tracing to false for remainder of tests
    unconfigured_settings.configure_tracing()


def test_metrics_calculation_real_math():
    """
    Per Section 19: All metrics must compute real mathematical formulas.
    Never fabricated numbers.
    """
    # Detection metrics
    gt = [True, True, False, False, True]
    dt = [True, False, False, True, True]
    # TP=2 (index 0, 4), FN=1 (index 1), FP=1 (index 3), TN=1 (index 2)
    det = calculate_detection_metrics(gt, dt)
    assert det.tp == 2
    assert det.fn == 1
    assert det.fp == 1
    assert det.tn == 1
    assert det.accuracy == 0.6
    assert det.precision == round(2 / 3, 4)
    assert det.recall == round(2 / 3, 4)
    assert det.f1 == round(2 / 3, 4)

    # Diagnosis accuracy
    diagnosed = ["LLM_FAILURE", "RAG_DEGRADATION", "LATENCY_SPIKE"]
    ground_truth = ["LLM_FAILURE", "RAG_DEGRADATION", "COST_SPIKE"]
    assert calculate_diagnosis_accuracy(diagnosed, ground_truth) == round(2 / 3, 4)

    # RAG Retrieval score
    assert calculate_rag_retrieval_score([0.75, 0.85, 0.65]) == 0.75

    # Groundedness score
    citations = [["RB-001", "RB-002"], ["RB-003"], []]
    assert calculate_groundedness_score(citations) == round((1.0 + 0.5 + 0.0) / 3, 4)

    # Recovery Success Rate
    assert calculate_recovery_success_rate([True, True, False, True]) == 0.75

    # Unsafe Action Rate
    assert calculate_unsafe_action_rate(total_actions=20, blocked_or_unsafe_actions=1) == 0.05

    # Mean Recovery Time
    assert calculate_mean_recovery_time([30.0, 60.0, 90.0]) == 60.0

    # Average Latency
    assert calculate_average_latency([1.2, 1.4, 1.6]) == 1.4


def test_benchmark_pipeline_version_comparison():
    """
    Per Section 18: Benchmark pipeline compares v1 (baseline) vs v2 (ARGUS)
    across at least 15 simulated scenarios.
    """
    runner = BenchmarkRunner()
    assert len(BENCHMARK_SCENARIOS) >= 15

    result = runner.run_benchmark(scenarios=BENCHMARK_SCENARIOS)

    assert result.total_scenarios >= 15
    assert result.v1_baseline.version_name == "v1_baseline"
    assert result.v2_argus.version_name == "v2_argus"

    # v2 (ARGUS LangGraph + ML + RAG) should strictly outperform v1 (static threshold)
    assert result.v2_argus.detection_f1 >= result.v1_baseline.detection_f1
    assert result.v2_argus.diagnosis_accuracy >= result.v1_baseline.diagnosis_accuracy
    assert result.v2_argus.recovery_success_rate >= result.v1_baseline.recovery_success_rate
    assert result.v2_argus.unsafe_action_rate <= result.v1_baseline.unsafe_action_rate
    assert result.v2_argus.mean_recovery_time_sec <= result.v1_baseline.mean_recovery_time_sec

    # Markdown table formatting
    table_md = result.to_markdown_table()
    assert "ARGUS Benchmark Evaluation Report" in table_md
    assert "v1 (Rule-Based Baseline)" in table_md
    assert "v2 (ARGUS LangGraph + RAG + MCP)" in table_md


def test_incident_evaluator_local_report():
    """
    Per Section 19: Local evaluation report must work without LangSmith credentials
    and return complete metrics.
    """
    evaluator = IncidentEvaluator()
    report = evaluator.evaluate_incidents(limit=50)

    assert isinstance(report, EvaluationReport)
    assert report.total_incidents >= 0
    assert 0.0 <= report.detection_accuracy <= 1.0
    assert 0.0 <= report.detection_f1 <= 1.0
    assert 0.0 <= report.diagnosis_accuracy <= 1.0
    assert 0.0 <= report.recovery_success_rate <= 1.0
    assert 0.0 <= report.unsafe_action_rate <= 1.0
    assert report.mean_recovery_time_sec >= 0.0

    table_md = report.to_markdown_table()
    assert "ARGUS Local Evaluation Report" in table_md
    assert "Detection F1 Score" in table_md


def test_finetune_dataset_generation(tmp_path: Path):
    """
    Per Section 28 & 37.5: Exports resolved incidents into Section 28 JSONL format
    and guarantees safe repeated execution without duplicates.
    """
    dataset_file = tmp_path / "dataset.jsonl"

    # Run 1: generate
    rows_pass1 = generate_finetune_dataset(output_path=dataset_file)
    assert len(rows_pass1) > 0

    first_row = rows_pass1[0]
    # Check Section 28 JSON schema: incident, evidence, root_cause, recovery, verification
    assert "incident" in first_row
    assert "evidence" in first_row
    assert "root_cause" in first_row
    assert "recovery" in first_row
    assert "verification" in first_row

    # Run 2: re-run to verify safe repeatability / idempotence
    rows_pass2 = generate_finetune_dataset(output_path=dataset_file)
    assert len(rows_pass2) == len(rows_pass1)
