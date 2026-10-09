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

## Agent skills

### Issue tracker

Issues live as GitHub Issues (kosoup/Customs-Automation), managed via `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical labels (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — `CONTEXT.md` + `docs/adr/` at repo root (not yet created; skills proceed silently until they exist). See `docs/agents/domain.md`.

# 작업 규칙

## 기본 규칙

- 코드·실험 protocol·결과 문서는 Git에 커밋한다. 기존 결과와 사용자의 변경을 보존한다.
- 사용자의 현재 명시적 지시가 이 파일의 작업 방식보다 우선한다.

## 설계·해석과 실행의 역할 분담

이 저장소의 실험은 두 기존 Codex 세션으로 진행한다.

| 역할 | 현재 담당 세션 | 책임 |
|---|---|---|
| 설계·해석 | 사용자가 설계·해석 담당으로 지정한 세션 | 사용자와 실험 질문·범위·판정 기준을 정하고, 결과를 해석해 다음 진행을 판단한다. |
| 실행 | 사용자가 실행 담당으로 지정한 세션 | 승인된 실험을 구현·실행·검증하고 결과 문서와 commit을 반환한다. |

- 세션 UUID를 우선 사용한다. 제목은 식별 보조이며 모델 이름으로 세션을 대신 선택하지 않는다.
- 실행 담당의 기존 모델·추론 설정은 별도 요청이 없으면 변경하지 않는다.
- 새 세션은 사용자 지정 또는 명시적인 인수인계 없이 위 역할을 자동으로 차지하지 않는다.
- 설계 담당은 기본적으로 실험을 직접 실행하지 않는다. 사용자 지시로 역할을 바꿀 수 있다.
- 실행 담당도 결과의 사실·한계·제안을 문서에 적되, 다음 실험이나 정책 변경을 자동 실행하지 않는다.

## 요청 → 실행 → 결과 반환

1. 설계 담당이 사용자와 합의한 범위를 실행 요청으로 작성해 `codex queue`로 보낸다.
   요청에는 실험 ID, 작업 폴더, 기준 commit, 부모 checkpoint·hash, 실험 질문,
   조건·예산·평가·종료 범위, 결과 문서 경로, 반환 세션 UUID를 포함한다.
2. 실행 담당은 요청과 참조 자료를 읽고 구체적인 protocol을 실행 전에 기록·커밋한다.
   필요한 세부 구현은 기존 검증된 절차를 따른다. 이미 충분히 승인된 범위는 재확인 없이 수행한다.
3. 실행 담당은 학습·평가·검증·문서화까지 완료한다. 결과가 기준 미달이어도 정상적인 실험 결과로 보고한다.
4. 결과 문서와 검증 자료를 커밋한 뒤 요청에 지정된 반환 세션으로 간단한 queue 메시지를 보낸다.
5. 설계 담당은 문서를 읽고 기존 설계 문맥에 따라 해석한다. 결과 메시지 수신 자체는 새 실험의 실행 승인이 아니다.

Queue는 `codex queue --thread <UUID> --message <TEXT>`를 사용한다.
긴 메시지는 `python3`의 `subprocess.run([...])` 등 argv 배열로 전달하여
셸 치환·따옴표 문제를 피한다. 접수 성공과 실험 완료는 별개다.
사용자가 대기를 요청하지 않으면 설계 담당은 접수 확인 후 기다리거나 반복 조회하지 않는다.

반환 메시지는 아래 정보만 간결하게 담고 상세 결과는 문서에 둔다.

- 실험 ID와 완료/중단/검증 실패 상태
- 결과 문서 경로와 결과 commit
- 기존 설계 문맥에 따른 결과 해석·다음 진행 판단 요청

## 규칙 갱신과 현재 세션

- 기존 세션이 이미 알고 있는 역할·queue 흐름은 재주입하지 않는다.
  기존 문맥에 없는 새 규칙이나 행동 변경만 commit과 함께 한 번 알린다.
- 평소에는 실험 요청과 결과만 queue로 주고받는다. 매 요청마다 AGENTS.md 재독이나
  기존 규칙의 재확인을 요구하지 않는다.
- 진행 중인 실험의 수치 계약을 새 규칙 때문에 소급 변경하지 않는다.
- 자주 바뀌는 상태는 이 파일 대신 해당 protocol과 결과 문서에 둔다.
