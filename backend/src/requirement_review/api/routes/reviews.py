from fastapi import APIRouter, Header, HTTPException, Response, status
from fastapi.responses import PlainTextResponse

from requirement_review.api.dependencies import ActorDep, ReviewerDep, ServicesDep
from requirement_review.api.schemas import (
    ApprovalRequest,
    FindingDecisionRequest,
    ReviewCreate,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _same_project(requested: str, actor_project: str) -> None:
    if requested != actor_project:
        raise HTTPException(status_code=404, detail="review not found")


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_review(
    body: ReviewCreate, response: Response, actor: ReviewerDep, services: ServicesDep
):
    _same_project(body.project_id, actor.project_id)
    result = await services.create_review(body.model_dump(mode="json"), actor.user_id)
    response.headers["Location"] = f"/api/v1/reviews/{result['review_id']}"
    return result


@router.get("/{review_id}")
async def get_review(review_id: str, actor: ActorDep, services: ServicesDep):
    result = await services.get_review(review_id, actor.project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="review not found")
    return result


@router.get("/{review_id}/findings")
async def get_findings(review_id: str, actor: ActorDep, services: ServicesDep):
    return await services.get_findings(review_id, actor.project_id)


@router.post(
    "/{review_id}/findings/{finding_id}/decision", status_code=status.HTTP_201_CREATED
)
async def decide_finding(
    review_id: str,
    finding_id: str,
    body: FindingDecisionRequest,
    actor: ReviewerDep,
    services: ServicesDep,
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    return await services.decide_finding(
        review_id,
        finding_id,
        actor.project_id,
        actor.user_id,
        idempotency_key,
        body.model_dump(mode="json"),
    )


@router.post("/{review_id}/approval", status_code=status.HTTP_202_ACCEPTED)
async def approve_review(
    review_id: str,
    body: ApprovalRequest,
    actor: ReviewerDep,
    services: ServicesDep,
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    return await services.approve(
        review_id,
        actor.project_id,
        actor.user_id,
        idempotency_key,
        body.model_dump(mode="json"),
    )


@router.get("/{review_id}/report", response_class=PlainTextResponse)
async def get_report(review_id: str, actor: ActorDep, services: ServicesDep):
    report = await services.get_report(review_id, actor.project_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return report
