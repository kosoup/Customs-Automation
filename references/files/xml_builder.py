"""
XML 생성 서비스
Pydantic 모델 → KCS WCO XML 변환
"""
from lxml import etree
from app.models.declaration import DeclarationRequest, GovernmentAgencyGoodsItemModel
from typing import Optional


WCO_NS = "urn:kr:gov:kcs:data:standard:KCS_DeclarationOfEXP_DJPSchemaModule:1:0"
KCS_NS = "urn:kr:gov:kcs:data:standard:KCS_DeclarationOfEXP_DJPSchemaModule:1:0"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

NSMAP = {
    "wco": WCO_NS,
    "kcs": KCS_NS,
    "xsi": XSI_NS,
}

def _w(tag: str) -> str:
    return f"{{{WCO_NS}}}{tag}"

def _k(tag: str) -> str:
    return f"{{{KCS_NS}}}{tag}"

def _sub(parent, tag: str, text: Optional[str], ns: str = "wco") -> Optional[etree._Element]:
    """값이 있을 때만 서브엘리먼트 추가"""
    if text is None or str(text).strip() == "":
        return None
    ns_func = _w if ns == "wco" else _k
    el = etree.SubElement(parent, ns_func(tag))
    el.text = str(text)
    return el

def _sub_attr(parent, tag: str, text: Optional[str], attr: dict, ns: str = "wco") -> Optional[etree._Element]:
    """속성 포함 서브엘리먼트"""
    if text is None or str(text).strip() == "":
        return None
    ns_func = _w if ns == "wco" else _k
    el = etree.SubElement(parent, ns_func(tag), attrib=attr)
    el.text = str(text)
    return el


def build_xml(req: DeclarationRequest) -> bytes:
    """DeclarationRequest → XML bytes"""

    root = etree.Element(_w("Declaration"), nsmap=NSMAP)
    root.set(
        f"{{{XSI_NS}}}schemaLocation",
        f"{WCO_NS} ../../schema4G/kcs/data/standard/KCS_DeclarationOfEXP_DJPSchemaModule_1.0_standard.xsd"
    )

    # ── 기본정보 ──────────────────────────────────────────────────────────────
    _sub(root, "DeclarationOfficeID", req.declaration_office_id)
    _sub(root, "GoodsItemQuantity", len(req.goods_items))
    _sub(root, "ID", req.declaration_id)
    _sub(root, "InvoiceAmount", req.invoice_amount)
    _sub(root, "IssueDateTime", req.issue_date)
    _sub(root, "TotalGrossMassMeasure", req.total_gross_mass)
    _sub(root, "TotalPackageQuantity", req.total_package_quantity)
    _sub(root, "TypeCode", "GOVCBRDJP")
    _sub(root, "TransactionNatureCode", req.transaction_nature_code)

    # ── AdditionalDocument (주문번호) ─────────────────────────────────────────
    add_doc = etree.SubElement(root, _w("AdditionalDocument"))
    _sub(add_doc, "AmountAmount", req.adjustment_amount)
    _sub(add_doc, "ID", req.order_id)

    # ── AdditionalInformation ─────────────────────────────────────────────────
    add_info = etree.SubElement(root, _w("AdditionalInformation"))
    _sub(add_info, "Content", req.webpage_url)
    _sub(add_info, "StatementCode", req.declarant.statement_code)
    _sub(add_info, "StatementDescription", req.statement_description)

    # ── Agent ─────────────────────────────────────────────────────────────────
    if req.agent:
        agent = etree.SubElement(root, _w("Agent"))
        _sub_attr(agent, "ID", req.agent.customs_code, {"schemeAgencyID": "380"})
        _sub_attr(agent, "ID", req.agent.kts_code, {"schemeAgencyID": "KTS"})
        _sub(agent, "Name", req.agent.name)

    # ── BorderTransportMeans ──────────────────────────────────────────────────
    btm = etree.SubElement(root, _w("BorderTransportMeans"))
    _sub(btm, "TypeCode", req.transport_type_code)

    # ── CurrencyExchange ──────────────────────────────────────────────────────
    ce = etree.SubElement(root, _w("CurrencyExchange"))
    _sub(ce, "RateNumeric", req.rate_numeric)

    # ── CustomsProcedure ──────────────────────────────────────────────────────
    cp = etree.SubElement(root, _w("CustomsProcedure"))
    _sub(cp, "ProcessTypeCode", req.process_type_code, ns="kcs")

    # ── Consignment (결제금액) ────────────────────────────────────────────────
    consignment = etree.SubElement(root, _w("Consignment"))
    cons_item = etree.SubElement(consignment, _w("ConsignmentItem"))
    commodity = etree.SubElement(cons_item, _w("Commodity"))
    if req.value_amount is not None:
        val_el = etree.SubElement(commodity, _w("ValueAmount"), attrib={"currencyID": req.currency_id})
        val_el.text = str(req.value_amount)

    # ── Declarant ─────────────────────────────────────────────────────────────
    declarant = etree.SubElement(root, _w("Declarant"))
    _sub(declarant, "ID", req.declarant.id)
    _sub(declarant, "Name", req.declarant.name)

    # ── Exporter ──────────────────────────────────────────────────────────────
    exporter = etree.SubElement(root, _w("Exporter"))
    _sub_attr(exporter, "ID", req.exporter.biz_number, {"schemeAgencyID": "ZZZ"})
    _sub_attr(exporter, "ID", req.exporter.customs_code, {"schemeAgencyID": "380"})
    _sub_attr(exporter, "ID", req.exporter.kts_code, {"schemeAgencyID": "KTS"})
    _sub(exporter, "Name", req.exporter.name)
    _sub(exporter, "RoleCode", req.exporter.role_code)
    if req.exporter.address:
        addr = req.exporter.address
        addr_el = etree.SubElement(exporter, _w("Address"))
        _sub(addr_el, "CountrySubDivisionID", addr.country_sub_division_id)
        _sub(addr_el, "Line", addr.line)
        _sub(addr_el, "PostcodeID", addr.postcode_id)
        _sub(addr_el, "BuildingNumber", addr.building_number, ns="kcs")
        _sub(addr_el, "Description", addr.description, ns="kcs")
    if req.exporter.representative_name:
        contact = etree.SubElement(exporter, _w("Contact"))
        _sub(contact, "RepresentativeName", req.exporter.representative_name, ns="kcs")

    # ── Express ───────────────────────────────────────────────────────────────
    if req.express_id:
        express = etree.SubElement(root, _w("Express"))
        _sub(express, "ID", req.express_id, ns="kcs")

    # ── GoodsShipment ─────────────────────────────────────────────────────────
    gs = etree.SubElement(root, _w("GoodsShipment"))

    if req.buyer:
        buyer = etree.SubElement(gs, _w("Buyer"))
        _sub(buyer, "Name", req.buyer.name)

    if req.delivery_id:
        gs_add_doc = etree.SubElement(gs, _w("AdditionalDocument"))
        _sub(gs_add_doc, "ID", req.delivery_id)

    gs_cons = etree.SubElement(gs, _w("Consignment"))
    goods_loc = etree.SubElement(gs_cons, _w("GoodsLocation"))
    _sub(goods_loc, "ID", req.goods_location_id)
    if req.goods_location_address:
        gl_addr = etree.SubElement(goods_loc, _w("Address"))
        _sub(gl_addr, "Description", req.goods_location_address, ns="kcs")

    cust_val = etree.SubElement(gs, _w("CustomsValuation"))
    _sub(cust_val, "FreightChargeAmount", req.freight_charge)

    dest = etree.SubElement(gs, _w("Destination"))
    _sub(dest, "CountryCode", req.destination_country)

    # ── GovernmentAgencyGoodsItem (란) ────────────────────────────────────────
    for item in req.goods_items:
        _build_goods_item(gs, item)

    # ── TradeTerms ────────────────────────────────────────────────────────────
    trade = etree.SubElement(gs, _w("TradeTerms"))
    _sub(trade, "ConditionCode", req.condition_code)
    _sub(trade, "SettlementConditionCode", req.settlement_code, ns="kcs")

    # ── Warehouse ─────────────────────────────────────────────────────────────
    if req.warehouse_name:
        wh = etree.SubElement(gs, _w("Warehouse"))
        _sub(wh, "Name", req.warehouse_name)

    # ── LoadingLocation ───────────────────────────────────────────────────────
    loading = etree.SubElement(root, _w("LoadingLocation"))
    _sub(loading, "ID", req.loading_location)

    # ── Submitter ─────────────────────────────────────────────────────────────
    submitter = etree.SubElement(root, _w("Submitter"))
    _sub(submitter, "ID", req.submitter.id)
    _sub(submitter, "Name", req.submitter.name)
    _sub(submitter, "RoleCode", req.submitter.role_code)

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")


def _build_goods_item(parent, item: GovernmentAgencyGoodsItemModel):
    gi = etree.SubElement(parent, _w("GovernmentAgencyGoodsItem"))
    _sub(gi, "CustomsValueAmount", item.customs_value_amount)
    _sub(gi, "SequenceNumeric", f"{item.sequence_numeric:03d}")

    add_info = etree.SubElement(gi, _w("AdditionalInformation"))
    _sub(add_info, "StatementCode", item.exporter_type_code)

    commodity = etree.SubElement(gi, _w("Commodity"))
    _sub(commodity, "CountQuantity", item.count_quantity)
    _sub(commodity, "Description", item.description)
    _sub(commodity, "ValueAmount", item.value_amount)
    cls_el = etree.SubElement(commodity, _w("Classification"))
    _sub(cls_el, "ID", item.hs_code)

    for detail in item.detailed_commodities:
        dc = etree.SubElement(commodity, _w("DetailedCommodity"))
        _sub(dc, "SequenceNumeric", detail.sequence_numeric)
        _sub(dc, "CargoDescription", detail.cargo_description)
        _sub(dc, "CountQuantity", detail.count_quantity)
        _sub(dc, "UnitPriceAmount", detail.unit_price_amount, ns="kcs")
        _sub(dc, "ValueAmount", detail.value_amount, ns="kcs")

    if item.draw_back:
        db = etree.SubElement(gi, _w("DrawBack"))
        _sub(db, "RoleCode", item.draw_back.role_code, ns="kcs")
        _sub(db, "ApplicationTypeCode", item.draw_back.application_type_code, ns="kcs")

    meas = etree.SubElement(gi, _w("GoodsMeasure"))
    _sub(meas, "NetNetWeightMeasure", item.net_weight)

    if item.manufacturer:
        mfg = etree.SubElement(gi, _w("Manufacturer"))
        _sub_attr(mfg, "ID", item.manufacturer.biz_number, {"schemeAgencyID": "ZZZ"})
        _sub_attr(mfg, "ID", item.manufacturer.kts_code, {"schemeAgencyID": "KTS"})
        _sub_attr(mfg, "ID", item.manufacturer.customs_code, {"schemeAgencyID": "380"})
        _sub(mfg, "Name", item.manufacturer.name)
