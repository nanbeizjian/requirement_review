# Backend Agent Instructions

## Inheritance

All rules in the repository-root `AGENTS.md` apply here. The root `openspec/specs/` directory is authoritative for public contracts; this directory may only add backend implementation constraints.

## Backend OpenSpec scope

- Put backend-only specifications and changes under `backend/openspec/`.
- Backend topics include LangGraph state and transitions, model gateways, knowledge retrieval, persistence, telemetry, deployment, and internal security controls.
- Reference root contracts with repository-relative paths such as `openspec/specs/public-contracts/spec.md`.
- If an implementation proposal changes an API, shared schema, authorization behavior, project isolation, or error response, create or update the corresponding root OpenSpec change first.

## Backend engineering rules

- Use Python typing and Pydantic models at external and graph-state boundaries.
- Keep FastAPI routes thin; place domain behavior behind services or protocols.
- Preserve project isolation and fail closed for authentication, authorization, model-routing, and evidence-validation failures.
- Require evidence locators and source quotes for review findings.
- Add or update pytest coverage before changing behavior.
- Run `pytest -q`, `ruff check .`, and `mypy --follow-imports=skip src` from `backend/` before completion.
- Use Alembic for database schema changes; do not mutate historical migrations after release.
