"""Integration tests for Regression Evaluation Harness."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.services.eval_benchmark_service import EvalBenchmarkService
from app.services.regression_harness_service import RegressionHarnessService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_regression_harness_execution(db_session):
    benchmark_service = EvalBenchmarkService(db_session)
    seeded = benchmark_service.seed_default_datasets()
    assert len(seeded) > 0

    dataset = seeded[0]
    harness = RegressionHarnessService(db_session)

    # Run Baseline
    baseline_run = harness.execute_eval_run(dataset_id=dataset.id, prompt_version="v1.0")
    assert baseline_run is not None
    assert baseline_run.status == "completed"
    assert len(baseline_run.results) == len(dataset.test_cases)

    # Run Current
    current_run = harness.execute_eval_run(dataset_id=dataset.id, prompt_version="v1.1")
    assert current_run is not None

    # Compare Baseline vs Current
    report = harness.compare_against_baseline(
        current_run_id=current_run.id,
        baseline_run_id=baseline_run.id,
        max_quality_drop_pct=5.0,
        max_cost_increase_pct=15.0,
    )
    assert report is not None
    assert report.run_id == current_run.id
    assert report.baseline_run_id == baseline_run.id
    assert isinstance(report.has_regression, bool)
