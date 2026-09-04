"""API Router for Data Analysis, Datasets, SQL Execution, Sandbox, and Visualizations."""
import os
import uuid
import tempfile
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
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
from app.services.data_service import DataService

router = APIRouter(prefix="/data", tags=["Data Agent & Visualization"])


@router.post("/datasets/upload", response_model=DatasetProfileResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Uploads a CSV or Excel dataset, ingests it into SQLite, and returns profile info."""
    filename = file.filename or "uploaded_data.csv"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Only .csv, .xlsx, .xls are allowed.",
        )

    # Save to temp file
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        service = DataService(db_session=db)
        profile = service.process_dataset_upload(file_path, filename)
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dataset processing failed: {str(e)}",
        )


@router.get("/datasets/{dataset_id}/schema", response_model=DatasetProfileResponse)
def get_dataset_schema(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Retrieves column schema and metadata for an uploaded dataset."""
    service = DataService(db_session=db)
    profile = service.get_dataset_schema(dataset_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found.",
        )
    return profile


@router.post("/query", response_model=SQLQueryResponse)
def execute_sql_query(
    req: SQLQueryRequest,
    query_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
):
    """Executes a read-only SQL query with safety validation."""
    service = DataService(db_session=db)
    res = service.execute_sql_query(req, query_id=query_id)
    if not res.is_success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.error_message,
        )
    return res


@router.post("/analyze", response_model=PythonAnalysisResponse)
def execute_python_analysis(
    req: PythonAnalysisRequest,
    query_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
):
    """Executes a Python script in a secure sandbox scope."""
    service = DataService(db_session=db)
    res = service.execute_python_analysis(req, query_id=query_id)
    if not res.is_success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.error_message,
        )
    return res


@router.post("/visualize", response_model=ChartSpecResponse, status_code=status.HTTP_201_CREATED)
def create_visualization(
    req: ChartSpecRequest,
    query_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
):
    """Generates visualization spec and summary table."""
    service = DataService(db_session=db)
    return service.generate_visualization(req, query_id=query_id)


@router.get("/artifacts/{query_id}", response_model=ReproducibleArtifactResponse)
def get_reproducible_artifact(
    query_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Retrieves reproducible analysis artifact bundle for a query."""
    service = DataService(db_session=db)
    artifact = service.get_reproducible_artifact(query_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reproducible artifact for query '{query_id}' not found.",
        )
    return artifact
