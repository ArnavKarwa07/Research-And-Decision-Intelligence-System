"""Data Analysis database models for Phase 7 (Data Agent & Data Visualization)."""
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import ForeignKey, Text, Float, Integer, JSON, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.query import Query


class UploadedDataset(TimestampMixin, Base):
    """Database model for an uploaded or ingested structured dataset (CSV / XLSX / SQLite)."""

    __tablename__ = "uploaded_datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # csv, xlsx, sqlite
    table_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    schema_info: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    summary_stats: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    storage_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "schema_info" not in kwargs or kwargs["schema_info"] is None:
            kwargs["schema_info"] = {}
        if "summary_stats" not in kwargs or kwargs["summary_stats"] is None:
            kwargs["summary_stats"] = {}
        super().__init__(**kwargs)


class DataQueryRecord(TimestampMixin, Base):
    """Database model for a logged SQL/Python data query execution."""

    __tablename__ = "data_query_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    query_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("queries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("uploaded_datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    query_type: Mapped[str] = mapped_column(String(50), nullable=False)  # sql, python
    raw_query: Mapped[str] = mapped_column(Text, nullable=False)
    executed_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_data: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0)

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "result_data" not in kwargs or kwargs["result_data"] is None:
            kwargs["result_data"] = []
        super().__init__(**kwargs)


class VisualizationSpec(TimestampMixin, Base):
    """Database model for generated chart & table specifications."""

    __tablename__ = "visualization_specs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    query_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("queries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    chart_type: Mapped[str] = mapped_column(String(50), nullable=False)  # bar, line, scatter, pie, summary_table
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    spec_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    table_data: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    key_findings: Mapped[List[str]] = mapped_column(JSON, default=list)

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "spec_json" not in kwargs or kwargs["spec_json"] is None:
            kwargs["spec_json"] = {}
        if "table_data" not in kwargs or kwargs["table_data"] is None:
            kwargs["table_data"] = []
        if "key_findings" not in kwargs or kwargs["key_findings"] is None:
            kwargs["key_findings"] = []
        super().__init__(**kwargs)


class ReproducibleArtifact(TimestampMixin, Base):
    """Database model for reproducible analysis artifacts."""

    __tablename__ = "reproducible_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    query_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("queries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    sql_queries: Mapped[List[str]] = mapped_column(JSON, default=list)
    python_scripts: Mapped[List[str]] = mapped_column(JSON, default=list)
    chart_configs: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    intermediate_data_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    execution_logs: Mapped[List[str]] = mapped_column(JSON, default=list)

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "sql_queries" not in kwargs or kwargs["sql_queries"] is None:
            kwargs["sql_queries"] = []
        if "python_scripts" not in kwargs or kwargs["python_scripts"] is None:
            kwargs["python_scripts"] = []
        if "chart_configs" not in kwargs or kwargs["chart_configs"] is None:
            kwargs["chart_configs"] = []
        if "intermediate_data_summary" not in kwargs or kwargs["intermediate_data_summary"] is None:
            kwargs["intermediate_data_summary"] = {}
        if "execution_logs" not in kwargs or kwargs["execution_logs"] is None:
            kwargs["execution_logs"] = []
        super().__init__(**kwargs)
