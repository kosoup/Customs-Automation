# Customs Automation (관세 신고 자동화)

## Project Structure
- `backend/` - FastAPI + SQLAlchemy + SQLite
- `frontend/` - React 19 + Vite + Ant Design 6 + TypeScript

## Run
- 최초 설치: `./scripts/bootstrap`
- Backend: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev`

## Key Libraries
- PDF parsing: pdfplumber
- Excel parsing: openpyxl
- API client: axios + react-query

## Conventions
- 답변은 한국어로
- Git remote: github.com/kosoup/Customs-Automation (private)

## Verification
- 전체 검사: `./scripts/check`
- Backend: `cd backend && .venv/bin/pytest`
- Frontend: `cd frontend && npm run lint && npm run build`
- UI 변경은 영향받은 사용자 흐름을 브라우저에서 확인한다.

## Safety
- 실제 관세 문서, 개인정보, 인증정보를 커밋하지 않는다.
- 테스트에서 운영 Uni-Pass 엔드포인트를 호출하지 않는다.
- `backend/customs.db`와 `backend/uploads/`는 사용자 데이터로 취급한다.
- DB 스키마를 변경하면 Alembic 마이그레이션 필요 여부를 확인한다.
