# KCS 전자상거래 수출신고 백엔드

> 관세청(Korea Customs Service) **전자상거래 수출신고서(GOVCBRDJP)** 처리 서버  
> WCO `KCS_DeclarationOfEXP_DJPSchemaModule:1:0` 스키마 기반 FastAPI 서버

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [아키텍처 구조도](#2-아키텍처-구조도)
3. [프로젝트 파일 구조](#3-프로젝트-파일-구조)
4. [신고 처리 흐름](#4-신고-처리-흐름)
5. [API 엔드포인트](#5-api-엔드포인트)
6. [데이터 모델 구조](#6-데이터-모델-구조)
7. [환경 설정](#7-환경-설정)
8. [설치 및 실행](#8-설치-및-실행)
9. [테스트](#9-테스트)
10. [실전 연동 체크리스트](#10-실전-연동-체크리스트)
11. [공인인증서 서명 구조](#11-공인인증서-서명-구조)
12. [오류 코드](#12-오류-코드)

---

## 1. 시스템 개요

```
목적      전자상거래 수출신고서를 작성·검증·서명하여 관세청 UNI-PASS로 전송
스키마    KCS_DeclarationOfEXP_DJPSchemaModule v1.0 (WCO 표준)
언어      Python 3.12 (FastAPI) + Java 17 (서명 전용 마이크로서비스)
모드      MOCK_MODE=true  → UNI-PASS 미연동 테스트 가능
          MOCK_MODE=false → 실제 관세청 전자통관망 전송
```

---

## 2. 아키텍처 구조도

### 전체 시스템 구성

```
┌─────────────────────────────────────────────────────────────────┐
│                         클라이언트                               │
│                                                                 │
│   ┌─────────────────────────┐    ┌──────────────────────────┐  │
│   │    웹 양식 (HTML/JS)     │    │   외부 시스템 / API 호출  │  │
│   │  kcs_export_declaration  │    │   (ERP, 쇼핑몰 등)       │  │
│   └────────────┬────────────┘    └────────────┬─────────────┘  │
└────────────────┼─────────────────────────────┼─────────────────┘
                 │ JSON                         │ JSON
                 ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI 서버 (port 8000)                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   API Layer (라우터)                      │  │
│  │                                                          │  │
│  │  POST /api/declaration/xml      XML 미리보기             │  │
│  │  POST /api/declaration/validate XSD 검증                 │  │
│  │  POST /api/declaration/sign     전자서명                  │  │
│  │  POST /api/declaration/submit   UNI-PASS 전송            │  │
│  │  POST /api/declaration/full     일괄 처리                 │  │
│  │  GET  /api/declaration/health   상태 확인                 │  │
│  └──────────────┬───────────────────────────────────────────┘  │
│                 │                                               │
│  ┌──────────────▼───────────────────────────────────────────┐  │
│  │                  Service Layer (서비스)                   │  │
│  │                                                          │  │
│  │  ┌─────────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐  │  │
│  │  │ xml_builder │ │validator │ │  signer   │ │unipass │  │  │
│  │  │             │ │          │ │  (브릿지) │ │_client │  │  │
│  │  │ Pydantic    │ │ XSD      │ │           │ │        │  │  │
│  │  │ → WCO XML   │ │ 스키마   │ │ Java 서비 │ │ HTTP   │  │  │
│  │  │             │ │ 검증     │ │ 스 호출   │ │ 전송   │  │  │
│  │  └─────────────┘ └──────────┘ └─────┬─────┘ └───┬────┘  │  │
│  └────────────────────────────────────┼────────────┼────────┘  │
│                                       │            │            │
└───────────────────────────────────────┼────────────┼────────────┘
                                        │            │
                    ┌───────────────────┘            │
                    ▼                                ▼
     ┌──────────────────────────┐     ┌─────────────────────────┐
     │  Java 서명 서비스         │     │  관세청 UNI-PASS         │
     │  (port 8081)             │     │                         │
     │                          │     │  [TEST]                 │
     │  Spring Boot             │     │  unipasstest.customs    │
     │  XmlSignerApplication    │     │  .go.kr                 │
     │                          │     │                         │
     │  - PKCS#12 로드          │     │  [PROD]                 │
     │  - RSA 개인키 추출       │     │  unipass.customs.go.kr  │
     │  - XML-DSig 서명         │     │                         │
     │  - 서명된 XML 반환       │     │  → 수리/반려/보정        │
     └──────────────────────────┘     └─────────────────────────┘
```

### Mock 모드 vs 실전 모드

```
[MOCK_MODE = true] ─────────────────────────────────────────────
                                                                 
  클라이언트 ──→ FastAPI ──→ xml_builder ──→ validator          
                                │                               
                                └──→ Mock 응답 생성              
                                     (95% 수리 / 5% 반려)        
                                     신고번호 자동 생성          
                                                                 
[MOCK_MODE = false] ────────────────────────────────────────────
                                                                 
  클라이언트 ──→ FastAPI ──→ xml_builder ──→ validator           
                                │                               
                                ├──→ Java 서명 서비스 (8081)     
                                │    └── 서명된 XML              
                                │                               
                                └──→ UNI-PASS HTTPS POST        
                                     └── 수리/반려 응답 파싱     
```

---

## 3. 프로젝트 파일 구조

```
kcs_backend/
│
├── app/                              ← FastAPI 애플리케이션
│   ├── main.py                       ← 앱 진입점, 라이프사이클, CORS
│   │
│   ├── core/
│   │   └── config.py                 ← 환경변수 설정 (Pydantic Settings)
│   │
│   ├── models/
│   │   └── declaration.py            ← Pydantic 데이터 모델
│   │       ├── DeclarationRequest    ← 신고서 전체 (메인 입력)
│   │       ├── ExporterModel         ← 수출화주
│   │       ├── DeclarantModel        ← 신고인
│   │       ├── AgentModel            ← 수출대행자
│   │       ├── SubmitterModel        ← 제출자
│   │       ├── GovernmentAgencyGoodsItemModel  ← 품목 란
│   │       ├── DetailedCommodityModel          ← 규격 명세
│   │       ├── ManufacturerModel     ← 제조자
│   │       ├── DrawBackModel         ← 환급
│   │       ├── DeclarationResponse   ← API 응답
│   │       ├── SignRequest / SignResponse       ← 서명 요청/응답
│   │       └── ValidationErrorDetail ← 검증 오류 상세
│   │
│   ├── api/
│   │   └── declaration.py            ← 라우터 (6개 엔드포인트)
│   │
│   └── services/
│       ├── xml_builder.py            ← Pydantic → lxml WCO XML 변환
│       ├── validator.py              ← XSD 스키마 검증 (폴백 포함)
│       ├── unipass_client.py         ← UNI-PASS HTTPS 전송 + Mock
│       └── signer.py                 ← Java 서명 서비스 브릿지
│
├── java_signer/                      ← Java 전자서명 마이크로서비스
│   ├── pom.xml                       ← Maven 빌드 설정 (Spring Boot 3.2)
│   └── src/main/java/kr/kcs/signer/
│       └── XmlSignerApplication.java ← XML-DSig RSA-SHA256 서명
│
├── schemas/                          ← XSD 스키마 파일 배치 위치
│   └── (KCS_DeclarationOfEXP_DJPSchemaModule_1.0_standard.xsd 배치)
│
├── tests/
│   └── test_declaration.py           ← pytest 통합 테스트 12개
│
├── requirements.txt                  ← Python 의존성
├── pyproject.toml                    ← pytest 설정
└── .env.example                      ← 환경변수 템플릿
```

---

## 4. 신고 처리 흐름

### 전체 흐름 (POST /api/declaration/full)

```
① 클라이언트 JSON 전송
   │
   ▼
② Pydantic 모델 검증
   ├── 사업자등록번호 형식 (8~13자리 숫자)
   ├── HS Code 형식 (6~10자리 숫자)
   ├── 란번호 연속성 검사 (1, 2, 3 ... 순서)
   ├── 란 수 범위 (1~999)
   └── 필수 필드 존재 여부
          │
          ▼ 검증 실패 시 422 반환
③ XML 생성 (xml_builder.py)
   ├── lxml etree로 WCO 네임스페이스 XML 구성
   ├── wco: 접두사 → 공통 필드
   ├── kcs: 접두사 → 한국 관세청 확장 필드
   └── 최대 999개 GovernmentAgencyGoodsItem 반복 생성
          │
          ▼
④ XSD 스키마 검증 (validator.py)
   ├── schemas/ 폴더에 실제 XSD 있음 → 엄격한 스키마 검증
   └── XSD 없음 → 수동 필수 필드 검사 후 전송 진행
          │
          ▼ 검증 실패 시 오류 목록 반환
⑤ 전자서명 (signer.py) [선택]
   ├── keystore_path 파라미터 제공 시 실행
   ├── Java 서비스(8081) 가동 중 → Java XML-DSig 서명
   ├── Java 서비스 미가동 → Python RSA 폴백 시도
   └── MOCK_MODE → 서명 생략
          │
          ▼
⑥ UNI-PASS 전송 (unipass_client.py)
   ├── MOCK_MODE=true  → Mock 응답 (95% 수리)
   └── MOCK_MODE=false → HTTPS POST → 관세청 서버
          │
          ▼
⑦ 응답 파싱 및 반환
   ├── ResultCode=0000 → success=true, 신고번호 반환
   └── 그 외 → success=false, 오류 메시지 반환
```

---

## 5. API 엔드포인트

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| `POST` | `/api/declaration/xml` | XML 미리보기 (다운로드) | `application/xml` |
| `POST` | `/api/declaration/validate` | XSD 유효성 검증 | `{valid, errors}` |
| `POST` | `/api/declaration/sign` | 공인인증서 서명 | `{success, signedXml}` |
| `POST` | `/api/declaration/submit` | UNI-PASS 전송 | `DeclarationResponse` |
| `POST` | `/api/declaration/full` | 전체 일괄 처리 | `DeclarationResponse` |
| `GET`  | `/api/declaration/health` | 서비스 상태 확인 | `{status, mock_mode, ...}` |
| `GET`  | `/docs` | Swagger UI | HTML |
| `GET`  | `/redoc` | ReDoc 문서 | HTML |

### 요청 예시 (curl)

```bash
# XML 미리보기
curl -X POST http://localhost:8000/api/declaration/xml \
  -H "Content-Type: application/json" \
  -d @sample_request.json \
  -o declaration.xml

# 유효성 검증
curl -X POST http://localhost:8000/api/declaration/validate \
  -H "Content-Type: application/json" \
  -d @sample_request.json | jq .

# 전체 처리 (서명 없이, Mock 모드)
curl -X POST http://localhost:8000/api/declaration/full \
  -H "Content-Type: application/json" \
  -d @sample_request.json | jq .

# 전체 처리 (공인인증서 서명 포함)
curl -X POST \
  "http://localhost:8000/api/declaration/full?cert_alias=my_cert&keystore_path=/path/to/cert.p12&keystore_password=1234" \
  -H "Content-Type: application/json" \
  -d @sample_request.json | jq .
```

---

## 6. 데이터 모델 구조

### DeclarationRequest 요약

```
DeclarationRequest
│
├── [기본정보]
│   ├── declaration_office_id   신고세관/과 코드    ex) "01001"
│   ├── declaration_id          전자상거래수출신고번호
│   ├── issue_date              신고일자 YYYYMMDD   ex) "20241108"
│   ├── invoice_amount          총신고가격(FOB)
│   ├── process_type_code       신고구분  01/02/03
│   └── transport_type_code     해상(01)/항공(02)
│
├── [주문/결제]
│   ├── order_id                주문번호 *필수
│   ├── delivery_id             배송번호
│   ├── currency_id             통화코드  ex) "KRW"
│   ├── condition_code          인도조건  ex) "DAP"
│   └── settlement_code         결제방법  01~04
│
├── [당사자]
│   ├── exporter                수출화주 (ExporterModel)
│   │   ├── biz_number          사업자등록번호 *필수
│   │   ├── customs_code        통관고유부호(380)
│   │   ├── name                상호 *필수
│   │   └── address             AddressModel
│   │
│   ├── declarant               신고인 (DeclarantModel) *필수
│   ├── submitter               제출자 (SubmitterModel) *필수
│   ├── agent                   수출대행자 (AgentModel) 선택
│   └── buyer                   구매자 (BuyerModel) 선택
│
└── [품목 란] goods_items  List[GovernmentAgencyGoodsItemModel]  1~999개
    └── GovernmentAgencyGoodsItemModel
        ├── sequence_numeric    란번호 (1부터 연속)
        ├── hs_code             세번부호 10자리 *필수
        ├── description         품명 *필수
        ├── customs_value_amount 신고금액 *필수
        ├── count_quantity      수량
        ├── net_weight          순중량(kg)
        ├── draw_back           DrawBackModel (환급)
        ├── manufacturer        ManufacturerModel (제조자)
        └── detailed_commodities  List[DetailedCommodityModel]  0~99개
            └── DetailedCommodityModel
                ├── sequence_numeric  규격번호
                ├── cargo_description 모델/규격
                ├── count_quantity    수량
                ├── unit_price_amount 단가
                └── value_amount      금액
```

---

## 7. 환경 설정

`.env.example`을 복사하여 `.env`로 사용합니다.

```bash
cp .env.example .env
```

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `MOCK_MODE` | `true` | `true`: 실제 전송 없이 테스트, `false`: 실전 전송 |
| `UNIPASS_ENV` | `test` | `test` / `production` |
| `UNIPASS_AUTH_KEY` | `` | 관세청 발급 인증키 (실전 시 필수) |
| `SSL_VERIFY` | `true` | TLS 인증서 검증 여부 |
| `JAVA_SIGNER_PORT` | `8081` | Java 서명 서비스 포트 |
| `AUTO_START_JAVA_SIGNER` | `false` | FastAPI 시작 시 Java 서비스 자동 시작 |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## 8. 설치 및 실행

### Python (FastAPI 서버)

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env

# 3. 서버 시작
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# → http://localhost:8000/docs 에서 Swagger UI 확인
```

### Java (서명 서비스) — 공인인증서 서명 필요 시

```bash
cd java_signer

# 빌드
mvn clean package -DskipTests

# 실행
java -jar target/kcs-signer.jar --server.port=8081
```

### Docker Compose (권장)

```yaml
# docker-compose.yml 예시
version: "3.9"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MOCK_MODE=false
      - UNIPASS_ENV=test
      - JAVA_SIGNER_PORT=8081
    depends_on:
      - signer

  signer:
    build: ./java_signer
    ports:
      - "8081:8081"
```

---

## 9. 테스트

```bash
# 전체 테스트 실행
python -m pytest tests/ -v

# 특정 테스트만
python -m pytest tests/test_declaration.py::test_api_full_flow -v

# 커버리지 포함
python -m pytest tests/ --cov=app --cov-report=term-missing
```

### 테스트 목록 (12개)

| 테스트명 | 분류 | 설명 |
|----------|------|------|
| `test_build_xml_success` | 단위 | XML 생성 성공 |
| `test_build_xml_contains_hs_code` | 단위 | HS Code XML 포함 여부 |
| `test_validate_xml_valid` | 단위 | 유효 XML 검증 통과 |
| `test_validate_xml_missing_field` | 단위 | 필수 필드 누락 감지 |
| `test_pydantic_invalid_hs_code` | 단위 | HS Code 형식 오류 |
| `test_pydantic_invalid_sequence` | 단위 | 란번호 비연속 오류 |
| `test_pydantic_too_many_goods_items` | 단위 | 1000란 초과 오류 |
| `test_api_preview_xml` | 통합 | XML 다운로드 API |
| `test_api_validate_success` | 통합 | 검증 API 성공 |
| `test_api_submit_mock` | 통합 | Mock 전송 API |
| `test_api_full_flow` | 통합 | 전체 흐름 일괄 |
| `test_api_health` | 통합 | 헬스체크 API |

---

## 10. 실전 연동 체크리스트

```
사전 준비
  □ 관세청 UNI-PASS 이용 신청 (portal.customs.go.kr)
  □ 통관고유부호(380) 등록 완료
  □ 신고인 부호 발급 완료
  □ 공인인증서 발급 (관세청 등록용 범용 또는 전용)
  □ UNI-PASS 테스트 계정 발급
  □ XSD 스키마 파일 수령 → schemas/ 폴더에 배치

개발 환경 (MOCK → TEST)
  □ .env: MOCK_MODE=false, UNIPASS_ENV=test
  □ Java 서명 서비스 빌드 및 실행
  □ 공인인증서 P12 파일 경로 확인
  □ /api/declaration/full 테스트 전송 성공 확인
  □ 신고번호 수신 확인

운영 환경 (TEST → PRODUCTION)
  □ .env: UNIPASS_ENV=production
  □ UNIPASS_AUTH_KEY 설정
  □ SSL_VERIFY=true 유지
  □ 로그 모니터링 구성
```

---

## 11. 공인인증서 서명 구조

```
한국 공인인증서 파일 구조
┌─────────────────────────────────────────────────┐
│  PKCS#12 (.p12 / .pfx)                          │
│                                                 │
│  ├── 개인키 (Private Key)                       │
│  │   └── SEED 또는 ARIA 암호화 (한국 표준)       │
│  │       ※ Python cryptography 라이브러리 미지원 │
│  │       ※ Java BouncyCastle 라이브러리 필요    │
│  │                                             │
│  └── 인증서 (X.509 Certificate)                │
│      ├── 공개키 (Public Key, RSA)               │
│      ├── 발급기관 (KISA / YESSIGN / KOSCOM 등)  │
│      └── 유효기간                               │
└─────────────────────────────────────────────────┘

서명 흐름 (Java XmlSignerApplication)
  1. KeyStore.getInstance("PKCS12").load(p12파일)
  2. keyStore.getKey(alias, password) → PrivateKey
  3. XMLSignatureFactory.getInstance("DOM")
  4. Reference 생성 (ENVELOPED Transform, SHA-256 Digest)
  5. SignedInfo 생성 (C14N + RSA-SHA256)
  6. DOMSignContext(privateKey, xmlRoot).sign()
  7. 서명된 XML 문서 반환
```

---

## 12. 오류 코드

### FastAPI 응답 코드

| HTTP | 상황 |
|------|------|
| `200` | 정상 처리 |
| `422` | Pydantic 검증 실패 또는 XSD 검증 실패 |
| `500` | 서버 내부 오류 (XML 생성 실패, Java 서비스 오류 등) |

### UNI-PASS 응답 코드

| ResultCode | 의미 |
|------------|------|
| `0000` | 정상 수리 |
| `E001` | 세번부호 오류 |
| `E002` | 신고인 부호 미등록 |
| `E003` | 수출화주 정보 불일치 |
| 기타 | 관세청 UNI-PASS 오류 코드표 참조 |

---

## 라이선스 및 문의

본 프로젝트는 내부 개발용 참고 코드입니다.  
실제 신고 시 관세사 또는 관세청 UNI-PASS 고객센터(1544-1285)에 문의하세요.
