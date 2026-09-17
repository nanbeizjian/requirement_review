"""Recursive payload redaction for `data_policy="cloud_redacted"`.

The rules below are deliberately conservative: they match only well-known
shapes (email, mainland-China phone, mainland-China resident ID, IPv4, IPv6,
RFC1918 hostnames). Anything else passes through. False positives are
preferable to leaks because the consumer (`PolicyModelGateway`) is a
defensive layer and the original payload is never reconstructed after
redaction.
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Iterable
from typing import Any

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_CN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_ID_CN = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
_IPV4 = re.compile(r"(?<!\d)((?:\d{1,3}\.){3}\d{1,3})(?!\d)")
# Heuristic IPv6: at least 2 groups of hex separated by `:` with optional
# `::`. We accept anything `ipaddress.IPv6Address` can parse.
_IPV6_CANDIDATE = re.compile(r"(?<!\w)([0-9A-Fa-f:]{3,})(?!\w)")
_INTERNAL_HOST = re.compile(
    r"\b(?:(?:[0-9A-Za-z](?:[0-9A-Za-z\-]{0,61}[0-9A-Za-z])?\.)+(?:local|internal|intranet|corp|lan))\b",
    re.IGNORECASE,
)

_PLACEHOLDER = {
    "email": "<email>",
    "phone": "<phone>",
    "id": "<id>",
    "host": "<host>",
    "ip": "<ip>",
}


def _replace_string(text: str) -> str:
    if not text:
        return text
    out = _EMAIL.sub(_PLACEHOLDER["email"], text)
    out = _PHONE_CN.sub(_PLACEHOLDER["phone"], out)
    out = _ID_CN.sub(_PLACEHOLDER["id"], out)
    out = _INTERNAL_HOST.sub(_PLACEHOLDER["host"], out)
    out = _IPV4.sub(_match_ipv4, out)
    out = _IPV6_CANDIDATE.sub(_match_ipv6, out)
    return out


def _match_ipv4(match: re.Match[str]) -> str:
    candidate = match.group(1)
    try:
        ipaddress.IPv4Address(candidate)
    except ValueError:
        return candidate
    return _PLACEHOLDER["ip"]


def _match_ipv6(match: re.Match[str]) -> str:
    candidate = match.group(1)
    try:
        ipaddress.IPv6Address(candidate)
    except ValueError:
        return candidate
    return _PLACEHOLDER["ip"]


def redact_payload(value: Any) -> Any:
    """Return a redacted deep-clone of `value`. Containers are recursed into."""
    return _walk(value, path=())


def _walk(value: Any, *, path: Iterable[str]) -> Any:
    if isinstance(value, str):
        return _replace_string(value)
    if isinstance(value, dict):
        return {key: _walk(item, path=(*path, str(key))) for key, item in value.items()}
    if isinstance(value, list):
        return [_walk(item, path=(*path, "[*]")) for item in value]
    if isinstance(value, tuple):
        return tuple(_walk(item, path=(*path, "[*]")) for item in value)
    return value
