# 합성 인보이스

두 파일은 테스트·면접 시연용 가상 문서이며 실제 거래처·고객 데이터가 없다.

- `synthetic-invoice.xlsx`: `demo_flow._synthetic_invoice_bytes()`로 생성. 품목 1개, 수량 2, 단가 12.75, 합계 USD 25.50.
- `synthetic-invoice.pdf`: ReportLab 4.4.9로 만든 텍스트·격자표 PDF. 같은 가상 품목을 사용하며 인보이스 번호는 `SYN-PDF-001`. 스캔/OCR 및 임의 양식을 대표하지 않는다.

브라우저 업로드 후 구매자 국가코드 `US`를 보완하고 저장·검증하면 다운로드할 수 있다. 이는 이 앱의 검증 규칙을 통과한다는 의미이며 공식 신고 요건 충족을 뜻하지 않는다.

`tests/test_api.py::test_synthetic_pdf_upload_review_and_export`는 실제 PDF 파서부터 API 출력까지 검증한다. PDF의 `Synthetic Exporter`와 `Synthetic Buyer`는 라벨 제거가 회사명까지 지우는 회귀를 검출한다.
