import json

import openpyxl
import pytest
from lxml import etree

from app.db.session import get_db
from app.main import app
from demo_flow import ARTIFACT_NAMES, run_demo


@pytest.mark.asyncio
async def test_synthetic_demo_covers_success_and_expected_failures(
    tmp_path,
    capsys,
) -> None:
    async def existing_override():
        raise AssertionError("The demo override should replace this only while it runs")

    original_dependency_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = existing_override
    try:
        summary = await run_demo(tmp_path)
        assert app.dependency_overrides[get_db] is existing_override
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_dependency_overrides)

    assert summary.artifact_names == ARTIFACT_NAMES
    assert summary.parse_failure_status == 422
    assert summary.parse_failure_removed_upload is True
    assert {
        "buyer_country_code",
        "items[0].hscode",
        "total_amount",
    } <= set(summary.validation_error_fields)

    xml_path = tmp_path / ARTIFACT_NAMES[0]
    csv_path = tmp_path / ARTIFACT_NAMES[1]
    xlsx_path = tmp_path / ARTIFACT_NAMES[2]
    assert etree.parse(str(xml_path)).getroot().tag.endswith("Declaration")
    assert csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    workbook = openpyxl.load_workbook(xlsx_path, read_only=True)
    assert workbook.active.title == "수출신고서"
    workbook.close()
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(ARTIFACT_NAMES)

    captured = capsys.readouterr().out
    events = [json.loads(line) for line in captured.splitlines()]
    event_names = {event["event"] for event in events}
    assert {
        "demo.started",
        "invoice.parsed",
        "declaration.review",
        "declaration.validate",
        "artifact.written",
        "invoice.parse_failure",
        "declaration.validation_failure",
        "demo.completed",
    } <= event_names
    assert "Synthetic Buyer" not in captured
    assert "Synthetic Exporter" not in captured
    assert "/Users/" not in captured
