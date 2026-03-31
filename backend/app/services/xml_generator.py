"""
GOVCBR830 수출신고서 XML 생성기.
관세청 표준 XML 스키마: KCS_DeclarationOfEXP_830SchemaModule_1.0_standard
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from lxml import etree

from app.models.declaration import Declaration
from app.models.company_settings import CompanySettings

NS = "urn:kr:gov:kcs:data:standard:KCS_DeclarationOfEXP_830SchemaModule:1:0"
NSMAP = {
    "wco": NS,
    "kcs": NS,
}


def _w(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def _sub(parent, tag: str, text: Optional[str] = None, **attrib) -> etree._Element:
    el = etree.SubElement(parent, _w(tag), **attrib)
    if text is not None:
        el.text = str(text)
    return el


def _str(val) -> str:
    if val is None:
        return ""
    return str(val)


def _date(val) -> str:
    if val is None:
        return datetime.now().strftime("%Y%m%d")
    if hasattr(val, "strftime"):
        return val.strftime("%Y%m%d")
    return str(val).replace("-", "")[:8]


def _amount(val) -> str:
    if val is None:
        return "0"
    if isinstance(val, Decimal):
        return str(int(val))
    return str(val)


def generate_govcbr830_xml(
    declaration: Declaration,
    company_settings: Optional[CompanySettings] = None,
) -> bytes:
    cs = company_settings

    root = etree.Element(_w("Declaration"), nsmap=NSMAP)

    # ── 헤더 ──────────────────────────────────────────────────
    _sub(root, "DeclarationOfficeID", cs.customs_office if cs and cs.customs_office else "")
    _sub(root, "FunctionCode", "1")
    _sub(root, "GoodsItemQuantity", str(len(declaration.items)))
    _sub(root, "ID", "")
    _sub(root, "InvoiceAmount", _amount(declaration.total_amount))
    _sub(root, "IssueDateTime", datetime.now().strftime("%Y%m%d"))

    gross = _sub(root, "TotalGrossMassMeasure", _amount(declaration.gross_weight_kg))
    gross.set("kcsUnitCode", "KG")

    _sub(root, "TotalPackageQuantity", str(declaration.package_count or 0))
    _sub(root, "TypeCode", "GOVCBR830")
    _sub(root, "TransactionNatureCode", "11")
    _sub(root, "ResponseTypeCode", "NA")

    # ── AdditionalCode ────────────────────────────────────────
    add_code = _sub(root, "AdditionalCode")
    _sub(add_code, "ReturnReasonCode", "ZZ")
    _sub(add_code, "ReturnScopeCode", "A")

    # ── AdditionalInformation ─────────────────────────────────
    add_info = _sub(root, "AdditionalInformation")
    _sub(add_info, "StatementCode", "B")
    _sub(add_info, "StatementDescription", "")

    # ── Agent (수출대행자) ────────────────────────────────────
    agent = _sub(root, "Agent")
    if cs and cs.exporter_customs_id:
        a_id = _sub(agent, "ID", cs.exporter_customs_id)
        a_id.set("schemeAgencyID", "380")
    _sub(agent, "Name", "")

    # ── BorderTransportMeans ──────────────────────────────────
    btm = _sub(root, "BorderTransportMeans")
    _sub(btm, "Name", _str(declaration.carrier))
    _sub(btm, "EstimatedDepartureDateTime", _date(declaration.shipping_date))

    # ── Carrier ───────────────────────────────────────────────
    carrier_el = _sub(root, "Carrier")
    _sub(carrier_el, "ID", "")
    _sub(carrier_el, "Name", _str(declaration.carrier))
    carrier_contact = _sub(carrier_el, "Contact")
    _sub(carrier_contact, "Name", "")

    # ── CurrencyExchange ──────────────────────────────────────
    curr_ex = _sub(root, "CurrencyExchange")
    _sub(curr_ex, "RateNumeric", "0")

    # ── CustomsProcedure ──────────────────────────────────────
    cust_proc = _sub(root, "CustomsProcedure")
    _sub(cust_proc, "ProcessTypeCode", "H")
    _sub(cust_proc, "TypeCode", "A")

    # ── Consignment ───────────────────────────────────────────
    consignment = _sub(root, "Consignment")
    cons_item = _sub(consignment, "ConsignmentItem")
    commodity = _sub(cons_item, "Commodity")
    val_amount = _sub(commodity, "ValueAmount", _amount(declaration.total_amount))
    val_amount.set("currencyID", _str(declaration.currency_code) or "USD")
    _sub(consignment, "GoodsLocation")

    # ── Exporter ──────────────────────────────────────────────
    exporter = _sub(root, "Exporter")
    if cs and cs.exporter_customs_id:
        ex_id1 = _sub(exporter, "ID", cs.exporter_customs_id)
        ex_id1.set("schemeAgencyID", "380")
    ex_id2 = _sub(exporter, "ID", _str(
        cs.exporter_business_number if cs and cs.exporter_business_number
        else declaration.exporter_business_number
    ))
    ex_id2.set("schemeAgencyID", "ZZZ")
    _sub(exporter, "Name", _str(declaration.exporter_name))
    _sub(exporter, "RoleCode", "01")
    _sub(exporter, "TypeCode", "A")

    ex_addr = _sub(exporter, "Address")
    addr_text = _str(
        cs.exporter_address if cs and cs.exporter_address
        else declaration.exporter_address
    )
    _sub(ex_addr, "Line", addr_text)
    _sub(ex_addr, "PostcodeID", _str(cs.exporter_postcode if cs else ""))
    _sub(ex_addr, "Description", addr_text)

    ex_contact = _sub(exporter, "Contact")
    _sub(ex_contact, "RepresentativeName", _str(cs.representative_name if cs else ""))

    # ── GoodsShipment ─────────────────────────────────────────
    gs = _sub(root, "GoodsShipment")

    # Buyer
    buyer = _sub(gs, "Buyer")
    _sub(buyer, "ID", "")
    _sub(buyer, "Name", _str(declaration.buyer_name))
    buyer_addr = _sub(buyer, "Address")
    _sub(buyer_addr, "CountryCode", _str(declaration.buyer_country_code))

    # GoodsShipment > Consignment
    gs_cons = _sub(gs, "Consignment")
    _sub(gs_cons, "ContainerIndicator", "false")
    _sub(gs_cons, "GoodsStatusCode", "O")
    gs_btm = _sub(gs_cons, "BorderTransportMeans")
    _sub(gs_btm, "TypeCode", "10")
    _sub(gs_cons, "GoodsLocation")

    # CustomsValuation
    cv = _sub(gs, "CustomsValuation")
    _sub(cv, "ExitToEntryChargeAmount", "0")
    _sub(cv, "FreightChargeAmount", "0")

    # DrawBack
    db_el = _sub(gs, "DrawBack")
    _sub(db_el, "RoleCode", "1")
    _sub(db_el, "ApplicationTypeCode", "AD")

    # GovernmentAgencyGoodsItem (품목 라인)
    for item in declaration.items:
        gi = _sub(gs, "GovernmentAgencyGoodsItem")
        _sub(gi, "SequenceNumeric", str(item.item_seq).zfill(3))

        add_code_gi = _sub(gi, "AdditionalCode")
        _sub(add_code_gi, "AttachmentIndicatorCode", "N")

        add_info_gi = _sub(gi, "AdditionalInformation")
        _sub(add_info_gi, "StatementCode", "N")
        _sub(add_info_gi, "StatementTypeCode", "N")

        comm = _sub(gi, "Commodity")
        _sub(comm, "CargoDescription", _str(item.product_name_ko or item.product_name_en))

        qty = _sub(comm, "CountQuantity", _amount(item.quantity))
        qty.set("kcsUnitCode", _str(item.unit) or "EA")

        _sub(comm, "Description", _str(item.product_name_en or item.product_name_ko))
        _sub(comm, "ValueAmount", _amount(item.amount))

        classif = _sub(comm, "Classification")
        _sub(classif, "ID", _str(item.hscode))

        # DetailedCommodity (규격)
        dc = _sub(comm, "DetailedCommodity")
        _sub(dc, "SequenceNumeric", "01")
        _sub(dc, "CargoDescription", _str(item.model_spec))
        dc_qty = _sub(dc, "CountQuantity", _amount(item.quantity))
        dc_qty.set("kcsUnitCode", _str(item.unit) or "EA")
        _sub(dc, "UnitPriceAmount", _amount(item.unit_price))
        _sub(dc, "ValueAmount", _amount(item.amount))

        # GoodsMeasure
        gm = _sub(gi, "GoodsMeasure")
        net_w = _sub(gm, "NetNetWeightMeasure", "0")
        net_w.set("kcsUnitCode", "KG")

        # Origin
        origin = _sub(gi, "Origin")
        _sub(origin, "CountryCode", "KR")
        _sub(origin, "RuleCode", "A")
        origin_desc = _sub(origin, "OriginDescription")
        _sub(origin_desc, "DisplayIndicatorCode", "N")

        # Packaging
        pkg = _sub(gi, "Packaging")
        _sub(pkg, "QuantityQuantity", str(declaration.package_count or 0))
        _sub(pkg, "TypeCode", _str(declaration.package_type) or "CT")

    # TradeTerms
    tt = _sub(gs, "TradeTerms")
    _sub(tt, "ConditionCode", _str(declaration.incoterms) or "EXW")
    _sub(tt, "SettlementConditionCode", "")

    # Warehouse
    wh = _sub(gs, "Warehouse")
    _sub(wh, "Name", "")

    # ── LoadingLocation ───────────────────────────────────────
    loading = _sub(root, "LoadingLocation")
    loading_id = _str(
        cs.loading_port if cs and cs.loading_port
        else declaration.loading_port
    )
    _sub(loading, "ID", loading_id)
    # 적재항 구분: 공항(3), 항구(6) - 기본 항구
    _sub(loading, "TypeCode", "6")

    # ── Packaging ─────────────────────────────────────────────
    root_pkg = _sub(root, "Packaging")
    _sub(root_pkg, "TypeCode", _str(declaration.package_type) or "CT")

    # ── SouthNorthTrade ───────────────────────────────────────
    snt = _sub(root, "SouthNorthTrade")
    _sub(snt, "IdentificationID", "")
    _sub(snt, "TradeIndicatorCode", "N")

    # ── Submitter ─────────────────────────────────────────────
    submitter = _sub(root, "Submitter")
    _sub(submitter, "ID", _str(
        cs.declarant_code if cs and cs.declarant_code
        else declaration.declarant_code
    ))
    _sub(submitter, "Name", _str(
        cs.declarant_name if cs and cs.declarant_name
        else declaration.declarant_name
    ))
    sub_contact = _sub(submitter, "Contact")
    _sub(sub_contact, "RepresentativeName", _str(cs.representative_name if cs else ""))

    # ── UCR ───────────────────────────────────────────────────
    ucr = _sub(root, "UCR")
    _sub(ucr, "ID", _str(declaration.invoice_number))

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)
