"""Evaluation Framework REST API Endpoints."""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.dependencies import get_db
from app.models.eval_benchmark import GoldenDataset, GoldenTestCase, EvalRun, EvalResult
from app.schemas.eval import (
    GoldenDatasetCreate,
    GoldenDatasetResponse,
    GoldenTestCaseCreate,
    GoldenTestCaseResponse,
    EvalRunCreate,
    EvalRunResponse,
    EvalResultResponse,
    RegressionReport,
)
from app.services.eval_benchmark_service import EvalBenchmarkService
from app.services.regression_harness_service import RegressionHarnessService

router = APIRouter(prefix="/eval", tags=["Evaluation Framework"])


@router.post("/datasets/seed", response_model=list[GoldenDatasetResponse])
def seed_golden_datasets(db: Session = Depends(get_db)):
    """Seed default golden benchmark datasets if not present."""
    service = EvalBenchmarkService(db)
    datasets = service.seed_default_datasets()
    return [
        GoldenDatasetResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            version=d.version,
            category=d.category,
            created_at=d.created_at,
            updated_at=d.updated_at,
            test_case_count=len(d.test_cases),
        )
        for d in datasets
    ]


@router.post("/datasets", response_model=GoldenDatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(data: GoldenDatasetCreate, db: Session = Depends(get_db)):
    """Create a new Golden Benchmark Dataset."""
    service = EvalBenchmarkService(db)
    dataset = service.create_dataset(data)
    return GoldenDatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        version=dataset.version,
        category=dataset.category,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
        test_case_count=len(dataset.test_cases),
    )


@router.get("/datasets", response_model=list[GoldenDatasetResponse])
def list_datasets(db: Session = Depends(get_db)):
    """List all golden benchmark datasets."""
    service = EvalBenchmarkService(db)
    datasets = service.list_datasets()
    return [
        GoldenDatasetResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            version=d.version,
            category=d.category,
            created_at=d.created_at,
            updated_at=d.updated_at,
            test_case_count=len(d.test_cases),
        )
        for d in datasets
    ]


@router.get("/datasets/{dataset_id}", response_model=GoldenDatasetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Get golden dataset by ID."""
    service = EvalBenchmarkService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Golden dataset '{dataset_id}' not found.")
    return GoldenDatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        version=dataset.version,
        category=dataset.category,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
        test_case_count=len(dataset.test_cases),
    )


@router.post("/datasets/{dataset_id}/cases", response_model=GoldenTestCaseResponse, status_code=status.HTTP_201_CREATED)
def add_test_case(dataset_id: str, data: GoldenTestCaseCreate, db: Session = Depends(get_db)):
    """Add a test case to a golden dataset."""
    service = EvalBenchmarkService(db)
    test_case = service.add_test_case(dataset_id, data)
    if not test_case:
        raise HTTPException(status_code=404, detail=f"Golden dataset '{dataset_id}' not found.")
    return test_case


@router.post("/runs", response_model=EvalRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_eval_run(data: EvalRunCreate, db: Session = Depends(get_db)):
    """Trigger an evaluation run against a dataset."""
    harness = RegressionHarnessService(db)
    eval_run = harness.execute_eval_run(
        dataset_id=data.dataset_id,
        model_name=data.model_name,
        prompt_version=data.prompt_version,
    )
    if not eval_run:
        raise HTTPException(status_code=404, detail=f"Golden dataset '{data.dataset_id}' not found.")
    return eval_run


@router.get("/runs", response_model=list[EvalRunResponse])
def list_eval_runs(dataset_id: Optional[str] = None, db: Session = Depends(get_db)):
    """List evaluation suite runs."""
    stmt = select(EvalRun)
    if dataset_id:
        stmt = stmt.where(EvalRun.dataset_id == dataset_id)
    stmt = stmt.order_by(EvalRun.created_at.desc())
    runs = db.scalars(stmt).all()
    return runs


@router.get("/runs/{run_id}", response_model=EvalRunResponse)
def get_eval_run(run_id: str, db: Session = Depends(get_db)):
    """Get detailed evaluation run report."""
    eval_run = db.scalar(select(EvalRun).where(EvalRun.id == run_id))
    if not eval_run:
        raise HTTPException(status_code=404, detail=f"Evaluation run '{run_id}' not found.")
    return eval_run


@router.post("/regression/compare", response_model=RegressionReport)
def compare_regression(
    current_run_id: str,
    baseline_run_id: str,
    max_quality_drop_pct: float = 5.0,
    max_cost_increase_pct: float = 15.0,
    db: Session = Depends(get_db),
):
    """Compare a current evaluation run against a baseline run for regression auditing."""
    harness = RegressionHarnessService(db)
    report = harness.compare_against_baseline(
        current_run_id=current_run_id,
        baseline_run_id=baseline_run_id,
        max_quality_drop_pct=max_quality_drop_pct,
        max_cost_increase_pct=max_cost_increase_pct,
    )
    if not report:
        raise HTTPException(status_code=404, detail="One or both evaluation runs not found.")
    return report
