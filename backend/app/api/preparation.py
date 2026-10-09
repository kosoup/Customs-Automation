"""Ephemeral preparation API: local processing, no client paths or database writes."""
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.services.preparation import PROFILE_KEYS, prepare_pdf

router = APIRouter(prefix='/api/preparation', tags=['preparation'])


@router.post('/pdf')
async def prepare(file: UploadFile = File(...), profile: str = Form('{}')):
    try:
        values = json.loads(profile)
        if not isinstance(values, dict) or any(
            key not in PROFILE_KEYS or not isinstance(value, str) or len(value) > 200
            for key, value in values.items()
        ):
            raise ValueError('잘못된 설정값')
    except (ValueError, TypeError) as error:
        raise HTTPException(422, '설정값 형식을 확인하세요.') from error
    try:
        content = await file.read(10 * 1024 * 1024 + 1)
    finally:
        await file.close()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, 'PDF는 10MB 이하로 올려 주세요.')
    if not content.startswith(b'%PDF-'):
        raise HTTPException(415, 'PDF 파일만 지원합니다.')
    try:
        return await run_in_threadpool(prepare_pdf, content, values)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
