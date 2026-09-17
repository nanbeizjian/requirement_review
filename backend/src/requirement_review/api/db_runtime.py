"""Database-backed implementation of the ApplicationServices Protocol.

Persists projects, reviews, findings, decisions, and reports to PostgreSQL while
keeping the LangGraph handle in memory (same as InMemoryApplicationServices).
The graph itself uses InMemorySaver — checkpoints do not survive a process
restart, but the durable record of every review does, so list / detail /
report / finding queries all read from the database.

This module intentionally mirrors the shape and idempotency semantics of
InMemoryApplicationServices so the route layer can swap one for the other
without code changes.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from uuid import uuid4

from requirement_review.domain.models import DataPolicy
from requirement_review.graph.workflow import build_review_graph
from requirement_review.knowledge.markdown_source import MarkdownKnowledgeSource
from requirement_review.knowledge.service import KnowledgeService
from requirement_review.persistence.tables import (
    FindingDecisionTable,
    ProjectMemberTable,
    ProjectTable,
    ReportApprovalTable,
    ReviewFindingTable,
    ReviewReportTable,
    ReviewRunTable,
    SourceDocumentTable,
)
from requirement_review.reports.markdown import render_markdown
from requirement_review.review.nodes import ReviewServices

from .runtime import (
    IdempotencyConflictError,
    PreconditionFailedError,
    ReviewRecord,
    _payloads_match,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _ensure_project(session, project_id: str) -> ProjectTable:
    row = (await session.get(ProjectTable, project_id))
    if row is None:
        raise KeyError("project not found")
    return row


@dataclass
class DatabaseApplicationServices:
    """Postgres-backed ApplicationServices implementation.

    The graph handle per review is kept in ``self.reviews`` (in-memory); the
    durable state lives in PostgreSQL. Restarting the process loses the graph
    handle but preserves the historical record so read paths keep working.
    """

    session_factory: async_sessionmaker
    model_gateway: Any = None
    reviews: dict[str, ReviewRecord] = field(default_factory=dict)
    _semaphore: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(5))

    # ------------------------------------------------------------------ projects

    async def create_project(
        self, name: str, data_policy: str, actor_id: str
    ) -> dict:
        project_id = str(uuid4())
        async with self.session_factory() as session:
            row = ProjectTable(
                id=project_id,
                name=name,
                data_policy=data_policy,
            )
            session.add(row)
            # Flush the project row first so the FK dependency in
            # project_members is satisfied (no ORM relationship between the
            # two tables, so flush order is not guaranteed).
            await session.flush()
            session.add(
                ProjectMemberTable(
                    project_id=project_id,
                    user_id=actor_id,
                    role="admin",
                )
            )
            await session.commit()
        return {"id": project_id, "name": name, "data_policy": data_policy, "owner": actor_id}

    # ------------------------------------------------------------------ knowledge

    async def add_knowledge(
        self, project_id: str, filename: str, content: bytes
    ) -> dict:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("knowledge must be UTF-8 Markdown") from exc

        document_id = hashlib.sha256(content).hexdigest()[:24]
        async with self.session_factory() as session:
            await _ensure_project(session, project_id)
            existing = (await session.get(SourceDocumentTable, document_id))
            if existing is not None and existing.project_id == project_id:
                # Same content already indexed — idempotent replay.
                await session.rollback()
                return {"document_id": document_id, "filename": filename, "status": "INDEXED"}
            session.add(SourceDocumentTable(
                id=document_id,
                project_id=project_id,
                kind="knowledge",
                filename=filename,
                version=1,
                checksum=hashlib.sha256(content).hexdigest(),
                access_level="project",
                status="INDEXED",
            ))
            await session.commit()
        return {"document_id": document_id, "filename": filename, "status": "INDEXED"}

    async def reindex(self, project_id: str) -> dict:
        async with self.session_factory() as session:
            await _ensure_project(session, project_id)
        return {"project_id": project_id, "status": "INDEXED"}

    # ------------------------------------------------------------------ reviews

    async def create_review(self, payload: dict, actor_id: str) -> dict:
        project_id = payload["project_id"]
        policy = DataPolicy(payload["data_policy"])
        text = payload.get("text")
        if not text:
            raise ValueError("the database runtime requires inline text")

        async with self.session_factory() as session:
            project = await _ensure_project(session, project_id)
            if policy.value != project.data_policy:
                raise ValueError("review data policy must match project policy")

            review_id = str(uuid4())
            thread_id = f"review:{review_id}"
            session.add(ReviewRunTable(
                id=review_id,
                project_id=project_id,
                thread_id=thread_id,
                document_id=payload.get("document_id") or f"inline:{review_id}",
                status="PENDING",
                config_snapshot={"data_policy": policy.value},
                errors=[],
            ))
            await session.commit()

        # Build and run the graph (in-memory only). Source is empty because
        # add_knowledge stores metadata only; inline text flows through
        # payload["text"] via document_text in the graph state.
        source = MarkdownKnowledgeSource.from_documents([])
        services = ReviewServices(KnowledgeService(source), self.model_gateway)
        graph = build_review_graph(services, InMemorySaver())
        config = {"configurable": {"thread_id": thread_id}}
        record = ReviewRecord(
            review_id=review_id,
            project_id=project_id,
            thread_id=thread_id,
            graph=graph,
            config=config,
            source_name=payload.get("source_name"),
        )
        self.reviews[review_id] = record

        async with self._semaphore:
            result = await graph.ainvoke(
                {
                    "review_id": review_id,
                    "project_id": project_id,
                    "document_id": payload.get("document_id") or f"inline:{review_id}",
                    "document_text": text,
                    "data_policy": policy,
                    "status": "PENDING",
                },
                config,
            )

        self._sync_record(record, result)
        await self._persist_run_outcome(record, result)
        return {"review_id": review_id, "status": "PENDING"}

    async def _persist_run_outcome(self, record: ReviewRecord, state: dict) -> None:
        """After the graph completes, write findings + final status to DB."""
        findings = state.get("findings") or []
        async with self.session_factory() as session:
            for item in findings:
                fid = item.finding_id
                # Idempotent insert: if the same finding_id exists in this
                # review, skip (shouldn't happen on first run but defends
                # against rerunning the same record).
                existing = (await session.execute(
                    select(ReviewFindingTable).where(
                        ReviewFindingTable.review_id == record.review_id,
                        ReviewFindingTable.id == fid,
                    )
                )).scalar_one_or_none()
                if existing is not None:
                    continue
                session.add(ReviewFindingTable(
                    id=fid,
                    project_id=record.project_id,
                    review_id=record.review_id,
                    requirement_id=item.requirement_id,
                    dimension=str(item.dimension),
                    severity=str(item.severity),
                    payload=item.model_dump(mode="json"),
                ))

            run = (await session.get(ReviewRunTable, record.review_id))
            if run is not None:
                run.status = state.get("status", run.status)
                run.errors = list(state.get("errors") or [])
            await session.commit()

    async def _get_record_snapshot(self, record: ReviewRecord) -> None:
        try:
            snapshot = await record.graph.aget_state(record.config)
            self._sync_record(record, snapshot.values)
        except Exception:
            pass

    async def get_review(self, review_id: str, project_id: str) -> dict | None:
        record = self.reviews.get(review_id)
        if record is not None and record.project_id == project_id:
            await self._get_record_snapshot(record)
            return await self._summary_for(record)
        # Fall back to DB (process restarted, graph gone, but history persists).
        return await self._summary_from_db(review_id, project_id)

    async def list_reviews(self, project_id: str) -> list[dict]:
        rows: list[dict] = []
        seen: set[str] = set()
        for r in self.reviews.values():
            if r.project_id != project_id:
                continue
            await self._get_record_snapshot(r)
            rows.append(await self._summary_for(r))
            seen.add(r.review_id)
        # Add any reviews that exist only in DB (e.g. after a process restart).
        async with self.session_factory() as session:
            stmt = select(ReviewRunTable).where(ReviewRunTable.project_id == project_id)
            for run in (await session.execute(stmt)).scalars():
                if run.id in seen:
                    continue
                rows.append(await self._summary_from_db(run.id, project_id) or {})
        rows = [r for r in rows if r]
        rows.sort(key=lambda s: (-int(datetime.fromisoformat(s["created_at"].replace("Z", "+00:00")).timestamp() * 1000) if s.get("created_at") else 0, s.get("review_id", "")))
        return rows

    async def get_findings(self, review_id: str, project_id: str) -> list[dict]:
        record = self.reviews.get(review_id)
        if record is not None and record.project_id == project_id:
            out = []
            for item in record.findings:
                decision = await self._latest_decision_for(record, item.finding_id)
                out.append({**item.model_dump(mode="json"), "decision": decision})
            return out
        # Fall back to DB (post-restart path).
        async with self.session_factory() as session:
            stmt = (
                select(ReviewFindingTable)
                .where(
                    ReviewFindingTable.review_id == review_id,
                    ReviewFindingTable.project_id == project_id,
                )
                .order_by(ReviewFindingTable.id)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {**self._finding_dict(row), "decision": await self._latest_db_decision(review_id, row.id)}
                for row in rows
            ]

    async def decide_finding(
        self,
        review_id: str,
        finding_id: str,
        project_id: str,
        actor_id: str,
        idempotency_key: str,
        payload: dict,
    ) -> dict:
        # Verify review + finding exist.
        async with self.session_factory() as session:
            run = (await session.get(ReviewRunTable, review_id))
            if run is None or run.project_id != project_id:
                raise KeyError("review not found")
            finding = (await session.get(ReviewFindingTable, finding_id))
            if finding is None or finding.review_id != review_id:
                raise KeyError("finding not found")

            decision_id = str(uuid4())
            row = FindingDecisionTable(
                id=decision_id,
                project_id=project_id,
                finding_id=finding_id,
                action=payload["action"],
                actor_id=actor_id,
                comment=payload.get("comment", "") or "",
                idempotency_key=idempotency_key,
            )
            session.add(row)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = (await session.execute(
                    select(FindingDecisionTable).where(
                        FindingDecisionTable.finding_id == finding_id,
                        FindingDecisionTable.idempotency_key == idempotency_key,
                    )
                )).scalar_one_or_none()
                if existing is None:
                    raise
                stored = {
                    "action": existing.action,
                    "comment": existing.comment,
                    "finding_id": existing.finding_id,
                    "actor_id": existing.actor_id,
                    "decided_at": existing.created_at.isoformat(),
                    "idempotency_key": existing.idempotency_key,
                }
                same_action = stored["action"] == payload.get("action")
                same_comment = (stored.get("comment", "") or "") == (payload.get("comment", "") or "")
                if same_action and same_comment:
                    # Replay: return a dict built from the STORED row, not from
                    # payload, so two replays of the same key produce
                    # byte-identical dicts (incl. decided_at).
                    return {
                        **payload,
                        "finding_id": existing.finding_id,
                        "actor_id": existing.actor_id,
                        "decided_at": existing.created_at.isoformat(),
                        "idempotency_key": existing.idempotency_key,
                    }
                raise IdempotencyConflictError(stored)

        # Reflect the timestamp we actually persisted (created_at from the
        # row) so two replays of the same key produce byte-identical dicts.
        return {
            **payload,
            "finding_id": finding_id,
            "actor_id": actor_id,
            "decided_at": row.created_at.isoformat(),
            "idempotency_key": idempotency_key,
        }

    async def approve(
        self,
        review_id: str,
        project_id: str,
        actor_id: str,
        idempotency_key: str,
        payload: dict,
    ) -> dict:
        record = self.reviews.get(review_id)
        if record is None or record.project_id != project_id:
            raise KeyError("review not found")

        # Idempotency: same key + same body returns prior response; same key
        # + different body raises IdempotencyConflictError.
        async with self.session_factory() as session:
            existing = (await session.execute(
                select(ReportApprovalTable).where(
                    ReportApprovalTable.review_id == review_id,
                    ReportApprovalTable.idempotency_key == idempotency_key,
                )
            )).scalar_one_or_none()
            if existing is not None:
                stored = {
                    "action": existing.action,
                    "comment": existing.comment,
                    "actor_id": existing.actor_id,
                    "idempotency_key": existing.idempotency_key,
                }
                if _payloads_match(stored, payload):
                    run = (await session.get(ReviewRunTable, review_id))
                    return {"review_id": review_id, "status": run.status if run else "COMPLETED"}
                raise IdempotencyConflictError(stored)

            # Finalization gate: every finding must have latest decision accept/reject.
            if record.findings:
                undecided = []
                for f in record.findings:
                    latest = await self._latest_decision_for(record, f.finding_id)
                    if latest is None or latest.get("action") == "re-review":
                        undecided.append(f.finding_id)
                if undecided:
                    raise PreconditionFailedError(
                        "approval_blocked_undecided",
                        f"cannot approve: findings {undecided} lack accept/reject decisions",
                    )

            decision = {**payload, "actor_id": actor_id, "idempotency_key": idempotency_key}
            result = await record.graph.ainvoke(Command(resume=decision), record.config)
            record.approvals.append(SimpleNamespace(**decision))
            self._sync_record(record, result)

            session.add(ReportApprovalTable(
                id=str(uuid4()),
                project_id=project_id,
                review_id=review_id,
                action=payload["action"],
                actor_id=actor_id,
                comment=payload.get("comment", "") or "",
                idempotency_key=idempotency_key,
            ))
            run = (await session.get(ReviewRunTable, review_id))
            if run is not None:
                run.status = record.status

            if record.status == "COMPLETED":
                review_ns = SimpleNamespace(
                    report_version=1,
                    status=record.status,
                    failed_dimensions=record.failed_dimensions,
                )
                markdown = render_markdown(review_ns, record.findings, record.approvals)
                record.report = markdown
                # Persist report if not already (one per (review_id, version)).
                existing_report = (await session.execute(
                    select(ReviewReportTable).where(
                        ReviewReportTable.review_id == review_id,
                        ReviewReportTable.version == 1,
                    )
                )).scalar_one_or_none()
                if existing_report is None:
                    session.add(ReviewReportTable(
                        id=str(uuid4()),
                        project_id=project_id,
                        review_id=review_id,
                        version=1,
                        markdown=markdown,
                    ))
                else:
                    existing_report.markdown = markdown

            await session.commit()
        return {"review_id": review_id, "status": record.status}

    async def get_report(self, review_id: str, project_id: str) -> str | None:
        record = self.reviews.get(review_id)
        if record is not None and record.project_id == project_id and record.report is not None:
            return record.report
        async with self.session_factory() as session:
            stmt = (
                select(ReviewReportTable)
                .where(
                    ReviewReportTable.review_id == review_id,
                    ReviewReportTable.project_id == project_id,
                )
                .order_by(ReviewReportTable.version.desc())
            )
            row = (await session.execute(stmt)).scalars().first()
            return row.markdown if row is not None else None

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _sync_record(record: ReviewRecord, state: dict) -> None:
        record.status = state.get("status", record.status)
        if not record.findings_locked:
            record.findings = state.get("findings", record.findings)
        record.failed_dimensions = state.get("failed_dimensions", record.failed_dimensions)

    async def _latest_decision_for(self, record: ReviewRecord, finding_id: str) -> dict | None:
        # Decision lookup is DB-backed so it survives a process restart.
        return await self._latest_db_decision(record.review_id, finding_id)

    async def _latest_db_decision(self, review_id: str, finding_id: str) -> dict | None:
        # FindingDecisionTable does not have review_id directly; the finding
        # carries it. We verify via review_findings.
        async with self.session_factory() as session:
            stmt = (
                select(FindingDecisionTable)
                .where(
                    FindingDecisionTable.finding_id == finding_id,
                    FindingDecisionTable.finding_id.in_(
                        select(ReviewFindingTable.id).where(
                            ReviewFindingTable.review_id == review_id
                        )
                    ),
                )
                .order_by(FindingDecisionTable.created_at.desc())
            )
            row = (await session.execute(stmt)).scalars().first()
            if row is None:
                return None
            return {
                "action": row.action,
                "comment": row.comment,
                "finding_id": row.finding_id,
                "actor_id": row.actor_id,
                "decided_at": row.created_at.isoformat(),
                "idempotency_key": row.idempotency_key,
            }

    async def _decision_dict_for_finding(self, review_id: str, finding_id: str) -> dict | None:
        return await self._latest_db_decision(review_id, finding_id)

    async def _summary_for(self, record: ReviewRecord) -> dict:
        pending = 0
        for f in record.findings:
            latest = await self._latest_decision_for(record, f.finding_id)
            if latest is None or latest.get("action") == "re-review":
                pending += 1
        return {
            "review_id": record.review_id,
            "project_id": record.project_id,
            "source_name": record.source_name,
            "status": record.status,
            "finding_count": len(record.findings),
            "pending_decision_count": pending,
            "created_at": record.created_at,
            "failed_dimensions": list(record.failed_dimensions),
        }

    async def _summary_from_db(self, review_id: str, project_id: str) -> dict | None:
        async with self.session_factory() as session:
            run = (await session.get(ReviewRunTable, review_id))
            if run is None or run.project_id != project_id:
                return None
            findings = (await session.execute(
                select(ReviewFindingTable).where(ReviewFindingTable.review_id == review_id)
            )).scalars().all()
            # Find decisions count to compute pending (one decision per finding
            # is enough — we just want to know whether each has any).
            decided_ids = set((await session.execute(
                select(FindingDecisionTable.finding_id)
                .where(
                    FindingDecisionTable.finding_id.in_(
                        select(ReviewFindingTable.id).where(
                            ReviewFindingTable.review_id == review_id
                        )
                    )
                )
                .distinct()
            )).scalars().all())
            pending = 0
            for f in findings:
                latest = await self._latest_db_decision(review_id, f.id)
                if latest is None or latest.get("action") == "re-review":
                    pending += 1
            return {
                "review_id": run.id,
                "project_id": run.project_id,
                "source_name": None,
                "status": run.status,
                "finding_count": len(findings),
                "pending_decision_count": pending,
                "created_at": run.created_at.isoformat(),
                "failed_dimensions": [],
            }

    @staticmethod
    def _finding_dict(row: ReviewFindingTable) -> dict:
        # Schema on the wire matches what InMemoryApplicationServices.get_findings
        # returns: full finding dict + "decision" field.
        payload = dict(row.payload or {})
        return {
            **payload,
            "finding_id": row.id,
            "review_id": row.review_id,
            "project_id": row.project_id,
            "requirement_id": row.requirement_id,
            "dimension": row.dimension,
            "severity": row.severity,
            "decision": None,
        }
