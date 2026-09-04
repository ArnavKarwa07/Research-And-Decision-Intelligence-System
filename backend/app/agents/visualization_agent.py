"""Data Visualization Agent for Phase 7 (Data Visualization)."""
import uuid
import logging
from typing import Any, Dict, Optional
from app.agents.agent_contracts import DataVisualizationInput, DataVisualizationOutput
from app.tools.chart_tool import ChartTool

logger = logging.getLogger(__name__)


class DataVisualizationAgent:
    """Specialist agent for programmatic chart generation, summary tables, and visual insights."""

    def __init__(self) -> None:
        self.chart_tool = ChartTool()

    def run(self, input_data: DataVisualizationInput) -> DataVisualizationOutput:
        """Transforms structured data into visualization specs and key findings."""
        logger.info(f"[DataVisualizationAgent] Generating chart '{input_data.title}' ({input_data.chart_type})")

        spec_res = self.chart_tool.generate_chart_spec(
            title=input_data.title,
            chart_type=input_data.chart_type,
            data=input_data.data,
            x_axis=input_data.x_axis,
            y_axis=input_data.y_axis,
            description=input_data.description,
            query_id=uuid.UUID(input_data.query_id) if input_data.query_id else None,
        )

        return DataVisualizationOutput(
            spec_json=spec_res.spec_json,
            table_data=spec_res.table_data,
            key_findings=spec_res.key_findings,
            reproducible_artifact_id=str(spec_res.id),
        )
