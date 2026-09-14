import asyncio

import pytest

from requirement_review.api.runtime import InMemoryApplicationServices


@pytest.mark.asyncio
async def test_five_reviews_can_run_concurrently() -> None:
    services = InMemoryApplicationServices()
    project = await services.create_project("Payments", "local_only", "admin")
    payload = {
        "project_id": project["id"],
        "text": "# Login\n\nThe system should log in quickly.",
        "data_policy": "local_only",
    }
    created = await asyncio.gather(
        *(services.create_review(payload, f"reviewer-{index}") for index in range(5))
    )
    states = await asyncio.gather(
        *(services.get_review(item["review_id"], project["id"]) for item in created)
    )
    assert [state["status"] for state in states if state is not None] == [
        "WAITING_APPROVAL"
    ] * 5
