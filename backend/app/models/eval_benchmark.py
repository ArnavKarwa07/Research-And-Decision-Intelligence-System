"""Database models for Golden Datasets, Evaluation Runs, and Metric Results."""
import uuid
from typing import Any, Optional
from sqlalchemy import String, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class GoldenDataset(Base, TimestampMixin):
    """Represents a standardized golden evaluation dataset."""
    __tablename__ = "golden_datasets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="general", index=True)

    # Relationships
    test_cases: Mapped[list["GoldenTestCase"]] = relationship(
        "GoldenTestCase", back_populates="dataset", cascade="all, delete-orphan"
    )
    eval_runs: Mapped[list["EvalRun"]] = relationship(
        "EvalRun", back_populates="dataset", cascade="all, delete-orphan"
    )


class GoldenTestCase(Base, TimestampMixin):
    """Represents a single ground-truth test case in a golden dataset."""
    __tablename__ = "golden_test_cases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("golden_datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="general", index=True)
    ground_truth_claims: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    required_sources: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    expected_decision_matrix: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    expected_rankings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # Relationships
    dataset: Mapped["GoldenDataset"] = relationship("GoldenDataset", back_populates="test_cases")
    results: Mapped[list["EvalResult"]] = relationship(
        "EvalResult", back_populates="test_case", cascade="all, delete-orphan"
    )


class EvalRun(Base, TimestampMixin):
    """Represents an execution of an evaluation benchmark suite."""
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("golden_datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    summary_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationships
    dataset: Mapped["GoldenDataset"] = relationship("GoldenDataset", back_populates="eval_runs")
    results: Mapped[list["EvalResult"]] = relationship(
        "EvalResult", back_populates="eval_run", cascade="all, delete-orphan"
    )


class EvalResult(Base, TimestampMixin):
    """Represents evaluation metric scores for a single test case run."""
    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    eval_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("golden_test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    retrieval_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    claim_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    citation_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    trajectory_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    decision_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pass_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationships
    eval_run: Mapped["EvalRun"] = relationship("EvalRun", back_populates="results")
    test_case: Mapped["GoldenTestCase"] = relationship("GoldenTestCase", back_populates="results")
