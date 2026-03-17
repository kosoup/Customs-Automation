from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel


class DeclarationItemBase(BaseModel):
    item_seq: int
    product_name_ko: Optional[str] = None
    product_name_en: Optional[str] = None
    hscode: Optional[str] = None
    model_spec: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    amount: Optional[Decimal] = None


class DeclarationItemCreate(DeclarationItemBase):
    pass


class DeclarationItemResponse(DeclarationItemBase):
    id: int
    declaration_id: int

    class Config:
        from_attributes = True


class DeclarationBase(BaseModel):
    declarant_code: Optional[str] = None
    declarant_name: Optional[str] = None
    exporter_name: Optional[str] = None
    exporter_business_number: Optional[str] = None
    exporter_address: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_country_code: Optional[str] = None
    buyer_address: Optional[str] = None
    incoterms: Optional[str] = None
    currency_code: Optional[str] = None
    payment_method: Optional[str] = None
    loading_port: Optional[str] = None
    destination_country_code: Optional[str] = None
    destination_port: Optional[str] = None
    carrier: Optional[str] = None
    shipping_date: Optional[date] = None
    net_weight_kg: Optional[Decimal] = None
    gross_weight_kg: Optional[Decimal] = None
    package_type: Optional[str] = None
    package_count: Optional[int] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    total_amount: Optional[Decimal] = None


class DeclarationCreate(DeclarationBase):
    items: List[DeclarationItemCreate] = []


class DeclarationUpdate(DeclarationBase):
    items: Optional[List[DeclarationItemCreate]] = None


class DeclarationResponse(DeclarationBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    submission_ref: Optional[str] = None
    unipass_ref: Optional[str] = None
    items: List[DeclarationItemResponse] = []

    class Config:
        from_attributes = True


class DeclarationListResponse(BaseModel):
    id: int
    status: str
    exporter_name: Optional[str] = None
    buyer_name: Optional[str] = None
    invoice_number: Optional[str] = None
    total_amount: Optional[Decimal] = None
    currency_code: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ValidationError(BaseModel):
    field: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    errors: List[ValidationError] = []
