import pytest

from requirement_review.documents.markdown import parse_markdown


def test_document_over_100000_characters_is_rejected() -> None:
    with pytest.raises(ValueError, match="100000"):
        parse_markdown("d", 1, "x" * 100_001)
