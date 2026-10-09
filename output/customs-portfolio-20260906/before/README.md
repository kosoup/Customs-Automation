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

## 2~3분 합성 데이터 데모

```bash
./scripts/demo
```

이 명령은 외부 서버나 실제 관세 문서를 사용하지 않고 임시 SQLite 데이터베이스에서 다음 흐름을 실행합니다.

1. 코드에서 생성한 합성 XLSX 인보이스를 FastAPI 업로드 경로로 전달합니다.
2. 파싱 결과로 신고서 초안을 만들고, 사람이 검토해 국가코드·중량 등 파서가 채우지 않는 값을 보완하는 상황을 재현합니다.
3. 필수값, 코드 형식, HS 코드, 품목 금액 합계를 검증합니다.
4. 검증을 통과한 초안을 GOVCBR830 형식 XML, CSV, XLSX로 내보냅니다.
5. 깨진 XLSX의 422 거부·임시 파일 정리와, 잘못된 국가코드·HS 코드·금액 합계의 검증 실패를 확인합니다.

진행 상태는 한 줄에 한 건씩 JSON으로 출력합니다. 로그에는 인보이스 추출값, 거래 당사자명, 주소, 원본 파일명을 넣지 않고 이벤트·상태·오류 필드·건수만 기록합니다. 결과 파일 세 개는 `.demo-output/<UTC 시각>/` 아래에 생성되며 Git 추적에서 제외됩니다.

직접 출력 위치를 정하려면 다음과 같이 실행합니다.

```bash
./scripts/demo --output-dir /tmp/customs-demo
```

| 확인할 채용 요건 | 데모에서 확인되는 증거 | 현재 한계 |
|---|---|---|
| 입력→처리→출력 | 합성 XLSX 업로드→초안→검증→XML/CSV/XLSX | 합성 데이터이며 실제 고객 문서가 아님 |
| 실패 처리 | 깨진 XLSX 거부·파일 정리, 필드별 검증 오류 | 장애 복구 자동화나 운영 SLA가 아님 |
| 관찰 가능한 상태 | 개인정보를 제외한 JSON 이벤트 로그 | 데모 실행 로그이며 운영 모니터링 시스템이 아님 |
| 자동 테스트 | `backend/tests/test_demo_flow.py`와 `./scripts/check` | 부하·브라우저 E2E 테스트가 아님 |
| 재현성 | `./scripts/bootstrap`, `./scripts/demo`, `./scripts/check` | 로컬 Python/Node 환경 기준 |

## 설정과 데이터 안전

- 실제 비밀값은 `backend/.env`에만 두고 커밋하지 않습니다.
- 업로드는 PDF와 `.xlsx`만 지원하며 기본 한도는 10MB입니다. `MAX_UPLOAD_BYTES`로 조정할 수 있습니다.
- 운영 프런트엔드 주소는 `CORS_ORIGINS`에 쉼표로 구분해 지정합니다.
- `backend/customs.db`, `backend/uploads/`, 실제 관세 문서와 개인정보는 저장소에 넣지 않습니다.
- UNI-PASS 및 uTradeHub 연동 키는 필요한 서비스만 설정합니다.

## 현재 신뢰 경계

GOVCBR830 XML은 회귀 테스트로 구조와 금액 정밀도를 보호하지만, 공개된 관세청 공식 XSD를 확보해 검증하는 단계는 아직 포함하지 않습니다. 실제 전송 전에는 연계 사업자가 제공한 최신 명세와 인증 환경으로 적합성을 확인해야 합니다.

이 데모는 실제 UNI-PASS·관세청·uTradeHub 네트워크 호출을 수행하지 않습니다. 저장소의 선택적 연계 코드는 데모와 포트폴리오 증거 범위 밖이며, 인증 환경 전송 성공이나 운영 배포를 증명하지 않습니다. PDF 파서 구현은 별도로 존재하지만 위 단일 데모 명령은 XLSX 흐름만 재현합니다.

실제 재현 절차, 정상·예상 실패 테스트 결과, 미검증 위험과 보완 우선순위는 [`docs/qa-test-report.md`](<docs/qa-test-report.md>)에 기록합니다.
