"""
KCS 전자상거래 수출신고 Pydantic 모델
WCO Declaration 스키마 기반
"""
from __future__ import annotations
from typing import List, Optional, Literal
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
import re


# ── 공통 ────────────────────────────────────────────────────────────────────

class AddressModel(BaseModel):
    country_sub_division_id: Optional[str] = Field(None, description="도로명코드", max_length=10)
    line: Optional[str] = Field(None, description="상세주소", max_length=200)
    postcode_id: Optional[str] = Field(None, description="우편번호", max_length=5)
    building_number: Optional[str] = Field(None, description="건물관리번호", max_length=20)
    description: Optional[str] = Field(None, description="주소", max_length=300)


# ── 당사자 ───────────────────────────────────────────────────────────────────

class ExporterModel(BaseModel):
    biz_number: str = Field(..., description="사업자등록번호(ZZZ)", max_length=13)
    customs_code: Optional[str] = Field(None, description="통관고유부호(380)", max_length=15)
    kts_code: Optional[str] = Field(None, description="사업장일련번호(KTS)", max_length=15)
    name: str = Field(..., description="수출화주 상호", max_length=100)
    role_code: Literal["01", "02"] = Field("01", description="사업자구분(01:사업자, 02:개인)")
    representative_name: Optional[str] = Field(None, description="대표자명", max_length=50)
    address: Optional[AddressModel] = None

    @field_validator("biz_number")
    @classmethod
    def validate_biz_number(cls, v: str) -> str:
        if not re.match(r"^\d{8,13}$", v):
            raise ValueError("사업자등록번호는 8~13자리 숫자여야 합니다.")
        return v


class DeclarantModel(BaseModel):
    id: str = Field(..., description="신고인 부호", max_length=14)
    name: str = Field(..., description="신고인 상호", max_length=100)
    statement_code: Optional[str] = Field(None, description="신고인 사서함부호", max_length=20)


class AgentModel(BaseModel):
    customs_code: Optional[str] = Field(None, description="통관고유부호(380)", max_length=15)
    kts_code: Optional[str] = Field(None, description="사업장일련번호(KTS)", max_length=15)
    name: Optional[str] = Field(None, description="수출대행자 상호", max_length=100)


class SubmitterModel(BaseModel):
    id: str = Field(..., description="제출자 사업자등록번호", max_length=20)
    name: str = Field(..., description="제출자 상호", max_length=100)
    role_code: Literal["01", "02", "03"] = Field("01", description="01:수출자 02:관세사 03:특송")


class BuyerModel(BaseModel):
    name: str = Field(..., description="구매자 상호", max_length=200)


# ── 품목 (란) ────────────────────────────────────────────────────────────────

class DetailedCommodityModel(BaseModel):
    sequence_numeric: int = Field(..., ge=1, le=99, description="규격번호")
    cargo_description: str = Field(..., description="모델/규격", max_length=200)
    count_quantity: int = Field(..., ge=0, description="수량")
    unit_price_amount: Decimal = Field(..., ge=0, description="단가")
    value_amount: Decimal = Field(..., ge=0, description="금액")


class ManufacturerModel(BaseModel):
    biz_number: Optional[str] = Field(None, description="사업자등록번호(ZZZ)", max_length=13)
    kts_code: Optional[str] = Field(None, description="사업장일련번호(KTS)", max_length=15)
    customs_code: Optional[str] = Field(None, description="통관고유부호(380)", max_length=15)
    name: Optional[str] = Field(None, description="제조자 상호", max_length=100)


class DrawBackModel(BaseModel):
    role_code: Literal["01", "02"] = Field("01", description="환급신청인(01:제조자, 02:수출자)")
    application_type_code: Literal["AD", "MN", "NO"] = Field(
        "AD", description="AD:자동간이정액 MN:개별환급 NO:해당없음"
    )


class GovernmentAgencyGoodsItemModel(BaseModel):
    sequence_numeric: int = Field(..., ge=1, le=999, description="란번호")
    customs_value_amount: Decimal = Field(..., ge=0, description="신고금액")
    exporter_type_code: Literal["C", "T", "M"] = Field("C", description="수출자구분")
    hs_code: str = Field(..., description="세번부호(10단위)", min_length=6, max_length=10)
    description: str = Field(..., description="품명", max_length=500)
    count_quantity: int = Field(..., ge=0, description="수량")
    value_amount: Optional[Decimal] = Field(None, description="조정금액")
    net_weight: Optional[Decimal] = Field(None, ge=0, description="순중량(kg)")
    draw_back: Optional[DrawBackModel] = DrawBackModel()
    manufacturer: Optional[ManufacturerModel] = None
    detailed_commodities: List[DetailedCommodityModel] = Field(default_factory=list)

    @field_validator("hs_code")
    @classmethod
    def validate_hs_code(cls, v: str) -> str:
        if not re.match(r"^\d{6,10}$", v):
            raise ValueError("세번부호는 6~10자리 숫자여야 합니다.")
        return v


# ── 메인 신고서 ──────────────────────────────────────────────────────────────

class DeclarationRequest(BaseModel):
    # 기본정보
    declaration_office_id: str = Field(..., description="신고세관/과", max_length=8)
    declaration_id: str = Field(..., description="전자상거래수출신고번호", max_length=20)
    issue_date: str = Field(..., description="신고일자 (YYYYMMDD)", pattern=r"^\d{8}$")
    invoice_amount: Decimal = Field(..., ge=0, description="총신고가격(FOB)")
    total_gross_mass: Optional[Decimal] = Field(None, ge=0, description="총중량합계")
    total_package_quantity: Optional[int] = Field(None, ge=0, description="총수량")
    rate_numeric: Optional[Decimal] = Field(None, ge=0, description="환율")
    process_type_code: Literal["01", "02", "03"] = Field("01", description="신고구분")
    transaction_nature_code: Literal["01", "02", "03"] = Field("01", description="거래구분")
    transport_type_code: Literal["01", "02"] = Field("01", description="01:해상 02:항공")

    # 주문/결제
    order_id: str = Field(..., description="주문번호", max_length=50)
    delivery_id: Optional[str] = Field(None, description="배송번호", max_length=50)
    adjustment_amount: Optional[Decimal] = Field(None, description="총조정금액")
    currency_id: str = Field("KRW", description="결제통화")
    value_amount: Optional[Decimal] = Field(None, ge=0, description="결제금액")
    freight_charge: Optional[Decimal] = Field(None, ge=0, description="운임")
    condition_code: str = Field("DAP", description="인도조건", max_length=5)
    settlement_code: Literal["01", "02", "03", "04"] = Field("01", description="결제방법")
    loading_location: Optional[str] = Field(None, description="적재항", max_length=10)

    # 물품정보
    goods_location_id: Optional[str] = Field(None, description="물품소재지부호", max_length=10)
    goods_location_address: Optional[str] = Field(None, description="물품소재지주소", max_length=300)
    destination_country: Optional[str] = Field(None, description="목적국", max_length=3)
    warehouse_name: Optional[str] = Field(None, description="장치장소명", max_length=100)
    webpage_url: Optional[str] = Field(None, description="웹페이지 URL", max_length=500)
    statement_description: Optional[str] = Field(None, description="신고인기재란", max_length=1000)

    # 당사자
    exporter: ExporterModel
    declarant: DeclarantModel
    agent: Optional[AgentModel] = None
    submitter: SubmitterModel
    buyer: Optional[BuyerModel] = None
    express_id: Optional[str] = Field(None, description="특송업체부호", max_length=10)

    # 품목 (란)
    goods_items: List[GovernmentAgencyGoodsItemModel] = Field(
        ..., min_length=1, max_length=999, description="품목 란 (1~999)"
    )

    @field_validator("goods_items")
    @classmethod
    def validate_sequence(cls, items: list) -> list:
        for i, item in enumerate(items, 1):
            if item.sequence_numeric != i:
                raise ValueError(f"란번호가 연속되지 않습니다. {i}번 란에 {item.sequence_numeric} 입력됨")
        return items


# ── 응답 모델 ────────────────────────────────────────────────────────────────

class ValidationErrorDetail(BaseModel):
    field: str
    message: str


class DeclarationResponse(BaseModel):
    success: bool
    message: str
    declaration_number: Optional[str] = None      # 수리 시 신고번호
    receipt_number: Optional[str] = None           # 접수번호
    errors: Optional[List[ValidationErrorDetail]] = None
    raw_response: Optional[str] = None             # UNI-PASS 원문 응답


class SignRequest(BaseModel):
    xml_content: str = Field(..., description="서명할 XML 원문")
    cert_alias: str = Field(..., description="인증서 alias (keystore 내)")
    keystore_path: str = Field(..., description="P12/JKS 경로")
    keystore_password: str = Field(..., description="keystore 비밀번호")


class SignResponse(BaseModel):
    success: bool
    signed_xml: Optional[str] = None
    error: Optional[str] = None
