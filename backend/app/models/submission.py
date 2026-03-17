from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    declaration_id: Mapped[int] = mapped_column(ForeignKey("declarations.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    method: Mapped[str] = mapped_column(String(20))        # utradehub | file_export
    status: Mapped[str] = mapped_column(String(20))        # pending | success | failed
    response_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
