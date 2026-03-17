from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import String, Date, DateTime, Numeric, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Declaration(Base):
    __tablename__ = "declarations"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|validated|submitted|accepted|rejected

    # 신고인
    declarant_code: Mapped[Optional[str]] = mapped_column(String(5))
    declarant_name: Mapped[Optional[str]] = mapped_column(String(100))

    # 수출자
    exporter_name: Mapped[Optional[str]] = mapped_column(String(200))
    exporter_business_number: Mapped[Optional[str]] = mapped_column(String(20))
    exporter_address: Mapped[Optional[str]] = mapped_column(String(500))

    # 구매자
    buyer_name: Mapped[Optional[str]] = mapped_column(String(200))
    buyer_country_code: Mapped[Optional[str]] = mapped_column(String(2))
    buyer_address: Mapped[Optional[str]] = mapped_column(String(500))

    # 무역조건
    incoterms: Mapped[Optional[str]] = mapped_column(String(3))
    currency_code: Mapped[Optional[str]] = mapped_column(String(3))
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))

    # 운송
    loading_port: Mapped[Optional[str]] = mapped_column(String(100))
    destination_country_code: Mapped[Optional[str]] = mapped_column(String(2))
    destination_port: Mapped[Optional[str]] = mapped_column(String(100))
    carrier: Mapped[Optional[str]] = mapped_column(String(200))
    shipping_date: Mapped[Optional[date]] = mapped_column(Date)

    # 중량/포장
    net_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    gross_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    package_type: Mapped[Optional[str]] = mapped_column(String(20))
    package_count: Mapped[Optional[int]] = mapped_column(Integer)

    # 인보이스
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50))
    invoice_date: Mapped[Optional[date]] = mapped_column(Date)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))

    # 제출 결과
    submission_ref: Mapped[Optional[str]] = mapped_column(String(50))
    unipass_ref: Mapped[Optional[str]] = mapped_column(String(50))

    # 관계
    items: Mapped[List["DeclarationItem"]] = relationship(back_populates="declaration", cascade="all, delete-orphan")


class DeclarationItem(Base):
    __tablename__ = "declaration_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    declaration_id: Mapped[int] = mapped_column(ForeignKey("declarations.id"))
    item_seq: Mapped[int] = mapped_column(Integer)  # 란번호

    product_name_ko: Mapped[Optional[str]] = mapped_column(String(200))
    product_name_en: Mapped[Optional[str]] = mapped_column(String(200))
    hscode: Mapped[Optional[str]] = mapped_column(String(10))
    model_spec: Mapped[Optional[str]] = mapped_column(String(200))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    unit: Mapped[Optional[str]] = mapped_column(String(10))
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))

    declaration: Mapped["Declaration"] = relationship(back_populates="items")
