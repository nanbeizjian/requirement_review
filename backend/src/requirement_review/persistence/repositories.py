import inspect
from uuid import uuid4

from sqlalchemy import func, select

from .tables import (
    AuditEventTable,
    FindingDecisionTable,
    ReviewFindingTable,
    ReviewReportTable,
    ReviewRunTable,
)


async def _resolve(value):
    return await value if inspect.isawaitable(value) else value


class ReviewRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def _flush(self) -> None:
        await _resolve(self.session.flush())

    async def create(
        self,
        *,
        review_id: str,
        project_id: str,
        thread_id: str,
        document_id: str | None,
        data_policy: str,
    ) -> ReviewRunTable:
        row = ReviewRunTable(
            id=review_id,
            project_id=project_id,
            thread_id=thread_id,
            document_id=document_id,
            status="PENDING",
            config_snapshot={"data_policy": data_policy},
            errors=[],
        )
        self.session.add(row)
        await self._flush()
        return row

    async def get_for_project(
        self, review_id: str, project_id: str
    ) -> ReviewRunTable | None:
        result = await _resolve(
            self.session.scalar(
                select(ReviewRunTable).where(
                    ReviewRunTable.id == review_id,
                    ReviewRunTable.project_id == project_id,
                )
            )
        )
        return result

    async def record_finding_decision(
        self,
        finding_id: str,
        action: str,
        actor_id: str,
        idempotency_key: str,
        project_id: str | None = None,
        comment: str = "",
    ) -> FindingDecisionTable:
        finding = await _resolve(
            self.session.scalar(
                select(ReviewFindingTable).where(
                    ReviewFindingTable.id == finding_id,
                )
            )
        )
        if finding is None or (
            project_id is not None and finding.project_id != project_id
        ):
            raise PermissionError("finding is not accessible")
        existing = await _resolve(
            self.session.scalar(
                select(FindingDecisionTable).where(
                    FindingDecisionTable.finding_id == finding_id,
                    FindingDecisionTable.idempotency_key == idempotency_key,
                )
            )
        )
        if existing is not None:
            return existing
        row = FindingDecisionTable(
            id=str(uuid4()),
            project_id=finding.project_id,
            finding_id=finding_id,
            action=action,
            actor_id=actor_id,
            comment=comment,
            idempotency_key=idempotency_key,
        )
        self.session.add(row)
        self.session.add(
            AuditEventTable(
                id=str(uuid4()),
                project_id=finding.project_id,
                actor_id=actor_id,
                action="finding_decision",
                object_type="review_finding",
                object_id=finding_id,
                summary={"action": action},
            )
        )
        await self._flush()
        return row

    async def publish_report(
        self, review_id: str, project_id: str, markdown: str
    ) -> ReviewReportTable:
        review = await self.get_for_project(review_id, project_id)
        if review is None:
            raise PermissionError("review is not accessible")
        current = await _resolve(
            self.session.scalar(
                select(func.max(ReviewReportTable.version)).where(
                    ReviewReportTable.review_id == review_id,
                    ReviewReportTable.project_id == project_id,
                )
            )
        )
        row = ReviewReportTable(
            id=str(uuid4()),
            project_id=project_id,
            review_id=review_id,
            version=(current or 0) + 1,
            markdown=markdown,
        )
        self.session.add(row)
        await self._flush()
        return row

    async def replace_report(self, report_id: str, body: str) -> None:
        raise ValueError("published reports are immutable")
