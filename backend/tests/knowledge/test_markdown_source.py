import pytest

from requirement_review.domain.models import (
    EvidenceRef,
    KnowledgeChunk,
    RequirementItem,
)
from requirement_review.knowledge.markdown_source import MarkdownKnowledgeSource
from requirement_review.knowledge.service import KnowledgeService


@pytest.mark.asyncio
async def test_search_never_returns_another_project() -> None:
    source = MarkdownKnowledgeSource.from_documents(
        [
            ("p1", "k1", 1, "# API\nERR_LOGIN_01 表示密码错误"),
            ("p2", "k2", 1, "# API\nERR_LOGIN_01 表示账户冻结"),
        ]
    )

    hits = await source.search("ERR_LOGIN_01", "p1", {})

    assert hits
    assert {hit.project_id for hit in hits} == {"p1"}
    assert "密码错误" in hits[0].text


@pytest.mark.asyncio
async def test_context_for_searches_requirement_within_its_project() -> None:
    source = MarkdownKnowledgeSource.from_documents(
        [("p1", "api", 1, "# 登录\nERR_LOGIN_01 表示密码错误")]
    )
    service = KnowledgeService(source)
    requirement = RequirementItem(
        requirement_id="REQ-001",
        text="登录失败时展示 ERR_LOGIN_01",
        evidence=EvidenceRef(
            source_type="requirement",
            document_id="requirements",
            version=1,
            locator="登录#p1",
            quote="登录失败时展示 ERR_LOGIN_01",
        ),
    )

    context = await service.context_for("p1", requirement)

    assert [chunk.text for chunk in context] == ["ERR_LOGIN_01 表示密码错误"]


def test_constructor_allows_ten_thousand_chunks_per_project_but_rejects_one_more() -> (
    None
):
    chunks_per_project = [
        KnowledgeChunk(
            chunk_id=f"{project_id}:{index}",
            project_id=project_id,
            document_id="doc",
            version=1,
            locator=f"root#p{index}",
            text="content",
        )
        for project_id in ("p1", "p2")
        for index in range(10_000)
    ]

    MarkdownKnowledgeSource(chunks_per_project)

    one_too_many_for_p1 = [
        *chunks_per_project,
        KnowledgeChunk(
            chunk_id="p1:10000",
            project_id="p1",
            document_id="doc",
            version=1,
            locator="root#p10000",
            text="content",
        ),
    ]
    with pytest.raises(ValueError):
        MarkdownKnowledgeSource(one_too_many_for_p1)


def test_from_documents_rejects_a_project_with_more_than_ten_thousand_chunks() -> None:
    ten_thousand_blocks = "\n\n".join("content" for _ in range(10_000))
    MarkdownKnowledgeSource.from_documents([("p1", "doc", 1, ten_thousand_blocks)])

    one_too_many_blocks = "\n\n".join("content" for _ in range(10_001))
    with pytest.raises(ValueError):
        MarkdownKnowledgeSource.from_documents([("p1", "doc", 1, one_too_many_blocks)])
