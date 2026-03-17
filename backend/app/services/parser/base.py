from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, List


@dataclass
class ParsedItem:
    item_seq: int
    product_name_ko: Optional[str] = None
    product_name_en: Optional[str] = None
    hscode: Optional[str] = None
    model_spec: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    amount: Optional[Decimal] = None


@dataclass
class ParsedInvoice:
    """파서 출력의 통일된 구조."""
    # 수출자
    exporter_name: Optional[str] = None
    exporter_address: Optional[str] = None

    # 구매자
    buyer_name: Optional[str] = None
    buyer_country_code: Optional[str] = None
    buyer_address: Optional[str] = None

    # 인보이스 기본 정보
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None   # YYYY-MM-DD

    # 무역조건
    incoterms: Optional[str] = None
    currency_code: Optional[str] = None
    payment_method: Optional[str] = None
    total_amount: Optional[Decimal] = None

    # 운송
    loading_port: Optional[str] = None
    destination_country_code: Optional[str] = None
    destination_port: Optional[str] = None

    # 중량/포장
    net_weight_kg: Optional[Decimal] = None
    gross_weight_kg: Optional[Decimal] = None
    package_type: Optional[str] = None
    package_count: Optional[int] = None

    # 품목
    items: List[ParsedItem] = field(default_factory=list)


class BaseParser(ABC):
    """모든 파서가 구현해야 하는 인터페이스."""

    @abstractmethod
    def parse(self, file_path: str, template: Optional[dict] = None) -> ParsedInvoice:
        """파일을 파싱하여 ParsedInvoice를 반환한다."""
        ...
