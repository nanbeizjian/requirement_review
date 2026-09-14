from requirement_review.documents.markdown import parse_markdown


def test_parse_markdown_preserves_heading_and_paragraph_locator() -> None:
    items = parse_markdown(
        "doc-1", 1, "# 登录\n\n用户应快速登录。\n\n用户应看到失败原因。"
    )

    assert [x.requirement_id for x in items] == ["REQ-001", "REQ-002"]
    assert items[0].evidence.locator == "登录#p1"
    assert items[1].evidence.quote == "用户应看到失败原因。"


def test_same_content_produces_same_ids() -> None:
    text = "# 登录\n\n用户应快速登录。"

    assert parse_markdown("doc-1", 1, text) == parse_markdown("doc-1", 1, text)


def test_heading_without_blank_line_still_parses_following_requirement() -> None:
    items = parse_markdown("doc-1", 1, "# 登录\n用户应快速登录。")

    assert len(items) == 1
    assert items[0].text == "用户应快速登录。"
    assert items[0].evidence.locator == "登录#p1"


def test_list_requirements_are_parsed_individually() -> None:
    items = parse_markdown("doc-1", 1, "# 账户\n- 用户可以登录\n- 用户可以退出")

    assert [item.text for item in items] == ["- 用户可以登录", "- 用户可以退出"]
    assert [item.evidence.locator for item in items] == ["账户#p1", "账户#p2"]


def test_repeated_headings_have_unique_stable_locators() -> None:
    text = "# 登录\n用户应快速登录。\n\n# 登录\n用户应看到失败原因。"

    items = parse_markdown("doc-1", 1, text)

    locators = [item.evidence.locator for item in items]
    assert locators == ["登录#p1", "登录#p2"]
    assert len(set(locators)) == len(locators)
    assert [
        item.evidence.locator for item in parse_markdown("doc-1", 1, text)
    ] == locators
