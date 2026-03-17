from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(10))   # pdf | xlsx
    file_path: Mapped[str] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    parser_template: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    declaration_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("declarations.id"), nullable=True
    )
