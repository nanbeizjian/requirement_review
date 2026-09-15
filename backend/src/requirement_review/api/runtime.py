import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from requirement_review.domain.models import DataPolicy
from requirement_review.graph.workflow import build_review_graph
from requirement_review.knowledge.markdown_source import MarkdownKnowledgeSource
from requirement_review.knowledge.service import KnowledgeService
from requirement_review.reports.markdown import render_markdown
from requirement_review.review.nodes import ReviewServices


class EmptyModelGateway:
    """Safe development provider; production must inject a configured model gateway."""

    async def review(self, **kwargs) -> list:
        return []


@dataclass
class ReviewRecord:
    review_id: str
    project_id: str
    thread_id: str
    graph: Any
    config: dict
    status: str = "PENDING"
    findings: list = field(default_factory=list)
    failed_dimensions: list[str] = field(default_factory=list)
    approvals: list = field(default_factory=list)
    report: str | None = None
    source_name: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    findings_locked: bool = False  # when True, graph snapshots do not overwrite findings


class IdempotencyConflictError(Exception):
    """Raised when a decision request reuses an Idempotency-Key with a different body."""

    def __init__(self, existing: dict) -> None:
        super().__init__("idempotency_conflict")
        self.existing = existing


class PreconditionFailedError(Exception):
    """Raised when the document finalization gate is not satisfied."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _select_latest_decision(records: list[dict]) -> dict | None:
    """Pick the latest decision by decided_at desc, then idempotency_key asc (stable)."""
    if not records:
        return None
    return sorted(
        records,
        key=lambda d: (d.get("decided_at", ""), d.get("idempotency_key", "")),
    )[-1]


class InMemoryApplicationServices:
    """Runnable local adapter. Database-backed deployments replace this service only."""

    def __init__(self, model_gateway=None) -> None:
        self.model_gateway = model_gateway or EmptyModelGateway()
        self.projects: dict[str, dict] = {}
        self.knowledge_documents: list[tuple[str, str, int, str]] = []
        self.reviews: dict[str, ReviewRecord] = {}
        # decisions[(review_id, finding_id, idempotency_key)] = {action, comment, actor_id, decided_at}
        self.decisions: dict[tuple[str, str, str], dict] = {}
        self._semaphore = asyncio.Semaphore(5)

    async def create_project(self, name: str, data_policy: str, actor_id: str) -> dict:
        project_id = str(uuid4())
        row = {
            "id": project_id,
            "name": name,
            "data_policy": data_policy,
            "owner": actor_id,
        }
        self.projects[project_id] = row
        return row

    async def add_knowledge(
        self, project_id: str, filename: str, content: bytes
    ) -> dict:
        self._require_project(project_id)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("knowledge must be UTF-8 Markdown") from exc
        document_id = hashlib.sha256(content).hexdigest()[:24]
        self.knowledge_documents.append((project_id, document_id, 1, text))
        return {"document_id": document_id, "filename": filename, "status": "INDEXED"}

    async def reindex(self, project_id: str) -> dict:
        self._require_project(project_id)
        return {"project_id": project_id, "status": "INDEXED"}

    async def create_review(self, payload: dict, actor_id: str) -> dict:
        project_id = payload["project_id"]
        project = self._require_project(project_id)
        policy = DataPolicy(payload["data_policy"])
        if policy.value != project["data_policy"]:
            raise ValueError("review data policy must match project policy")
        text = payload.get("text")
        if not text:
            raise ValueError("the in-memory runtime requires inline text")
        review_id = str(uuid4())
        thread_id = f"review:{review_id}"
        source = MarkdownKnowledgeSource.from_documents(self.knowledge_documents)
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
        return {"review_id": review_id, "status": "PENDING"}

    async def _get_record_snapshot(self, record: ReviewRecord) -> None:
        try:
            snapshot = await record.graph.aget_state(record.config)
            self._sync_record(record, snapshot.values)
        except Exception:
            # Graph may be torn down on errors; keep stored state.
            pass

    async def get_review(self, review_id: str, project_id: str) -> dict | None:
        record = self.reviews.get(review_id)
        if record is None or record.project_id != project_id:
            return None
        await self._get_record_snapshot(record)
        return self._summary_for(record)

    async def list_reviews(self, project_id: str) -> list[dict]:
        rows: list[dict] = []
        for r in self.reviews.values():
            if r.project_id != project_id:
                continue
            await self._get_record_snapshot(r)
            rows.append(self._summary_for(r))
        # Stable order: created_at desc, then review_id asc.
        rows.sort(key=lambda s: (s["created_at"], s["review_id"]), reverse=True)
        # Sort by created_at desc and review_id asc secondary
        rows.sort(key=lambda s: s["created_at"], reverse=True)
        rows.sort(key=lambda s: s["review_id"])
        # Final canonical order per spec: created_at desc, review_id asc as tie-breaker
        rows = sorted(rows, key=lambda s: (-int(datetime.fromisoformat(s["created_at"].replace("Z", "+00:00")).timestamp() * 1000) if s["created_at"] else 0, s["review_id"]))
        return rows

    async def get_findings(self, review_id: str, project_id: str) -> list[dict]:
        record = self._require_review(review_id, project_id)
        return [
            {**item.model_dump(mode="json"), "decision": self._latest_decision_for(record, item.finding_id)}
            for item in record.findings
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
        record = self._require_review(review_id, project_id)
        if finding_id not in {item.finding_id for item in record.findings}:
            raise KeyError("finding not found")
        key = (review_id, finding_id, idempotency_key)
        existing = self.decisions.get(key)
        if existing is not None:
            same_action = existing.get("action") == payload.get("action")
            same_comment = existing.get("comment", "") == payload.get("comment", "")
            if same_action and same_comment:
                return existing
            raise IdempotencyConflictError(existing)
        now = datetime.now(timezone.utc).isoformat()
        decision = {
            **payload,
            "finding_id": finding_id,
            "actor_id": actor_id,
            "decided_at": now,
            "idempotency_key": idempotency_key,
        }
        self.decisions[key] = decision
        return decision

    async def approve(
        self,
        review_id: str,
        project_id: str,
        actor_id: str,
        idempotency_key: str,
        payload: dict,
    ) -> dict:
        record = self._require_review(review_id, project_id)
        # Finalization gate: every finding must have latest decision accept/reject.
        if record.findings:
            undecided = []
            for f in record.findings:
                latest = self._latest_decision_for(record, f.finding_id)
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
        if record.status == "COMPLETED":
            review = SimpleNamespace(
                report_version=1,
                status=record.status,
                failed_dimensions=record.failed_dimensions,
            )
            record.report = render_markdown(review, record.findings, record.approvals)
        return {"review_id": review_id, "status": record.status}

    async def get_report(self, review_id: str, project_id: str) -> str | None:
        return self._require_review(review_id, project_id).report

    def _require_project(self, project_id: str) -> dict:
        if project_id not in self.projects:
            raise KeyError("project not found")
        return self.projects[project_id]

    def _require_review(self, review_id: str, project_id: str) -> ReviewRecord:
        record = self.reviews.get(review_id)
        if record is None or record.project_id != project_id:
            raise KeyError("review not found")
        return record

    def _latest_decision_for(self, record: ReviewRecord, finding_id: str) -> dict | None:
        records = [
            d for (rid, fid, _key), d in self.decisions.items()
            if rid == record.review_id and fid == finding_id
        ]
        return _select_latest_decision(records)

    def _summary_for(self, record: ReviewRecord) -> dict:
        finding_count = len(record.findings)
        pending = 0
        for f in record.findings:
            latest = self._latest_decision_for(record, f.finding_id)
            if latest is None or latest.get("action") == "re-review":
                pending += 1
        return {
            "review_id": record.review_id,
            "project_id": record.project_id,
            "source_name": record.source_name,
            "status": record.status,
            "finding_count": finding_count,
            "pending_decision_count": pending,
            "created_at": record.created_at,
            "failed_dimensions": list(record.failed_dimensions),
        }

    @staticmethod
    def _sync_record(record: ReviewRecord, state: dict) -> None:
        record.status = state.get("status", record.status)
        if not record.findings_locked:
            record.findings = state.get("findings", record.findings)
        record.failed_dimensions = state.get(
            "failed_dimensions", record.failed_dimensions
        )
