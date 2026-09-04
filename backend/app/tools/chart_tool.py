"""Chart Spec & Summary Table Generation Engine for Phase 7 (Data Visualization)."""
import uuid
import logging
from typing import Any, Dict, List, Optional, Tuple
from app.schemas.data_analysis import ChartSpecResponse

logger = logging.getLogger(__name__)


class ChartTool:
    """Programmatic generation of clean visualization specs and summary tables."""

    def build_vega_spec(
        self,
        title: str,
        chart_type: str,
        x_axis: str,
        y_axis: str,
        data: List[Dict[str, Any]],
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Constructs a standard Vega-Lite JSON visualization spec."""
        mark_type = "bar"
        if chart_type == "line":
            mark_type = "line"
        elif chart_type == "scatter":
            mark_type = "point"
        elif chart_type == "pie":
            mark_type = "arc"

        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title,
            "description": description or f"{chart_type.capitalize()} chart for {y_axis} by {x_axis}",
            "data": {"values": data},
            "mark": mark_type,
            "encoding": {
                "x": {"field": x_axis, "type": "nominal", "title": x_axis.capitalize()},
                "y": {"field": y_axis, "type": "quantitative", "title": y_axis.capitalize()},
                "tooltip": [{"field": x_axis}, {"field": y_axis}],
            },
        }

        if chart_type == "line":
            spec["encoding"]["x"]["type"] = "ordinal"
        elif chart_type == "pie":
            spec["encoding"] = {
                "theta": {"field": y_axis, "type": "quantitative"},
                "color": {"field": x_axis, "type": "nominal"},
            }

        return spec

    def extract_key_findings(self, data: List[Dict[str, Any]], x_axis: str, y_axis: str) -> List[str]:
        """Extracts statistical highlights and trend takeaways from data."""
        findings = []
        if not data:
            return ["No data points available for visual analysis."]

        valid_rows = [r for r in data if r.get(y_axis) is not None and isinstance(r.get(y_axis), (int, float))]
        if not valid_rows:
            return [f"Data contains {len(data)} rows across '{x_axis}' and '{y_axis}'."]

        y_vals = [r[y_axis] for r in valid_rows]
        max_row = max(valid_rows, key=lambda r: r[y_axis])
        min_row = min(valid_rows, key=lambda r: r[y_axis])
        avg_val = round(sum(y_vals) / len(y_vals), 2)

        findings.append(f"Peak value for {y_axis} was {max_row[y_axis]} recorded at {x_axis} '{max_row.get(x_axis)}'.")
        findings.append(f"Minimum value for {y_axis} was {min_row[y_axis]} recorded at {x_axis} '{min_row.get(x_axis)}'.")
        findings.append(f"Average {y_axis} across {len(valid_rows)} data categories was {avg_val}.")

        return findings

    def generate_chart_spec(
        self,
        title: str,
        chart_type: str,
        data: List[Dict[str, Any]],
        x_axis: Optional[str] = None,
        y_axis: Optional[str] = None,
        description: Optional[str] = None,
        query_id: Optional[uuid.UUID] = None,
    ) -> ChartSpecResponse:
        """Generates a complete ChartSpecResponse containing Vega-Lite JSON and summary table."""
        if not data:
            return ChartSpecResponse(
                id=uuid.uuid4(),
                query_id=query_id,
                title=title,
                chart_type=chart_type,
                description=description or "Empty dataset",
                spec_json={},
                table_data=[],
                key_findings=["No data provided."],
            )

        keys = list(data[0].keys())
        x_col = x_axis or (keys[0] if len(keys) > 0 else "x")
        y_col = y_axis or (keys[1] if len(keys) > 1 else keys[0])

        vega_spec = self.build_vega_spec(
            title=title,
            chart_type=chart_type,
            x_axis=x_col,
            y_axis=y_col,
            data=data,
            description=description,
        )

        findings = self.extract_key_findings(data, x_col, y_col)

        return ChartSpecResponse(
            id=uuid.uuid4(),
            query_id=query_id,
            title=title,
            chart_type=chart_type,
            description=description,
            spec_json=vega_spec,
            table_data=data[:50],  # Format top 50 rows for summary table
            key_findings=findings,
        )
