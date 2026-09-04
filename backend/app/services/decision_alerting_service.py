"""Decision Alerting Service for Phase 12 Continuous Intelligence."""
import asyncio
import ipaddress
import logging
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import (
    AlertSeverity,
    AlertStatus,
    DecisionAlert,
    MaterialityLevel,
    WebhookStatus,
)
from app.models.audit_log import AuditLog
from app.schemas.monitoring import MaterialityScoreBreakdown

logger = logging.getLogger(__name__)

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
]


def is_safe_webhook_url(url: str) -> bool:
    """
    Validate URL scheme (http/https) and parse/resolve host IP to block private,
    loopback, and link-local IP ranges.
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        if hostname.lower() in ("localhost", "localhost.localdomain"):
            return False

        ip_objs = []
        try:
            ip_objs.append(ipaddress.ip_address(hostname))
        except ValueError:
            try:
                addr_info = socket.getaddrinfo(hostname, None)
                for info in addr_info:
                    ip_str = info[4][0]
                    ip_objs.append(ipaddress.ip_address(ip_str))
            except (socket.gaierror, socket.herror, Exception):
                pass

        for ip in ip_objs:
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
                or ip.is_unspecified
            ):
                return False

            for net in BLOCKED_IP_NETWORKS:
                if ip in net:
                    return False

        return True
    except Exception:
        return False


class DecisionAlertingService:
    """
    Evaluates materiality scores against thresholds, creates DecisionAlert database records,
    and dispatches notifications via HTTP webhooks with retry policies and audit logging.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def evaluate_and_create_alert(
        self,
        job_id: UUID,
        execution_log_id: Optional[UUID],
        materiality_score: float,
        threshold: float,
        delta_summary: Dict[str, Any],
        project_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        webhook_url: Optional[str] = None,
    ) -> Optional[DecisionAlert]:
        """
        Evaluate materiality score against threshold. If score >= threshold,
        create and persist DecisionAlert. Automatically trigger webhook dispatch if webhook_url provided.
        """
        if materiality_score < threshold:
            logger.info(
                f"Materiality score {materiality_score:.4f} is below threshold {threshold:.4f}. No alert created."
            )
            return None

        # Determine severity based on score & level
        if materiality_score >= 0.8:
            severity = AlertSeverity.CRITICAL.value
        elif materiality_score >= 0.6:
            severity = AlertSeverity.HIGH.value
        elif materiality_score >= 0.4:
            severity = AlertSeverity.WARNING.value
        else:
            severity = AlertSeverity.INFO.value

        title = f"Decision Alert: {severity} Materiality Delta ({materiality_score:.2f})"
        summary_msg = delta_summary.get("summary") or "Materiality threshold breached by recent research run."
        message = f"{title} - {summary_msg}"

        alert = DecisionAlert(
            job_id=job_id,
            execution_log_id=execution_log_id,
            project_id=project_id,
            session_id=session_id,
            materiality_score=materiality_score,
            severity=severity,
            title=title,
            message=message,
            payload=delta_summary,
            status=AlertStatus.UNREAD.value,
            webhook_status=WebhookStatus.NONE.value,
        )

        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        # Audit log creation
        audit_log = AuditLog(
            action_type="decision_alert_created",
            severity=severity,
            details={
                "alert_id": str(alert.id),
                "job_id": str(job_id),
                "materiality_score": materiality_score,
                "threshold": threshold,
            },
        )
        self.db.add(audit_log)
        await self.db.commit()

        if webhook_url:
            await self.dispatch_webhook(alert=alert, webhook_url=webhook_url)

        return alert

    async def dispatch_webhook(
        self,
        alert: DecisionAlert,
        webhook_url: str,
        max_retries: int = 3,
        backoff_base: float = 0.05,
    ) -> WebhookStatus:
        """
        Dispatch alert payload to HTTP Webhook with retry policy (up to 3 retries with exponential backoff)
        and audit logging.
        """
        if not webhook_url:
            return WebhookStatus.NONE

        if not is_safe_webhook_url(webhook_url):
            logger.warning(f"SSRF validation blocked unsafe webhook URL '{webhook_url}'.")
            alert.webhook_status = WebhookStatus.FAILED.value
            await self.db.commit()
            await self.db.refresh(alert)
            return WebhookStatus.FAILED

        payload = {
            "alert_id": str(alert.id),
            "job_id": str(alert.job_id),
            "materiality_score": alert.materiality_score,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "payload": alert.payload,
            "created_at": alert.created_at.isoformat() if alert.created_at else datetime.now(timezone.utc).isoformat(),
        }

        delivered = False
        last_error: Optional[str] = None

        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(1, max_retries + 1):
                try:
                    response = await client.post(webhook_url, json=payload)
                    if response.status_code in (200, 201, 202, 204):
                        delivered = True
                        logger.info(
                            f"Webhook delivered successfully to {webhook_url} on attempt {attempt}."
                        )
                        break
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text}"
                        logger.warning(
                            f"Webhook delivery attempt {attempt} failed with status {response.status_code}."
                        )
                except Exception as exc:
                    last_error = str(exc)
                    logger.warning(f"Webhook delivery attempt {attempt} exception: {exc}")

                if attempt < max_retries:
                    delay = backoff_base * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

        final_status = WebhookStatus.DELIVERED if delivered else WebhookStatus.FAILED
        alert.webhook_status = final_status.value
        await self.db.commit()
        await self.db.refresh(alert)

        # Audit log for webhook dispatch
        audit_log = AuditLog(
            action_type="webhook_dispatch",
            severity="INFO" if delivered else "ERROR",
            details={
                "alert_id": str(alert.id),
                "webhook_url": webhook_url,
                "status": final_status.value,
                "error": last_error if not delivered else None,
            },
        )
        self.db.add(audit_log)
        await self.db.commit()

        return final_status

    async def get_alert(self, alert_id: UUID) -> Optional[DecisionAlert]:
        """Fetch alert by ID."""
        result = await self.db.execute(select(DecisionAlert).where(DecisionAlert.id == alert_id))
        return result.scalar_one_or_none()

    async def list_alerts(
        self,
        job_id: Optional[UUID] = None,
        execution_log_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[DecisionAlert]:
        """List decision alerts with optional filters."""
        stmt = select(DecisionAlert)
        if job_id:
            stmt = stmt.where(DecisionAlert.job_id == job_id)
        if execution_log_id:
            stmt = stmt.where(DecisionAlert.execution_log_id == execution_log_id)
        if project_id:
            stmt = stmt.where(DecisionAlert.project_id == project_id)
        if session_id:
            stmt = stmt.where(DecisionAlert.session_id == session_id)
        if status:
            stmt = stmt.where(DecisionAlert.status == status)
        if severity:
            stmt = stmt.where(DecisionAlert.severity == severity)

        stmt = stmt.order_by(DecisionAlert.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_alert_status(self, alert_id: UUID, status: str) -> Optional[DecisionAlert]:
        """Update status of a decision alert (e.g. ACKNOWLEDGED, RESOLVED)."""
        valid_statuses = {e.value for e in AlertStatus}
        if status not in valid_statuses:
            raise ValueError(f"Invalid alert status '{status}'. Must be one of {sorted(list(valid_statuses))}.")

        alert = await self.get_alert(alert_id)
        if not alert:
            return None

        alert.status = status
        await self.db.commit()
        await self.db.refresh(alert)

        audit_log = AuditLog(
            action_type="alert_status_updated",
            severity="INFO",
            details={"alert_id": str(alert_id), "new_status": status},
        )
        self.db.add(audit_log)
        await self.db.commit()

        return alert
