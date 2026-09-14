from requirement_review.review.merge import RANK


def _escape(value: object) -> str:
    return str(value).replace("\r", " ").replace("\n", " ")


def render_markdown(review, findings, approvals) -> str:
    ordered = sorted(
        findings,
        key=lambda item: (
            -RANK[item.severity],
            item.requirement_id,
            item.dimension.value,
        ),
    )
    lines = [f"# 需求评审报告 v{review.report_version}", "", f"状态：{review.status}"]
    if review.failed_dimensions:
        lines += [
            "",
            "## 未完成评审维度",
            "",
            ", ".join(sorted(review.failed_dimensions)),
        ]
    lines += ["", "## 问题清单"]
    for item in ordered:
        lines += [
            "",
            f"### {_escape(item.requirement_id)} · {item.severity.value}",
            "",
            _escape(item.issue),
            "",
            f"影响：{_escape(item.impact)}",
            "",
            f"建议：{_escape(item.recommendation)}",
            "",
            "证据：",
        ]
        lines.extend(
            f"- `{_escape(e.document_id)}@{e.version}:{_escape(e.locator)}` — {_escape(e.quote)}"
            for e in item.evidence
        )
    lines += ["", "## 审批记录"]
    lines.extend(
        f"- {_escape(a.actor_id)}: {_escape(a.action)} — {_escape(a.comment)}"
        for a in approvals
    )
    return "\n".join(lines) + "\n"
