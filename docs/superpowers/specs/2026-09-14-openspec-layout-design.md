# OpenSpec Layout Design

## Goal

Initialize OpenSpec for the separated frontend/backend repository while keeping cross-component contracts in one authoritative location.

## Structure

- The repository root owns `AGENTS.md` and `openspec/`.
- Root `openspec/specs/` contains public contracts shared by frontend, backend, and integrations: HTTP APIs, authentication and authorization, project isolation, common data schemas, error responses, and compatibility rules.
- `backend/` owns a nested `AGENTS.md` and `backend/openspec/`.
- `backend/openspec/specs/` contains backend-only implementation specifications: LangGraph workflows, persistence, model gateways, knowledge retrieval, observability, and deployment behavior.
- Backend specifications reference root public contracts instead of duplicating them. Root contracts take precedence when there is a conflict.

## Agent Instructions

The root `AGENTS.md` defines repository-wide OpenSpec workflow and public-contract ownership. The backend file inherits those rules and adds Python, FastAPI, LangGraph, database, security, and test requirements.

## Initialization and Validation

Run OpenSpec initialization with Codex integration at both levels. Preserve generated OpenSpec files, add project context to each configuration, and validate both roots independently. Commit generated workflow files together with the two OpenSpec trees and instruction files.

## Non-goals

This change does not alter application behavior, API endpoints, runtime configuration, or deployment topology.
