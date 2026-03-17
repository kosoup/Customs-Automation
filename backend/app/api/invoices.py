import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.models.declaration import Declaration, DeclarationItem
from app.models.invoice import Invoice
from app.schemas.invoice import UploadResponse
from app.services.mapper import map_to_declaration
from app.services.parser.excel_parser import ExcelParser
from app.services.parser.pdf_parser import PdfParser

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls"}
TEMPLATE_DIR = Path(__file__).parent.parent / "services" / "parser" / "templates"


def _load_template(name: Optional[str]) -> Optional[dict]:
    if not name:
        path = TEMPLATE_DIR / "default.json"
    else:
        path = TEMPLATE_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_invoice(
    file: UploadFile = File(...),
    template_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    # 확장자 검증
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"지원하지 않는 파일 형식입니다: {ext}")

    # 저장 경로
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    save_path = upload_dir / f"{timestamp}_{file.filename}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 파싱
    template = _load_template(template_name)
    try:
        if ext == ".pdf":
            parsed = PdfParser().parse(str(save_path), template)
        else:
            parsed = ExcelParser().parse(str(save_path), template)
    except Exception as e:
        raise HTTPException(422, f"파일 파싱 실패: {e}")

    # 매핑 → 신고서 초안 생성
    decl_data = map_to_declaration(parsed)
    items_data = decl_data.pop("items", [])

    decl = Declaration(**decl_data)
    for item_data in items_data:
        decl.items.append(DeclarationItem(**item_data))
    db.add(decl)
    await db.flush()  # id 획득

    # Invoice 레코드 저장
    invoice = Invoice(
        filename=file.filename,
        file_type="pdf" if ext == ".pdf" else "xlsx",
        file_path=str(save_path),
        parsed_at=datetime.now(timezone.utc),
        parser_template=template_name or "default",
        declaration_id=decl.id,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)

    return UploadResponse(
        invoice=invoice,
        declaration_id=decl.id,
        parsed_data=decl_data,
    )
