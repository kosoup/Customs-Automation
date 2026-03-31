from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CompanySettingsUpdate(BaseModel):
    declarant_code: Optional[str] = None
    declarant_name: Optional[str] = None
    representative_name: Optional[str] = None
    exporter_business_number: Optional[str] = None
    exporter_customs_id: Optional[str] = None
    exporter_address: Optional[str] = None
    exporter_postcode: Optional[str] = None
    loading_port: Optional[str] = None
    customs_office: Optional[str] = None


class CompanySettingsResponse(BaseModel):
    id: int
    declarant_code: Optional[str] = None
    declarant_name: Optional[str] = None
    representative_name: Optional[str] = None
    exporter_business_number: Optional[str] = None
    exporter_customs_id: Optional[str] = None
    exporter_address: Optional[str] = None
    exporter_postcode: Optional[str] = None
    loading_port: Optional[str] = None
    customs_office: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
