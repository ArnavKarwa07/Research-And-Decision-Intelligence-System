"""CSV & Structured File Handling and Profiling Tool for Phase 7 (Data Agent)."""
import os
import re
import sqlite3
import pandas as pd
import numpy as np
import logging
from typing import Any, Dict, List, Tuple, Optional
from app.schemas.data_analysis import DatasetProfileResponse, TableColumnInfo

logger = logging.getLogger(__name__)


class CSVTool:
    """CSV and Excel File Ingestion, Profiling, and In-Memory SQLite Table Creation Tool."""

    def __init__(self, db_path: str = "radis_dev.db") -> None:
        self.db_path = db_path

    def sanitize_identifier(self, name: str) -> str:
        """Sanitizes table or column names to alphanumeric + underscores."""
        clean = re.sub(r"[^a-zA-Z0-9_]", "_", str(name)).strip("_")
        if not clean or clean[0].isdigit():
            clean = f"col_{clean}"
        return clean.lower()

    def parse_file(self, file_path: str) -> Tuple[pd.DataFrame, str]:
        """Loads a CSV or Excel file into a pandas DataFrame."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".csv", ".txt"):
            df = pd.read_csv(file_path)
            file_type = "csv"
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
            file_type = "xlsx"
        else:
            raise ValueError(f"Unsupported structured file format: {ext}")

        # Sanitize column headers
        df.columns = [self.sanitize_identifier(col) for col in df.columns]
        return df, file_type

    def ingest_to_sqlite(self, file_path: str, custom_table_name: Optional[str] = None) -> Tuple[str, pd.DataFrame]:
        """Ingests CSV/Excel file into SQLite database table."""
        df, file_type = self.parse_file(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        table_name = self.sanitize_identifier(custom_table_name or f"data_{base_name}")

        conn = sqlite3.connect(self.db_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.close()
        logger.info(f"Ingested {len(df)} rows into SQLite table '{table_name}' from {file_path}")

        return table_name, df

    def profile_dataframe(self, df: pd.DataFrame, table_name: str, filename: str, file_type: str) -> DatasetProfileResponse:
        """Generates comprehensive summary profile of a tabular dataset."""
        columns_info = []
        summary_stats = {}

        for col in df.columns:
            dtype_str = str(df[col].dtype)
            sql_type = "INTEGER" if "int" in dtype_str else ("REAL" if "float" in dtype_str else "TEXT")
            has_nulls = df[col].isnull().any()

            columns_info.append(
                TableColumnInfo(
                    name=col,
                    data_type=sql_type,
                    nullable=bool(has_nulls),
                    primary_key=False,
                )
            )

            # Calculate numerical column summary stats if numeric
            if pd.api.types.is_numeric_dtype(df[col]):
                summary_stats[col] = {
                    "count": int(df[col].count()),
                    "mean": float(np.round(df[col].mean(), 4)) if not df[col].isnull().all() else None,
                    "std": float(np.round(df[col].std(), 4)) if not df[col].isnull().all() and len(df[col].dropna()) > 1 else None,
                    "min": float(np.round(df[col].min(), 4)) if not df[col].isnull().all() else None,
                    "max": float(np.round(df[col].max(), 4)) if not df[col].isnull().all() else None,
                    "median": float(np.round(df[col].median(), 4)) if not df[col].isnull().all() else None,
                    "missing_count": int(df[col].isnull().sum()),
                }
            else:
                summary_stats[col] = {
                    "count": int(df[col].count()),
                    "unique_values": int(df[col].nunique()),
                    "missing_count": int(df[col].isnull().sum()),
                }

        # Convert sample rows safely (handling NaNs)
        sample_df = df.head(5).replace({np.nan: None})
        sample_rows = sample_df.to_dict(orient="records")

        import uuid
        return DatasetProfileResponse(
            dataset_id=uuid.uuid4(),
            filename=filename,
            file_type=file_type,
            table_name=table_name,
            row_count=len(df),
            column_count=len(df.columns),
            columns=columns_info,
            summary_stats=summary_stats,
            sample_rows=sample_rows,
        )
