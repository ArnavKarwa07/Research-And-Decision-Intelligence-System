"""Comprehensive Unit and Integration Tests for Phase 7 (Data Agent & Data Visualization)."""
import os
import tempfile
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.dependencies import get_db
from app.models.base import Base

from app.tools.sql_tool import SQLTool
from app.tools.csv_tool import CSVTool
from app.tools.python_sandbox import PythonSandboxTool
from app.tools.chart_tool import ChartTool
from app.agents.data_agent import DataInvestigationAgent
from app.agents.visualization_agent import DataVisualizationAgent
from app.agents.agent_contracts import DataAgentInput, DataVisualizationInput
from app.schemas.data_analysis import SQLQueryRequest, PythonAnalysisRequest, ChartSpecRequest

# Setup test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_phase7.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db_override():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()

client = TestClient(app)


# --- 1. SQLTool Unit Tests ---
def test_sql_tool_valid_query():
    tool = SQLTool(db_path="test_phase7.db")
    res = tool.execute_query("SELECT 1 AS num, 'test' AS name")
    assert res.is_success is True
    assert res.row_count == 1
    assert res.rows[0]["num"] == 1
    assert res.rows[0]["name"] == "test"


def test_sql_tool_blocks_mutation():
    tool = SQLTool(db_path="test_phase7.db")
    res = tool.execute_query("DROP TABLE queries;")
    assert res.is_success is False
    assert "Forbidden non-read-only SQL keyword" in res.error_message


def test_sql_tool_blocks_multi_statements():
    tool = SQLTool(db_path="test_phase7.db")
    res = tool.execute_query("SELECT 1; SELECT 2;")
    assert res.is_success is False
    assert "Multiple SQL statements are strictly forbidden" in res.error_message


# --- 2. CSVTool Unit Tests ---
def test_csv_tool_ingest_and_profile():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("Category,Revenue,Sales_Count\nA,100.5,10\nB,200.0,20\nC,150.2,15\n")
        f_path = f.name

    try:
        tool = CSVTool(db_path="test_phase7.db")
        table_name, df = tool.ingest_to_sqlite(f_path, custom_table_name="test_revenue")
        assert table_name == "test_revenue"
        assert len(df) == 3

        profile = tool.profile_dataframe(df, table_name, "test.csv", "csv")
        assert profile.row_count == 3
        assert profile.column_count == 3
        assert "revenue" in profile.summary_stats
        assert profile.summary_stats["revenue"]["mean"] == 150.2333
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


# --- 3. PythonSandboxTool Security & Calculation Tests ---
def test_python_sandbox_ast_security():
    sandbox = PythonSandboxTool()
    res = sandbox.execute_script("import os\nos.system('echo hacked')")
    assert res.is_success is False
    assert "Forbidden module import" in res.error_message


def test_python_sandbox_dunder_blocking():
    sandbox = PythonSandboxTool()
    res = sandbox.execute_script("x = (1).__class__")
    assert res.is_success is False
    assert "Forbidden dunder attribute access" in res.error_message


def test_python_sandbox_valid_pandas_calc():
    sandbox = PythonSandboxTool()
    code = "import pandas as pd\ndf['double_val'] = df['val'] * 2\nresult = df"
    data = [{"val": 10}, {"val": 20}]
    res = sandbox.execute_script(code, input_data=data)
    assert res.is_success is True
    assert len(res.result_data) == 2
    assert res.result_data[0]["double_val"] == 20


# --- 4. ChartTool Unit Tests ---
def test_chart_tool_generation():
    tool = ChartTool()
    data = [{"month": "Jan", "sales": 100}, {"month": "Feb", "sales": 250}]
    res = tool.generate_chart_spec(
        title="Monthly Sales",
        chart_type="bar",
        data=data,
        x_axis="month",
        y_axis="sales",
    )
    assert res.title == "Monthly Sales"
    assert res.chart_type == "bar"
    assert "mark" in res.spec_json
    assert len(res.key_findings) > 0


# --- 5. Data Agent & Visualization Agent Contract Tests ---
def test_data_investigation_agent():
    agent = DataInvestigationAgent(db_path="test_phase7.db")
    inp = DataAgentInput(query="Show me queries", sql_query="SELECT 1 AS col")
    out = agent.run(inp)
    assert out.is_success is True
    assert out.row_count == 1


def test_data_visualization_agent():
    agent = DataVisualizationAgent()
    inp = DataVisualizationInput(
        title="Test Chart",
        chart_type="line",
        data=[{"x": 1, "y": 10}, {"x": 2, "y": 20}],
    )
    out = agent.run(inp)
    assert out.spec_json["mark"] == "line"
    assert len(out.key_findings) > 0


# --- 6. REST API Integration Tests ---
def test_api_sql_query_endpoint():
    payload = {"sql": "SELECT 42 AS answer", "limit": 10}
    response = client.post("/api/v1/data/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_success"] is True
    assert data["rows"][0]["answer"] == 42


def test_api_python_analyze_endpoint():
    payload = {
        "python_code": "df['res'] = df['a'] + df['b']\nresult = df",
        "input_data": [{"a": 5, "b": 10}]
    }
    response = client.post("/api/v1/data/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_success"] is True
    assert data["result_data"][0]["res"] == 15


def test_api_visualize_endpoint():
    payload = {
        "title": "API Test Chart",
        "chart_type": "bar",
        "data": [{"cat": "A", "val": 10}, {"cat": "B", "val": 30}]
    }
    response = client.post("/api/v1/data/visualize", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "API Test Chart"
