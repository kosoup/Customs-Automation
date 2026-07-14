from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    uploaded_at: datetime
    parsed_at: Optional[datetime] = None
    parser_template: Optional[str] = None
    declaration_id: Optional[int] = None

class UploadResponse(BaseModel):
    invoice: InvoiceResponse
    declaration_id: int
    parsed_data: dict
