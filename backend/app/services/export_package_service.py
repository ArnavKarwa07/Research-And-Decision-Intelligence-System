"""ExportPackageService for bundling multi-format research ZIP packages in Phase 11."""
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.query import Query
from app.models.claim import Claim
from app.models.source import Source
from app.models.decision import Decision
from app.services.artifact_service import ArtifactService


class ExportPackageService:
    """Bundles research findings, decision memos, graphs, sources, and CSVs into a downloadable ZIP archive."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.artifact_service = ArtifactService(db)

    async def generate_zip_package(self, query_id: uuid.UUID) -> Tuple[io.BytesIO, str]:
        """Compile complete multi-format research export package into a ZIP byte buffer."""
        query_stmt = select(Query).where(Query.id == query_id)
        q_res = await self.db.execute(query_stmt)
        query_obj = q_res.scalars().first()
        if not query_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query with ID '{query_id}' not found."
            )

        # Generate Decision Memo & Research Report
        decision_memo = await self.artifact_service.get_or_create_decision_memo(query_id)
        research_report = await self.artifact_service.generate_research_report(query_id)
        comparison_table = await self.artifact_service.export_comparison_table(query_id)

        # Fetch raw sources and claims
        claims_stmt = select(Claim).where(Claim.query_id == query_id)
        claims_res = await self.db.execute(claims_stmt)
        claims_list = list(claims_res.scalars().all())

        sources_stmt = select(Source)
        sources_res = await self.db.execute(sources_stmt)
        sources_list = list(sources_res.scalars().all())

        dec_stmt = select(Decision).where(Decision.query_id == query_id)
        dec_res = await self.db.execute(dec_stmt)
        decision_obj = dec_res.scalars().first()

        # Build Sources Manifest CSV
        sources_csv_lines = ["Source ID,Title,Publisher,Quality Score,Source Type,URL,Created At"]
        for s in sources_list:
            sources_csv_lines.append(
                f'"{s.id}","{s.title or ""}","{s.publisher or ""}","{s.quality_score or 0.85}","{s.source_type or "web"}","{s.url or ""}","{s.created_at}"'
            )
        sources_csv_content = "\n".join(sources_csv_lines)

        # Build Full JSON State Dump
        research_state = {
            "query": {
                "id": str(query_obj.id),
                "text": query_obj.text,
                "status": query_obj.status,
                "confidence": query_obj.confidence,
                "summary": query_obj.summary,
                "research_plan": query_obj.research_plan,
            },
            "decision": {
                "recommendation": decision_obj.recommendation if decision_obj else None,
                "confidence": decision_obj.confidence if decision_obj else None,
                "alternatives": decision_obj.alternatives if decision_obj else [],
                "criteria": decision_obj.criteria if decision_obj else [],
                "scenarios": decision_obj.scenarios if decision_obj else {},
                "key_risks": decision_obj.key_risks if decision_obj else [],
                "assumptions": decision_obj.assumptions if decision_obj else [],
            } if decision_obj else None,
            "claims": [
                {
                    "id": str(c.id),
                    "text": getattr(c, "content", getattr(c, "text", "")),
                    "claim_type": c.claim_type,
                    "confidence": c.confidence,
                    "verification_status": getattr(c, "status", getattr(c, "verification_status", "verified")),
                }
                for c in claims_list
            ],

            "sources": [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "publisher": s.publisher,
                    "quality_score": s.quality_score,
                    "url": s.url,
                    "source_type": s.source_type,
                }
                for s in sources_list
            ],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        json_dump_content = json.dumps(research_state, indent=2)

        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("decision_memo.md", decision_memo.markdown_content)
            zip_file.writestr("research_report.md", research_report.markdown_content)
            zip_file.writestr("executive_summary.html", decision_memo.html_content)
            zip_file.writestr("research_state.json", json_dump_content)
            zip_file.writestr("sources_manifest.csv", sources_csv_content)
            zip_file.writestr("mcda_comparison.csv", comparison_table.csv_spec)

        zip_buffer.seek(0)
        filename = f"radis_research_export_{str(query_id)[:8]}.zip"
        return zip_buffer, filename
