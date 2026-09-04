"""Data Analysis Service for Phase 7 (Data Agent & Data Visualization)."""
import os
import uuid
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.data_analysis import (
    UploadedDataset,
    DataQueryRecord,
    VisualizationSpec,
    ReproducibleArtifact,
)
from app.schemas.data_analysis import (
    SQLQueryRequest,
    SQLQueryResponse,
    DatasetProfileResponse,
    PythonAnalysisRequest,
    PythonAnalysisResponse,
    ChartSpecRequest,
    ChartSpecResponse,
    ReproducibleArtifactResponse,
)
from app.tools.sql_tool import SQLTool
from app.tools.csv_tool import CSVTool
from app.tools.python_sandbox import PythonSandboxTool
from app.tools.chart_tool import ChartTool

logger = logging.getLogger(__name__)


class DataService:
    """Service layer orchestrating dataset uploads, SQL execution, Python sandbox, and visualization artifacts."""

    def __init__(self, db_session: Session, db_path: str = "radis_dev.db") -> None:
        self.db = db_session
        self.sql_tool = SQLTool(db_path=db_path)
        self.csv_tool = CSVTool(db_path=db_path)
        self.python_sandbox = PythonSandboxTool()
        self.chart_tool = ChartTool()

    def process_dataset_upload(self, file_path: str, filename: str) -> DatasetProfileResponse:
        """Ingests structured file, creates SQLite table, persists model, and returns profile."""
        table_name, df = self.csv_tool.ingest_to_sqlite(file_path)
        ext = os.path.splitext(filename)[1].lstrip(".").lower()
        
        profile = self.csv_tool.profile_dataframe(
            df=df,
            table_name=table_name,
            filename=filename,
            file_type=ext,
        )

        dataset_record = UploadedDataset(
            id=profile.dataset_id,
            filename=filename,
            file_type=ext,
            table_name=table_name,
            row_count=profile.row_count,
            column_count=profile.column_count,
            schema_info={"columns": [c.model_dump() for c in profile.columns]},
            summary_stats=profile.summary_stats,
            storage_path=file_path,
        )
        self.db.add(dataset_record)
        self.db.commit()
        self.db.refresh(dataset_record)

        return profile

    def get_dataset_schema(self, dataset_id: uuid.UUID) -> Optional[DatasetProfileResponse]:
        """Fetches dataset profile and column schema for a given dataset_id."""
        record = self.db.query(UploadedDataset).filter(UploadedDataset.id == dataset_id).first()
        if not record:
            return None

        columns = self.sql_tool.get_table_schema(record.table_name)
        return DatasetProfileResponse(
            dataset_id=record.id,
            filename=record.filename,
            file_type=record.file_type,
            table_name=record.table_name,
            row_count=record.row_count,
            column_count=record.column_count,
            columns=columns,
            summary_stats=record.summary_stats or {},
            sample_rows=[],
        )

    def execute_sql_query(self, req: SQLQueryRequest, query_id: Optional[uuid.UUID] = None) -> SQLQueryResponse:
        """Executes read-only SQL query and persists DataQueryRecord."""
        res = self.sql_tool.execute_query(req.sql, limit=req.limit)

        query_record = DataQueryRecord(
            query_id=query_id,
            dataset_id=req.dataset_id,
            query_type="sql",
            raw_query=req.sql,
            executed_code=res.sql,
            is_success=res.is_success,
            error_message=res.error_message,
            result_data=res.rows,
            row_count=res.row_count,
            execution_time_ms=res.execution_time_ms,
        )
        self.db.add(query_record)
        self.db.commit()

        res.query_id = query_record.id
        return res

    def execute_python_analysis(
        self, req: PythonAnalysisRequest, query_id: Optional[uuid.UUID] = None
    ) -> PythonAnalysisResponse:
        """Executes sandboxed Python script and logs DataQueryRecord."""
        input_rows = req.input_data
        if req.dataset_id and not input_rows:
            dataset = self.db.query(UploadedDataset).filter(UploadedDataset.id == req.dataset_id).first()
            if dataset:
                sql_res = self.sql_tool.execute_query(f"SELECT * FROM {dataset.table_name} LIMIT 500")
                input_rows = sql_res.rows

        res = self.python_sandbox.execute_script(
            python_code=req.python_code,
            input_data=input_rows,
        )

        query_record = DataQueryRecord(
            query_id=query_id,
            dataset_id=req.dataset_id,
            query_type="python",
            raw_query=req.python_code,
            executed_code=req.python_code,
            is_success=res.is_success,
            error_message=res.error_message,
            result_data=res.result_data,
            row_count=len(res.result_data),
            execution_time_ms=res.execution_time_ms,
        )
        self.db.add(query_record)
        self.db.commit()

        return res

    def generate_visualization(
        self, req: ChartSpecRequest, query_id: Optional[uuid.UUID] = None
    ) -> ChartSpecResponse:
        """Generates visualization spec and persists spec to DB."""
        spec_res = self.chart_tool.generate_chart_spec(
            title=req.title,
            chart_type=req.chart_type,
            data=req.data,
            x_axis=req.x_axis,
            y_axis=req.y_axis,
            description=req.description,
            query_id=query_id,
        )

        spec_record = VisualizationSpec(
            id=spec_res.id,
            query_id=query_id,
            title=spec_res.title,
            chart_type=spec_res.chart_type,
            description=spec_res.description,
            spec_json=spec_res.spec_json,
            table_data=spec_res.table_data,
            key_findings=spec_res.key_findings,
        )
        self.db.add(spec_record)
        self.db.commit()

        return spec_res

    def get_reproducible_artifact(self, query_id: uuid.UUID) -> Optional[ReproducibleArtifactResponse]:
        """Compiles SQL queries, Python scripts, chart configs, and logs into a ReproducibleArtifact."""
        records = self.db.query(DataQueryRecord).filter(DataQueryRecord.query_id == query_id).all()
        specs = self.db.query(VisualizationSpec).filter(VisualizationSpec.query_id == query_id).all()

        sql_queries = [r.raw_query for r in records if r.query_type == "sql"]
        python_scripts = [r.raw_query for r in records if r.query_type == "python"]
        chart_configs = [s.spec_json for s in specs]
        logs = [f"[{r.query_type.upper()}] Execution time: {r.execution_time_ms}ms, rows: {r.row_count}" for r in records]

        artifact = ReproducibleArtifact(
            query_id=query_id,
            title=f"Reproducible Analysis Artifact for Query {query_id}",
            sql_queries=sql_queries,
            python_scripts=python_scripts,
            chart_configs=chart_configs,
            intermediate_data_summary={"query_count": len(records), "chart_count": len(specs)},
            execution_logs=logs,
        )
        self.db.add(artifact)
        self.db.commit()

        return ReproducibleArtifactResponse(
            id=artifact.id,
            query_id=query_id,
            title=artifact.title,
            sql_queries=artifact.sql_queries,
            python_scripts=artifact.python_scripts,
            chart_configs=artifact.chart_configs,
            intermediate_data_summary=artifact.intermediate_data_summary,
            execution_logs=artifact.execution_logs,
            created_at=artifact.created_at,
        )
