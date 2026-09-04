"""Data Investigation Agent for Phase 7 (Data Agent)."""
import logging
from typing import Any, Dict, Optional
from app.agents.agent_contracts import DataAgentInput, DataAgentOutput
from app.tools.sql_tool import SQLTool
from app.tools.python_sandbox import PythonSandboxTool

logger = logging.getLogger(__name__)


class DataInvestigationAgent:
    """Specialist Data Agent for SQL queries, sandboxed Python analysis, and data profiling."""

    def __init__(self, db_path: str = "radis_dev.db") -> None:
        self.sql_tool = SQLTool(db_path=db_path)
        self.python_sandbox = PythonSandboxTool()

    def run(self, input_data: DataAgentInput) -> DataAgentOutput:
        """Executes data investigation workflow with safety guardrails and budget enforcement."""
        logger.info(f"[DataInvestigationAgent] Processing query: {input_data.query}")

        # If explicit SQL query provided
        if input_data.sql_query:
            sql_res = self.sql_tool.execute_query(input_data.sql_query)
            stat_summary = None
            if sql_res.is_success and sql_res.rows:
                # Optionally run statistical summary if numerical columns exist
                import pandas as pd
                df = pd.DataFrame(sql_res.rows)
                summary_obj = self.python_sandbox.calculate_statistical_summary(df)
                if summary_obj:
                    stat_summary = summary_obj.model_dump()

            return DataAgentOutput(
                is_success=sql_res.is_success,
                sql_executed=sql_res.sql,
                rows=sql_res.rows,
                row_count=sql_res.row_count,
                statistical_summary=stat_summary,
                error_message=sql_res.error_message,
                execution_time_ms=sql_res.execution_time_ms,
            )

        # If explicit Python script provided
        if input_data.python_script:
            py_res = self.python_sandbox.execute_script(input_data.python_script)
            stat_summary = py_res.statistical_summary.model_dump() if py_res.statistical_summary else None
            return DataAgentOutput(
                is_success=py_res.is_success,
                rows=py_res.result_data,
                row_count=len(py_res.result_data),
                statistical_summary=stat_summary,
                python_stdout=py_res.stdout,
                error_message=py_res.error_message,
                execution_time_ms=py_res.execution_time_ms,
            )

        # Automated data query resolution against table
        table_name = input_data.table_name or "queries"
        tables = self.sql_tool.list_tables()
        if table_name not in tables and tables:
            table_name = tables[0]

        auto_sql = f"SELECT * FROM {table_name} LIMIT 50"
        sql_res = self.sql_tool.execute_query(auto_sql)
        stat_summary = None
        if sql_res.is_success and sql_res.rows:
            import pandas as pd
            df = pd.DataFrame(sql_res.rows)
            summary_obj = self.python_sandbox.calculate_statistical_summary(df)
            if summary_obj:
                stat_summary = summary_obj.model_dump()

        return DataAgentOutput(
            is_success=sql_res.is_success,
            sql_executed=sql_res.sql,
            rows=sql_res.rows,
            row_count=sql_res.row_count,
            statistical_summary=stat_summary,
            error_message=sql_res.error_message,
            execution_time_ms=sql_res.execution_time_ms,
        )
