"""
ARGUS Benchmark Runner CLI (Phase 8 - Sections 18 & 19)

Executes the version-comparison benchmark pipeline against at least 15 simulated
incidents and prints the raw Section 19 formatted evaluation table to the terminal.
"""
import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.evaluation.benchmark import BenchmarkRunner, BENCHMARK_SCENARIOS


def main():
    print("=" * 80)
    print("ARGUS BENCHMARK PIPELINE — VERSION COMPARISON (Sections 18 & 19)")
    print("=" * 80)
    print(f"Loading {len(BENCHMARK_SCENARIOS)} simulated incident scenarios...")

    runner = BenchmarkRunner()
    result = runner.run_benchmark(scenarios=BENCHMARK_SCENARIOS)

    # Print Section 19 raw markdown table
    print("\n" + result.to_markdown_table() + "\n")

    # Save benchmark JSON artifact
    eval_dir = root_dir / "data" / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    report_path = eval_dir / "benchmark_report.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2)

    print(f"Benchmark artifact saved to: {report_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
