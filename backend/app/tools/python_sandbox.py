"""Sandboxed Python Execution & Statistical Analysis Engine for Phase 7 (Data Agent)."""
import ast
import io
import math
import sys
import time
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

from app.schemas.data_analysis import PythonAnalysisResponse, StatisticalSummary

logger = logging.getLogger(__name__)

# Strictly forbidden Python AST node types & module names
FORBIDDEN_AST_NODES = {
    ast.Import, ast.ImportFrom
}


FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "http", "urllib", "requests",
    "importlib", "ctypes", "multiprocessing", "threading", "pathlib"
}

FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "__import__", "open", "file", "input",
    "globals", "locals", "vars", "dir", "getattr", "setattr", "delattr", "hasattr"
}


class ASTSecurityChecker(ast.NodeVisitor):
    """AST Visitor that validates Python code safety before execution."""

    def __init__(self) -> None:
        self.errors: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                self.errors.append(f"Forbidden module import: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.split(".")[0] in FORBIDDEN_MODULES:
            self.errors.append(f"Forbidden module import: '{node.module}'")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in FORBIDDEN_NAMES or node.id.startswith("__"):
            self.errors.append(f"Forbidden function or variable access: '{node.id}'")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__"):
            self.errors.append(f"Forbidden dunder attribute access: '{node.attr}'")
        self.generic_visit(node)


class PythonSandboxTool:
    """Secure Sandboxed Python Analysis Engine."""

    def validate_code_safety(self, python_code: str) -> Optional[str]:
        """Parses AST and validates code safety against security rules."""
        try:
            tree = ast.parse(python_code)
        except SyntaxError as se:
            return f"Syntax Error: {se.msg} at line {se.lineno}"

        checker = ASTSecurityChecker()
        checker.visit(tree)
        if checker.errors:
            return f"Sandbox Security Violation: {'; '.join(checker.errors)}"
        return None

    def calculate_statistical_summary(self, df: pd.DataFrame) -> Optional[StatisticalSummary]:
        """Calculates statistical summary metrics for numeric columns in DataFrame."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            return None

        primary_col = numeric_cols[0]
        series = df[primary_col].dropna()
        if len(series) == 0:
            return None

        mean_val = float(np.round(series.mean(), 4))
        std_val = float(np.round(series.std(), 4)) if len(series) > 1 else 0.0
        median_val = float(np.round(series.median(), 4))
        min_val = float(np.round(series.min(), 4))
        max_val = float(np.round(series.max(), 4))
        p25_val = float(np.round(series.quantile(0.25), 4))
        p75_val = float(np.round(series.quantile(0.75), 4))

        # Correlation matrix
        correlations = {}
        if len(numeric_cols) > 1:
            corr_df = df[numeric_cols].corr()
            for c in numeric_cols:
                if c != primary_col and not math.isnan(corr_df.loc[primary_col, c]):
                    correlations[c] = float(np.round(corr_df.loc[primary_col, c], 4))

        # Trend direction
        trend_direction = "stable"
        if len(series) >= 3:
            first_half = series.iloc[: len(series) // 2].mean()
            second_half = series.iloc[len(series) // 2 :].mean()
            diff = second_half - first_half
            if abs(diff) > 0.05 * (abs(mean_val) + 1e-5):
                trend_direction = "increasing" if diff > 0 else "decreasing"

        return StatisticalSummary(
            metric_name=primary_col,
            count=len(series),
            mean=mean_val,
            std_dev=std_val,
            min_val=min_val,
            max_val=max_val,
            median=median_val,
            p25=p25_val,
            p75=p75_val,
            correlations=correlations,
            trend_direction=trend_direction,
        )

    def execute_script(
        self,
        python_code: str,
        input_data: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: float = 5.0,
    ) -> PythonAnalysisResponse:
        """Executes a Python script in a restricted sandbox scope."""
        start_time = time.time()

        # AST Security Validation
        sec_error = self.validate_code_safety(python_code)
        if sec_error:
            return PythonAnalysisResponse(
                is_success=False,
                error_message=sec_error,
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
            )

        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            mod_root = name.split(".")[0]
            if mod_root in FORBIDDEN_MODULES:
                raise ImportError(f"Forbidden module import: '{name}'")
            return __import__(name, globals, locals, fromlist, level)

        # Prepare safe execution global scope
        df = pd.DataFrame(input_data) if input_data else pd.DataFrame()
        safe_globals = {
            "pd": pd,
            "np": np,
            "math": math,
            "df": df,
            "result": None,
            "__builtins__": {
                "__import__": safe_import,
                "range": range,
                "len": len,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "bool": bool,
                "zip": zip,
                "enumerate": enumerate,
                "abs": abs,
                "round": round,
                "sum": sum,
                "min": min,
                "max": max,
                "sorted": sorted,
                "print": print,
                "isinstance": isinstance,
            },
        }


        # Intercept stdout/stderr
        stdout_capture = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_capture

        try:
            exec(python_code, safe_globals)
            sys.stdout = old_stdout
            stdout_text = stdout_capture.getvalue()

            # Extract result variable or df
            res_obj = safe_globals.get("result")
            result_data = []
            stat_summary = None

            if isinstance(res_obj, pd.DataFrame):
                result_data = res_obj.replace({np.nan: None}).to_dict(orient="records")
                stat_summary = self.calculate_statistical_summary(res_obj)
            elif isinstance(res_obj, list):
                result_data = res_obj
            elif isinstance(res_obj, dict):
                result_data = [res_obj]
            elif not df.empty:
                result_data = df.replace({np.nan: None}).head(100).to_dict(orient="records")
                stat_summary = self.calculate_statistical_summary(df)

            exec_time = round((time.time() - start_time) * 1000, 2)
            return PythonAnalysisResponse(
                is_success=True,
                stdout=stdout_text,
                result_data=result_data,
                statistical_summary=stat_summary,
                execution_time_ms=exec_time,
            )
        except Exception as e:
            sys.stdout = old_stdout
            exec_time = round((time.time() - start_time) * 1000, 2)
            logger.error(f"Python sandbox execution failed: {e}")
            return PythonAnalysisResponse(
                is_success=False,
                stderr=str(e),
                error_message=f"Runtime Error: {str(e)}",
                execution_time_ms=exec_time,
            )
