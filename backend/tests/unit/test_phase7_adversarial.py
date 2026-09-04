"""Adversarial Security Audit for Phase 7 (Data Agent & Data Visualization).
Aggressively audits:
1. SQL Injection & Non-Read-Only Mutation Attacks
2. Sandbox Escape Attempts & AST Bypass Vectors
3. Division by Zero & Float Overflow/NaN Edge Cases
4. Malformed CSV Ingestion Edge Cases
5. Missing Parameters & Null Payload Defensive Validation
"""
import pytest
from app.tools.sql_tool import SQLTool
from app.tools.python_sandbox import PythonSandboxTool
from app.tools.csv_tool import CSVTool
from app.tools.chart_tool import ChartTool


# --- 1. SQL Injection & Non-Read-Only Attacks ---
def test_adversarial_sql_injection_union():
    tool = SQLTool()
    # Union injection with forbidden keyword inside substring
    res = tool.execute_query("SELECT * FROM queries WHERE id = 1 UNION SELECT 1, 'DROP TABLE queries'")
    # Must fail because DROP keyword is present
    assert res.is_success is False
    assert "Forbidden non-read-only SQL keyword" in res.error_message


def test_adversarial_sql_injection_semicolon_chained():
    tool = SQLTool()
    res = tool.execute_query("SELECT * FROM queries; DELETE FROM queries;")
    assert res.is_success is False
    assert "Multiple SQL statements are strictly forbidden" in res.error_message


def test_adversarial_sql_comment_bypass():
    tool = SQLTool()
    res = tool.execute_query("INSERT INTO queries DEFAULT VALUES;")
    assert res.is_success is False
    assert "Forbidden non-read-only SQL keyword" in res.error_message


# --- 2. Sandbox Escape Attempts & AST Bypass Vectors ---
def test_adversarial_sandbox_escape_importlib():
    sandbox = PythonSandboxTool()
    code = "__import__('os').system('calc')"
    res = sandbox.execute_script(code)
    assert res.is_success is False
    assert "Forbidden function or variable access" in res.error_message


def test_adversarial_sandbox_escape_subclasses():
    sandbox = PythonSandboxTool()
    code = "x = ().__class__.__base__.__subclasses__()"
    res = sandbox.execute_script(code)
    assert res.is_success is False
    assert "Forbidden dunder attribute access" in res.error_message


def test_adversarial_sandbox_eval_nesting():
    sandbox = PythonSandboxTool()
    code = "eval('1 + 1')"
    res = sandbox.execute_script(code)
    assert res.is_success is False
    assert "Forbidden function or variable access" in res.error_message


# --- 3. Division by Zero & Float Overflow Edge Cases ---
def test_adversarial_division_by_zero():
    sandbox = PythonSandboxTool()
    code = "x = 10 / 0"
    res = sandbox.execute_script(code)
    assert res.is_success is False
    assert "ZeroDivisionError" in res.error_message or "division by zero" in res.error_message.lower()


def test_adversarial_float_infinity():
    sandbox = PythonSandboxTool()
    code = "import math\nx = math.exp(1000)"
    res = sandbox.execute_script(code)
    assert res.is_success is False
    assert "OverflowError" in res.error_message or "math range error" in res.error_message.lower()


# --- 4. Malformed Data & Empty Payloads ---
def test_adversarial_chart_tool_empty_data():
    tool = ChartTool()
    res = tool.generate_chart_spec("Empty Chart", "bar", data=[])
    assert res.title == "Empty Chart"
    assert res.table_data == []
    assert "No data provided" in res.key_findings[0]


def test_adversarial_csv_sanitization_special_chars():
    tool = CSVTool()
    sanitized = tool.sanitize_identifier("123-Bad Name!! @#$%")
    assert sanitized.startswith("col_")
    assert "!" not in sanitized
    assert "@" not in sanitized
