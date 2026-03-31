from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 신고인 정보
    declarant_code: Mapped[Optional[str]] = mapped_column(String(5))
    declarant_name: Mapped[Optional[str]] = mapped_column(String(100))
    representative_name: Mapped[Optional[str]] = mapped_column(String(100))

    # 수출자 정보
    exporter_business_number: Mapped[Optional[str]] = mapped_column(String(20))
    exporter_customs_id: Mapped[Optional[str]] = mapped_column(String(15))   # 통관고유부호
    exporter_address: Mapped[Optional[str]] = mapped_column(String(500))
    exporter_postcode: Mapped[Optional[str]] = mapped_column(String(10))

    # 기본 운송
    loading_port: Mapped[Optional[str]] = mapped_column(String(10))    # 적재항 코드 (e.g. KRPUS)
    customs_office: Mapped[Optional[str]] = mapped_column(String(10))  # 신고세관 코드 (e.g. 010)

    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
