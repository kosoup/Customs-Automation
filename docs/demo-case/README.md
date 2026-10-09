# 시연 사례 DEMO-001 정답표

모든 회사명·값은 가상이다. PDF 추출과 설정 적용의 경계를 검증하기 위한 자료이며 신고용이 아니다.

## 공통항목

| 항목 | 정답 | 출처 |
|---|---|---|
| 환급신청인 | 2 | demo profile; synthetic assumption |
| 간이자동정액환급여부 | NO | demo profile; synthetic assumption |
| 구매자코드 | DEMO-BUYER-001 | demo profile; not a real customs code |
| 목적국 | US | invoice p1 |
| 구매자 | DEMO PLAY IMPORTS | invoice p1 |
| 제조자 | DEMO TOY WORKS | invoice p1 |
| 거래구분 | 11 | demo profile; synthetic assumption |
| 결제방법 | TT | invoice p1; fixture mapping T/T -> TT |
| 인도조건 | FOB | invoice p1 |
| 통화단위 | USD | invoice p1 |
| 운임비 | 0.00 | invoice p1; invoice currency USD, ecom conversion unverified |
| 기타금액 | 0.00 | invoice p1; invoice currency USD |
| 총금액 | 225.00 | invoice p1 |
| 총중량 | 15.00 | packing list p2 |
| 전체순중량 | 12.00 | packing list p2; not distributed to items |
| 카톤수 | 3 | packing list p2 |

## 품목

12행, 총수량 90, 총금액 USD 225.00. 세부 정답은 `expected.json`에 있다. 규격2·3, FTA협정코드, 품목별 순중량은 공란이다.

## 구분해야 할 결과

- 이미지 PDF는 2페이지이며 추출 가능한 텍스트층이 없다. OCR/시각 인식 입력으로 사용한다.
- PDF만으로 알 수 없는 설정값은 정답 JSON에 가정으로 명시했다. 사용자의 실제 기본값이 아니다.
- 원산지코드는 의미·매핑 미확인으로 검토 대상이다. 그럴듯한 값으로 완성하지 않는다.
- 앱에서 실제 OCR 추출과 정답 대조를 완료했다. 결과는 `evaluation.json`과 `../prototype-demo.md`를 참조한다.
- 이 한 사례로 OCR 정확도·처리시간 개선을 주장하지 않는다.
