from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    declaration_id: int
    submitted_at: datetime
    method: str
    status: str
    tracking_number: Optional[str] = None
    error_message: Optional[str] = None

class TrackResponse(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None
    declaration_status: Optional[str] = None
    accept_number: Optional[str] = None
    accept_date: Optional[str] = None
