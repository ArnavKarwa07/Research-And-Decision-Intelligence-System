"""Benchmark Dataset Management & Seeding Service."""
import logging
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.eval_benchmark import GoldenDataset, GoldenTestCase
from app.schemas.eval import GoldenDatasetCreate, GoldenTestCaseCreate

logger = logging.getLogger(__name__)

# Pre-seeded Standard Golden Evaluation Cases
PRESEEDED_GOLDEN_DATASETS: list[dict[str, Any]] = [
    {
        "name": "Market & Strategic Decision Benchmark v1",
        "description": "Standard benchmark dataset covering market analysis, technical feasibility, financial ROI, and strategic positioning decisions.",
        "version": "1.0.0",
        "category": "strategic_decision",
        "test_cases": [
            {
                "query_text": "Should Enterprise Corp migrate customer database workload from AWS Aurora PostgreSQL to Neon Serverless PostgreSQL?",
                "category": "technical_feasibility",
                "ground_truth_claims": [
                    {"text": "Neon supports autoscaling computing endpoints that scale down to zero.", "is_supported": True, "confidence": 0.95},
                    {"text": "Aurora PostgreSQL provides multi-region global database replication.", "is_supported": True, "confidence": 0.95},
                    {"text": "Neon branching allows instant database copy creation for preview environments.", "is_supported": True, "confidence": 0.90},
                ],
                "required_sources": ["neon.tech", "aws.amazon.com"],
                "expected_decision_matrix": {
                    "criteria": [
                        {"name": "Cost Reduction", "weight": 0.35},
                        {"name": "Developer Velocity", "weight": 0.30},
                        {"name": "High Availability & SLA", "weight": 0.20},
                        {"name": "Migration Complexity", "weight": 0.15},
                    ],
                    "sensitivity_points": [{"criterion": "Cost Reduction", "threshold": 0.40}],
                },
                "expected_rankings": ["Neon Serverless PostgreSQL", "AWS Aurora PostgreSQL", "Self-hosted PostgreSQL"],
            },
            {
                "query_text": "Evaluate commercial viability of launching an AI-assisted diagnostic assistant for radiology clinics.",
                "category": "market_analysis",
                "ground_truth_claims": [
                    {"text": "FDA 510(k) clearance is required for AI software acting as medical devices.", "is_supported": True, "confidence": 0.98},
                    {"text": "Radiologist burnout rate exceeds 45% due to high imaging volume.", "is_supported": True, "confidence": 0.90},
                ],
                "required_sources": ["fda.gov", "ncbi.nlm.nih.gov"],
                "expected_decision_matrix": {
                    "criteria": [
                        {"name": "Regulatory Compliance", "weight": 0.40},
                        {"name": "Market Demand", "weight": 0.30},
                        {"name": "Unit Economics", "weight": 0.30},
                    ],
                    "sensitivity_points": [{"criterion": "Regulatory Compliance", "threshold": 0.50}],
                },
                "expected_rankings": ["Phased Triage Copilot", "Full Autonomous Diagnostic Tool", "Status Quo Manual Reading"],
            },
            {
                "query_text": "Calculate financial ROI and payback period of adopting Rust over C++ for low-latency trading infrastructure.",
                "category": "financial_evaluation",
                "ground_truth_claims": [
                    {"text": "Rust guarantees memory safety without garbage collection overhead.", "is_supported": True, "confidence": 0.96},
                    {"text": "C++ memory corruption vulnerabilities account for over 60% of critical security patches.", "is_supported": True, "confidence": 0.92},
                ],
                "required_sources": ["rust-lang.org", "isocpp.org"],
                "expected_decision_matrix": {
                    "criteria": [
                        {"name": "Security & Stability", "weight": 0.40},
                        {"name": "Latency Performance", "weight": 0.35},
                        {"name": "Refactoring Cost", "weight": 0.25},
                    ],
                    "sensitivity_points": [{"criterion": "Latency Performance", "threshold": 0.45}],
                },
                "expected_rankings": ["Incremental Rust Migration", "Full C++ Modernization", "Full Rust Rewrite"],
            },
        ],
    }
]


class EvalBenchmarkService:
    """Service for managing golden datasets and evaluation test cases."""

    def __init__(self, db: Session):
        self.db = db

    def seed_default_datasets(self) -> list[GoldenDataset]:
        """Seed default golden datasets if none exist."""
        seeded: list[GoldenDataset] = []

        for ds_data in PRESEEDED_GOLDEN_DATASETS:
            existing = self.db.scalar(
                select(GoldenDataset).where(GoldenDataset.name == ds_data["name"])
            )
            if existing:
                seeded.append(existing)
                continue

            dataset = GoldenDataset(
                name=ds_data["name"],
                description=ds_data.get("description"),
                version=ds_data.get("version", "1.0.0"),
                category=ds_data.get("category", "general"),
            )
            self.db.add(dataset)
            self.db.flush()

            for tc_data in ds_data.get("test_cases", []):
                test_case = GoldenTestCase(
                    dataset_id=dataset.id,
                    query_text=tc_data["query_text"],
                    category=tc_data.get("category", "general"),
                    ground_truth_claims=tc_data.get("ground_truth_claims", []),
                    required_sources=tc_data.get("required_sources", []),
                    expected_decision_matrix=tc_data.get("expected_decision_matrix", {}),
                    expected_rankings=tc_data.get("expected_rankings", []),
                )
                self.db.add(test_case)

            self.db.commit()
            self.db.refresh(dataset)
            seeded.append(dataset)
            logger.info(f"Seeded golden dataset '{dataset.name}' with {len(dataset.test_cases)} test cases.")

        return seeded

    def create_dataset(self, data: GoldenDatasetCreate) -> GoldenDataset:
        """Create a new golden dataset with optional test cases."""
        dataset = GoldenDataset(
            name=data.name,
            description=data.description,
            version=data.version,
            category=data.category,
        )
        self.db.add(dataset)
        self.db.flush()

        for tc in data.test_cases:
            test_case = GoldenTestCase(
                dataset_id=dataset.id,
                query_text=tc.query_text,
                category=tc.category,
                ground_truth_claims=tc.ground_truth_claims,
                required_sources=tc.required_sources,
                expected_decision_matrix=tc.expected_decision_matrix,
                expected_rankings=tc.expected_rankings,
            )
            self.db.add(test_case)

        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def list_datasets(self) -> list[GoldenDataset]:
        """List all golden datasets."""
        stmt = select(GoldenDataset).order_by(GoldenDataset.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_dataset(self, dataset_id: str) -> Optional[GoldenDataset]:
        """Get dataset by ID."""
        return self.db.scalar(select(GoldenDataset).where(GoldenDataset.id == dataset_id))

    def add_test_case(self, dataset_id: str, data: GoldenTestCaseCreate) -> Optional[GoldenTestCase]:
        """Add a test case to an existing dataset."""
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            return None

        test_case = GoldenTestCase(
            dataset_id=dataset_id,
            query_text=data.query_text,
            category=data.category,
            ground_truth_claims=data.ground_truth_claims,
            required_sources=data.required_sources,
            expected_decision_matrix=data.expected_decision_matrix,
            expected_rankings=data.expected_rankings,
        )
        self.db.add(test_case)
        self.db.commit()
        self.db.refresh(test_case)
        return test_case
