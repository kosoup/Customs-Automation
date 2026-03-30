# 관세 신고 자동화 - 현재 구현 범위

## Context

실전 제출은 나중 단계. 현재는 신고서 작성 자동화 + XML 생성까지만 구현.
테스트 중 실수로 관세청에 실제 신고되는 사고를 방지하기 위해 제출/추적 기능은 제외.

---

## 현재 구현 범위 (3가지)

### 1. 회사(신고인) 설정
한 번 입력해두면 모든 신고서에 자동 채워지는 기본 정보 관리

### 2. UNI-PASS 조회 API 연동 (신고서 작성 보조)
신고서 입력 시 자동 도움:
- **HS코드 검색**: 품목명 입력 → HS코드 자동 추천
- **관세율 조회**: HS코드 입력 시 세율 자동 표시
- **세관장확인대상 조회**: 해당 품목이 확인 대상인지 사전 체크

### 3. GOVCBR830 XML 생성
작성 완료된 신고서 → 관세청 표준 XML 파일로 다운로드

---

## 제외 항목 (나중에)
- 실제 관세청 제출 (EDI/VAN)
- 수출이행내역 추적
- 로그인/인증

---

## UNI-PASS API 인증키

| API | 인증키 |
|-----|--------|
| HS CODE 내비게이션 | `q260c205y132u009k080o020d0` |
| HS 부호검색 | `m250o275s132p039a030c090t0` |
| 세관장확인대상물품조회 | `i280x285t122x079u070y060l0` |
| 관세율기본조회 | `z290u255b132v214x040m000q0` |

Base URL: `https://unipass.customs.go.kr:38010/ext/rest/`

---

## 구현 계획

### Step 1: 서식 파일 복사
- `/mnt/c/Users/user/Downloads/서식/수출신고서/` → `backend/app/services/customs_schema/`

### Step 2: 회사 설정
- `backend/app/models/company_settings.py` (신규)
- `backend/app/api/settings.py` (신규)
- `frontend/src/pages/Settings.tsx` (신규)
- `frontend/src/App.tsx` (수정: /settings 라우트)
- `backend/app/main.py` (수정: router 등록)

저장 항목: 신고인부호, 신고인상호, 사업자등록번호, 수출자주소, 적재항, 신고세관

### Step 3: UNI-PASS 조회 API
- `backend/app/services/unipass_api.py` (신규)
  - `search_hs(keyword)` → HS코드 목록 반환
  - `get_tariff(hscode)` → 관세율 반환
  - `check_customs_confirmation(hscode)` → 세관장확인대상 여부
- `backend/app/api/unipass.py` (신규: `/api/unipass/hs-search`, `/api/unipass/tariff`, `/api/unipass/customs-check`)
- `frontend/src/pages/DeclarationEdit.tsx` (수정: HS코드 검색 자동완성)

### Step 4: GOVCBR830 XML 생성
- `backend/app/services/xml_generator.py` (신규)
  - Declaration + DeclarationItem → GOVCBR830 XML
  - lxml로 XSD 유효성 검사
- `backend/app/api/submissions.py` (수정: `?fmt=xml` 엔드포인트)
- `frontend/src/pages/DeclarationEdit.tsx` (수정: XML 다운로드 버튼)

---

## 수정/신규 파일 목록

| 파일 | 작업 |
|------|------|
| `backend/app/models/company_settings.py` | 신규 |
| `backend/app/api/settings.py` | 신규 |
| `backend/app/services/unipass_api.py` | 신규 |
| `backend/app/api/unipass.py` | 신규 |
| `backend/app/services/xml_generator.py` | 신규 |
| `backend/app/api/submissions.py` | 수정 |
| `backend/app/main.py` | 수정 |
| `backend/requirements.txt` | 수정: lxml 추가 |
| `frontend/src/pages/Settings.tsx` | 신규 |
| `frontend/src/pages/DeclarationEdit.tsx` | 수정 |
| `frontend/src/App.tsx` | 수정 |

---

## 검증 방법

1. 회사 설정 저장 → 새 신고서 생성 시 신고인 정보 자동 채움 확인
2. 신고서 품목 HS코드 검색창 → 품목명 입력 → 드롭다운 결과 확인
3. HS코드 선택 → 관세율 자동 표시 확인
4. 신고서 완성 → XML 다운로드 → XSD 유효성 통과 확인
