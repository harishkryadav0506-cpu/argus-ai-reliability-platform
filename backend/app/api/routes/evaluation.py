"""
ARGUS Evaluation API Routes (Phase 8 - Sections 18, 19, 23)

Endpoints for triggering local evaluation and fetching benchmark results.
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.evaluation.evaluators import IncidentEvaluator
from app.evaluation.benchmark import BenchmarkRunner, BenchmarkResult
from app.evaluation.metrics import EvaluationReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
evaluator = IncidentEvaluator()
benchmark_runner = BenchmarkRunner()


@router.post("/run", response_model=EvaluationReport)
def run_evaluation(db: Session = Depends(get_db)):
    """
    Computes Section 19 local evaluation metrics across all recorded incidents.
    Works without LangSmith credentials.
    """
    report = evaluator.evaluate_incidents(db=db)
    return report


@router.get("/benchmark", response_model=BenchmarkResult)
def get_benchmark():
    """
    Executes and returns the Section 18 version comparison benchmark report.
    """
    result = benchmark_runner.run_benchmark()
    return result
