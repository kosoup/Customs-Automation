# Customs Automation

PDF 또는 Excel 인보이스를 파싱해 수출신고서 초안을 만들고, 검증·XML/파일 내보내기·제출 이력을 관리하는 FastAPI/React 애플리케이션입니다.

## 시작하기

필수 도구는 Python 3.12와 Node.js 22입니다.

```bash
./scripts/bootstrap
cp backend/.env.example backend/.env
```

터미널 두 개에서 각각 실행합니다.

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

```bash
cd frontend
npm run dev
```

프런트엔드는 기본적으로 `http://localhost:5173`, API는 `http://localhost:8000`에서 실행됩니다.

## 검증

```bash
./scripts/check
```

이 명령은 백엔드 테스트, 프런트엔드 린트, 프로덕션 빌드를 순서대로 실행합니다. GitHub Actions도 같은 bootstrap/check 경로를 사용합니다.

## 설정과 데이터 안전

- 실제 비밀값은 `backend/.env`에만 두고 커밋하지 않습니다.
- 업로드는 PDF와 `.xlsx`만 지원하며 기본 한도는 10MB입니다. `MAX_UPLOAD_BYTES`로 조정할 수 있습니다.
- 운영 프런트엔드 주소는 `CORS_ORIGINS`에 쉼표로 구분해 지정합니다.
- `backend/customs.db`, `backend/uploads/`, 실제 관세 문서와 개인정보는 저장소에 넣지 않습니다.
- UNI-PASS 및 uTradeHub 연동 키는 필요한 서비스만 설정합니다.

## 현재 신뢰 경계

GOVCBR830 XML은 회귀 테스트로 구조와 금액 정밀도를 보호하지만, 공개된 관세청 공식 XSD를 확보해 검증하는 단계는 아직 포함하지 않습니다. 실제 전송 전에는 연계 사업자가 제공한 최신 명세와 인증 환경으로 적합성을 확인해야 합니다.
