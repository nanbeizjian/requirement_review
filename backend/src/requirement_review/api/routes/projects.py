from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from requirement_review.api.dependencies import AdminDep, ServicesDep
from requirement_review.api.schemas import ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate, actor: AdminDep, services: ServicesDep):
    return await services.create_project(
        body.name, body.data_policy.value, actor.user_id
    )


@router.post("/{project_id}/knowledge/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_knowledge(
    project_id: str,
    actor: AdminDep,
    services: ServicesDep,
    file: Annotated[UploadFile, File()],
):
    if project_id != actor.project_id:
        raise HTTPException(status_code=404, detail="project not found")
    if not file.filename or not file.filename.lower().endswith((".md", ".markdown")):
        raise HTTPException(
            status_code=415, detail="only Markdown knowledge is supported"
        )
    content = await file.read(1_000_001)
    if len(content) > 1_000_000:
        raise HTTPException(status_code=413, detail="knowledge document too large")
    return await services.add_knowledge(project_id, file.filename, content)


@router.post("/{project_id}/knowledge/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_knowledge(project_id: str, actor: AdminDep, services: ServicesDep):
    if project_id != actor.project_id:
        raise HTTPException(status_code=404, detail="project not found")
    return await services.reindex(project_id)
