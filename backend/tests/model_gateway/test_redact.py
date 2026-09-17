"""Unit tests for `redact_payload`."""

import pytest

from requirement_review.model_gateway.redact import redact_payload


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("plain text", "plain text"),
        ("alice@example.com", "<email>"),
        ("联系 13800001234 或 13800001235", "联系 <phone> 或 <phone>"),
        ("身份证 11010119900101001X", "身份证 <id>"),
        ("主机 db.corp.local", "主机 <host>"),
        ("IP 10.0.0.5 出现", "IP <ip> 出现"),
        ("IPv6 ::1 出现", "IPv6 <ip> 出现"),
        ("版本号 1.2.3 不应命中", "版本号 1.2.3 不应命中"),
        ("user-name 不是邮箱", "user-name 不是邮箱"),
    ],
)
def test_redact_string(text: str, expected: str) -> None:
    assert redact_payload(text) == expected


def test_redact_nested_structures() -> None:
    payload = {
        "requirement": {"text": "邮箱 alice@example.com"},
        "knowledge": [
            {"text": "phone 13800001234"},
            {"text": "无敏感"},
        ],
        "evidence": [
            {"quote": "10.1.2.3 mentioned", "locator": "L1"},
            {"quote": "no pii here", "locator": "L2"},
        ],
        "meta": {"dimension": "completeness", "kept": 1},
    }
    out = redact_payload(payload)
    assert out["requirement"]["text"] == "邮箱 <email>"
    assert out["knowledge"][0]["text"] == "phone <phone>"
    assert out["knowledge"][1]["text"] == "无敏感"
    assert out["evidence"][0]["quote"] == "<ip> mentioned"
    assert out["evidence"][1]["quote"] == "no pii here"
    assert out["meta"]["dimension"] == "completeness"
    assert out["meta"]["kept"] == 1
    # Original is not mutated.
    assert payload["requirement"]["text"] == "邮箱 alice@example.com"


def test_redact_list_of_strings() -> None:
    out = redact_payload(["alice@example.com", "bob@example.com"])
    assert out == ["<email>", "<email>"]


def test_redact_empty_string_is_unchanged() -> None:
    assert redact_payload("") == ""
