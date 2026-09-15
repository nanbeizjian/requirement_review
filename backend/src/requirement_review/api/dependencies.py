from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, Header, HTTPException, Request, status


class ApplicationServices(Protocol):
    async def create_project(
        self, name: str, data_policy: str, actor_id: str
    ) -> dict: ...
    async def add_knowledge(
        self, project_id: str, filename: str, content: bytes
    ) -> dict: ...
    async def reindex(self, project_id: str) -> dict: ...
    async def create_review(self, payload: dict, actor_id: str) -> dict: ...
    async def get_review(self, review_id: str, project_id: str) -> dict | None: ...
    async def list_reviews(self, project_id: str) -> list[dict]: ...
    async def get_findings(self, review_id: str, project_id: str) -> list[dict]: ...
    async def decide_finding(
        self,
        review_id: str,
        finding_id: str,
        project_id: str,
        actor_id: str,
        idempotency_key: str,
        payload: dict,
    ) -> dict: ...
    async def approve(
        self,
        review_id: str,
        project_id: str,
        actor_id: str,
        idempotency_key: str,
        payload: dict,
    ) -> dict: ...
    async def get_report(self, review_id: str, project_id: str) -> str | None: ...


@dataclass(frozen=True)
class Actor:
    user_id: str
    project_id: str
    role: str


def get_actor(
    user_id: Annotated[str, Header(alias="X-User-ID")],
    header_project_id: Annotated[str, Header(alias="X-Project-ID")],
    role: Annotated[str, Header(alias="X-Role")],
) -> Actor:
    if role not in {"admin", "reviewer", "viewer"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="invalid role"
        )
    return Actor(user_id=user_id, project_id=header_project_id, role=role)


def require_reviewer(actor: Annotated[Actor, Depends(get_actor)]) -> Actor:
    if actor.role not in {"admin", "reviewer"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="reviewer role required"
        )
    return actor


def require_admin(actor: Annotated[Actor, Depends(get_actor)]) -> Actor:
    if actor.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="admin role required"
        )
    return actor


def get_services(request: Request) -> ApplicationServices:
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="service not configured",
        )
    return services


ActorDep = Annotated[Actor, Depends(get_actor)]
ReviewerDep = Annotated[Actor, Depends(require_reviewer)]
AdminDep = Annotated[Actor, Depends(require_admin)]
ServicesDep = Annotated[ApplicationServices, Depends(get_services)]
