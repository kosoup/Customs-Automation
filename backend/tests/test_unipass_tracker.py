from app.services.submission.unipass_tracker import _parse_status_xml


def test_parse_status_xml_uses_primary_tag_even_when_it_has_no_children():
    """Regression: Element truthiness is len()-based, so a leaf element with
    text but no children used to be silently discarded by `a or b` chains."""
    xml_text = (
        "<response>"
        "<tCd>00</tCd><tMsg>정상처리</tMsg>"
        "<expDclrStts>수리</expDclrStts>"
        "<expDclrAceptNo>12345678</expDclrAceptNo>"
        "<expDclrAceptDt>20260101</expDclrAceptDt>"
        "</response>"
    )

    result = _parse_status_xml(xml_text)

    assert result["code"] == "00"
    assert result["message"] == "정상처리"
    assert result["declaration_status"] == "수리"
    assert result["accept_number"] == "12345678"
    assert result["accept_date"] == "20260101"


def test_parse_status_xml_falls_back_to_secondary_tag():
    xml_text = "<response><errCd>99</errCd><errMsg>오류</errMsg></response>"

    result = _parse_status_xml(xml_text)

    assert result["code"] == "99"
    assert result["message"] == "오류"
