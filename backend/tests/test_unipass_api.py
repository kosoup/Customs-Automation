import pytest

from app.config import settings
from app.services import unipass_api


@pytest.mark.asyncio
async def test_unipass_calls_fail_closed_without_keys(monkeypatch) -> None:
    monkeypatch.setattr(settings, "UNIPASS_KEY_HS_SEARCH", None)
    monkeypatch.setattr(settings, "UNIPASS_KEY_TARIFF", None)
    monkeypatch.setattr(settings, "UNIPASS_KEY_CUSTOMS_CHECK", None)

    search = await unipass_api.search_hs("widget")
    tariff = await unipass_api.get_tariff("1234567890")
    confirmation = await unipass_api.check_customs_confirmation("1234567890")

    assert search["items"] == []
    assert "설정되지 않았습니다" in search["error"]
    assert tariff["hscode"] == "1234567890"
    assert "설정되지 않았습니다" in tariff["error"]
    assert confirmation["is_target"] is False
    assert "설정되지 않았습니다" in confirmation["error"]
