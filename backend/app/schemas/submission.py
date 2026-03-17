from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SubmissionResponse(BaseModel):
    id: int
    declaration_id: int
    submitted_at: datetime
    method: str
    status: str
    tracking_number: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TrackResponse(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None
    declaration_status: Optional[str] = None
    accept_number: Optional[str] = None
    accept_date: Optional[str] = None
