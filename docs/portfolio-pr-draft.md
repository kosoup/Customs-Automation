# 포트폴리오 PR 범위와 검증

## 변경 내용

이미지 선적서류에서 신고서 공통사항과 품목 정보를 옮겨 적는 반복 작업을 줄이는 로컬 OCR 초안 작성 화면을 추가한다. 문서 근거와 기본 설정을 구분하고 누락을 검토·수정한 뒤 JSON과 12열 TSV로 내보낸다.

기존 인보이스 흐름도 함께 보완한다. 검증 실패·미저장 초안의 출력을 차단하고, 파일 작업으로 실제 제출 상태가 바뀌지 않게 한다. 제출·수리·반려 상태는 재검증으로 되돌리지 않는다. 합성 파일과 임시 DB로 재현하는 데모를 제공한다.

## 검증

- 새 의존성 환경에서 백엔드 테스트 38개, 프런트엔드 lint·빌드 통과.
- 브라우저에서 OCR 초안 생성·누락값 수정·원문 확인·JSON 저장·12열 복사 확인.
- 합성 이미지 PDF 4건, 문서별 3회 실제 로컬 OCR. 최초 매핑 실패와 개선 후 결과를 별도 보존.
- 새 소스 복사본에서 bootstrap/check/setup-ocr와 DEMO-004 정답 대조 통과. 같은 Mac이며 새 OS 검증은 아님.
- 실제 신고·ecom 연계·현업 시간 절감은 미검증. Ubuntu CI에서 macOS OCR을 실행하지 않음. 빌드 번들 크기 경고가 남음.

## 게시 상태

원격 main과 로컬 기준 커밋 a13e78d가 일치한다. 저장소 조회는 가능하지만 GitHub 연결 앱의 blob 생성이 HTTP 403 Resource not accessible by integration으로 거부됐다. 기존 gh CLI 토큰도 만료돼 원격 PR과 CI 실행은 완료하지 못했다.

검토한 변경을 로컬 별도 브랜치 `portfolio/ocr-draft-evaluation`에 보존한다. 원래 워킹트리와 인덱스는 유지한다. 실제 문서·DB·업로드·환경 파일은 포함하지 않고 합성 샘플만 포함한다.

본인 터미널에서 `gh auth login -h github.com`으로 인증을 복구한 뒤 다음 순서로 게시할 수 있다. 토큰을 채팅에 전달할 필요는 없다.

```bash
git push -u origin portfolio/ocr-draft-evaluation
gh pr create --draft --base main --head portfolio/ocr-draft-evaluation --title "feat: add local OCR draft preparation and portfolio evidence" --body-file docs/portfolio-pr-draft.md
```

PR 생성 뒤 GitHub Actions 결과를 확인한다. 아직 원격에 업로드됐거나 CI가 통과했다고 표현하지 않는다.
