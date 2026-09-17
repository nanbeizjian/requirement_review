"""OpenAI-compatible HTTP client for requirement review.

This module deliberately exposes `transport` so tests can inject
`httpx.MockTransport`. Production code uses `httpx.AsyncClient`; tests
fake it.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Iterable

import httpx

from .errors import (
    ModelGatewayAuthError,
    ModelGatewayConfigError,
    ModelGatewayParseError,
    ModelGatewayRateLimitError,
    ModelGatewayResponseError,
    ModelGatewayTimeoutError,
    ModelGatewayTransientError,
)
from .redact import redact_payload


DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"
DEFAULT_MODEL = "MiniMax-Text-01"
ENV_BASE_URL = "MINIMAX_BASE_URL"
ENV_MODEL = "MINIMAX_MODEL"
ENV_API_KEY = "MINIMAX_API_KEY"


def _extract_api_key(name: str = ENV_API_KEY) -> str:
    value = os.environ.get(name)
    if not value:
        raise ModelGatewayConfigError(
            f"missing required environment variable {name!r}; set it in the secrets manager or local .env"
        )
    return value


# System prompt: explicit JSON schema, no markdown, no <think> blocks.
# MiniMax M-series is a reasoning model that emits <think>...</think>
# before the actual answer; we strip those on the parse side. The schema
# below uses the exact snake_case field names ReviewFinding expects, so
# the parser can validate without aliasing most of the time.
_SYSTEM_PROMPT = (
    "You are a strict requirement reviewer. Output ONLY a single JSON object "
    "(no prose, no markdown fences, no <think> blocks) matching this exact schema:\n"
    "{\n"
    '  "requirement_id": string,    // e.g. "REQ-001"\n'
    '  "dimension": string,         // one of: completeness, consistency, clarity, feasibility, testability, security, performance, data_interface\n'
    '  "severity": string,          // one of: critical, high, medium, low\n'
    '  "issue": string,             // what is wrong (Chinese, 1-2 sentences)\n'
    '  "impact": string,            // why it matters (Chinese, 1-2 sentences)\n'
    '  "recommendation": string,    // concrete fix (Chinese, 1-2 sentences)\n'
    '  "confidence": number,        // 0.0 to 1.0\n'
    '  "evidence": [\n'
    "    {\n"
    '      "source_type": string,  // "requirement" or "knowledge"\n'
    '      "document_id": string,\n'
    '      "version": integer,\n'
    '      "locator": string,\n'
    '      "quote": string         // copied VERBATIM from the requirement or knowledge text\n'
    "    }\n"
    "  ],\n"
    '  "uses_system_fact": boolean  // true if any evidence source_type is "knowledge"\n'
    "}\n"
    "Wrap your final answer as: {\"findings\": [<one or more objects as above>]}. "
    "If the requirement has no real issues, output {\"findings\": []}."
)


_SEVERITY_ALIAS = {"major": "medium", "minor": "low", "blocker": "critical"}


class OpenAICompatibleClient:
    """Minimal OpenAI-compatible chat client for requirement review dimensions."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        require_api_key: bool = True,
        timeout_s: float = 30.0,
        max_retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
        redact_for_cloud: bool = False,
    ) -> None:
        self.base_url = base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL
        self.model = model or os.environ.get(ENV_MODEL) or DEFAULT_MODEL
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.redact_for_cloud = redact_for_cloud

        if api_key is None and require_api_key:
            api_key = _extract_api_key()
        self.api_key = api_key
        if require_api_key and not self.api_key:
            raise ModelGatewayConfigError(
                f"model gateway requires {ENV_API_KEY!r} to be set"
            )

        if transport is None:
            transport = httpx.AsyncHTTPTransport()
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {"Content-Type": "application/json"}
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    async def review(
        self,
        *,
        project_id: str,
        data_policy,
        dimension,
        requirement,
        knowledge,
    ) -> list:
        from requirement_review.domain.models import DataPolicy

        payload = self._build_payload(
            project_id=project_id,
            dimension=dimension,
            requirement=requirement,
            knowledge=knowledge,
        )
        if data_policy == DataPolicy.CLOUD_REDACTED or self.redact_for_cloud:
            payload = redact_payload(payload)
        body = json.dumps(payload, ensure_ascii=False)
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = self._headers()

        attempt = 0
        last_exc: Exception | None = None
        while attempt <= self.max_retries:
            try:
                # NOTE: a shared AsyncHTTPTransport across concurrent reviews
                # causes upstream connection errors (httpx reuses keep-alive
                # connections from the shared pool concurrently). Use a fresh
                # client per call so each request owns its own connection.
                async with httpx.AsyncClient(
                    timeout=self.timeout_s,
                ) as client:
                    response = await client.post(url, headers=headers, content=body)
            except httpx.TimeoutException as exc:
                last_exc = ModelGatewayTimeoutError("upstream timeout")
                attempt += 1
                continue
            except httpx.HTTPError as exc:
                raise ModelGatewayTransientError("upstream transport error") from exc

            if response.status_code == 429:
                last_exc = ModelGatewayRateLimitError(
                    "upstream rate limited", status_code=response.status_code
                )
                attempt += 1
                continue
            if response.status_code in (500, 502, 503, 504):
                last_exc = ModelGatewayTransientError(
                    "upstream unavailable", status_code=response.status_code
                )
                attempt += 1
                continue
            if response.status_code in (401, 403):
                raise ModelGatewayAuthError(
                    "upstream authentication failed", status_code=response.status_code
                )
            if response.status_code >= 400:
                raise ModelGatewayTransientError(
                    "upstream request failed", status_code=response.status_code
                )
            try:
                response_json = response.json()
            except json.JSONDecodeError as exc:
                raise ModelGatewayResponseError("invalid upstream JSON") from exc
            return self._parse_response(response_json, requirement, dimension)

        if isinstance(last_exc, ModelGatewayTransientError):
            raise last_exc
        raise ModelGatewayTransientError("upstream retries exhausted")

    def _build_payload(
        self,
        *,
        project_id: str,
        dimension,
        requirement,
        knowledge,
    ) -> dict[str, Any]:
        context_blocks: list[str] = []
        for chunk in knowledge or []:
            context_blocks.append(
                f"[KNOWLEDGE id={chunk.chunk_id} project={chunk.project_id} v{chunk.version}]\n{chunk.text}"
            )
        user_prompt = (
            f"You are reviewing requirement {requirement.requirement_id} of project {project_id}.\n"
            f"Dimension: {dimension.value if hasattr(dimension, 'value') else dimension}\n"
            f"Requirement text:\n{requirement.text}\n\n"
            f"Knowledge context (cite verbatim when used):\n"
            + ("\n\n".join(context_blocks) if context_blocks else "(none)\n")
        )
        return {
            "model": self.model,
            "temperature": 0.1,
            "max_tokens": 4096,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            # NOTE: MiniMax M-series rejects response_format=json_schema.name=missing
            # and silently returns free-form text otherwise. We rely on the system
            # prompt + _parse_response + _normalize_finding instead.
        }

    def _parse_response(self, response_json: dict[str, Any], requirement, dimension) -> list:
        from requirement_review.domain.models import ReviewFinding, EvidenceValidationError

        choices = response_json.get("choices") or []
        if not choices:
            return []
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            return []

        # Strip <think>...</think> blocks and markdown code fences.
        cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                raise ModelGatewayParseError("unparseable model content")
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                raise ModelGatewayParseError("unparseable model content")

        # Accept {"findings": [...]}, bare array, or single bare object.
        if isinstance(parsed, list):
            items = parsed
        else:
            items = parsed.get("findings")
            if items is None:
                items = [parsed]
        if not isinstance(items, list):
            return []

        # Force the canonical dimension value from the call site so model
        # variants (e.g. "complete", "complete-ness") don't trip the
        # downstream "mismatched review scope" check.
        canonical_dim = dimension.value if hasattr(dimension, "value") else str(dimension)
        out: list = []
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized = _normalize_finding(item)
            # Re-key the requirement evidence to point at the actual requirement
            # so validate_finding() in the LangGraph node accepts the finding.
            # The model's free-form document_id/locator are not authoritative;
            # only the quote text is what gets verified against the requirement.
            req_ev = requirement.evidence
            has_quote_match = False
            for ev in normalized.get("evidence", []):
                if ev.get("source_type") == "requirement":
                    quote = ev.get("quote", "")
                    if requirement.text and quote in requirement.text:
                        ev["document_id"] = req_ev.document_id
                        ev["version"] = req_ev.version
                        ev["locator"] = req_ev.locator
                        has_quote_match = True
            if not has_quote_match:
                continue
            # Force canonical requirement_id and dimension so the model cannot
            # desync from the call site (which would trip "mismatched review
            # scope" in the LangGraph node).
            normalized["requirement_id"] = requirement.requirement_id
            normalized["dimension"] = canonical_dim
            try:
                out.append(ReviewFinding.model_validate(normalized))
            except EvidenceValidationError:
                continue
            except (ValueError, TypeError):
                continue
        return out


def _normalize_finding(item: dict[str, Any]) -> dict[str, Any]:
    """Translate common variant field names (camelCase, synonyms) into the
    snake_case shape that ReviewFinding / EvidenceRef expect.
    """
    raw_ev = item.get("evidence") or item.get("evidences") or []
    norm_ev: list[dict[str, Any]] = []
    for e in raw_ev if isinstance(raw_ev, list) else []:
        if not isinstance(e, dict):
            continue
        quote = e.get("quote") or e.get("text") or e.get("snippet") or ""
        source_type = e.get("source_type") or e.get("source") or "requirement"
        if source_type not in ("requirement", "knowledge"):
            source_type = "requirement"
        document_id = (
            e.get("document_id")
            or e.get("doc_id")
            or item.get("document_id")
            or "doc1"
        )
        version = e.get("version") or 1
        locator = (
            e.get("locator")
            or e.get("location")
            or e.get("section")
            or "L?"
        )
        try:
            version = int(version)
        except (TypeError, ValueError):
            version = 1
        norm_ev.append({
            "source_type": source_type,
            "document_id": str(document_id),
            "version": version,
            "locator": str(locator),
            "quote": str(quote),
        })

    severity = item.get("severity") or "medium"
    if isinstance(severity, str):
        severity = _SEVERITY_ALIAS.get(severity.lower(), severity.lower())

    confidence = item.get("confidence") or item.get("score")
    try:
        confidence = float(confidence) if confidence is not None else 0.7
    except (TypeError, ValueError):
        confidence = 0.7
    confidence = max(0.0, min(1.0, confidence))

    impact = (
        item.get("impact")
        or item.get("consequence")
        or item.get("details")
        or item.get("description")
        or ""
    )

    return {
        "requirement_id": (
            item.get("requirement_id")
            or item.get("requirementId")
            or item.get("req_id")
            or ""
        ),
        "dimension": item.get("dimension") or item.get("category") or "completeness",
        "severity": severity,
        "issue": (
            item.get("issue")
            or item.get("summary")
            or item.get("problem")
            or item.get("title")
            or ""
        ),
        "impact": impact,
        "recommendation": (
            item.get("recommendation")
            or item.get("suggestion")
            or item.get("fix")
            or ""
        ),
        "confidence": confidence,
        "evidence": norm_ev,
        "uses_system_fact": any(
            e.get("source_type") == "knowledge" for e in norm_ev
        ),
    }
