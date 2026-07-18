# autoknowledge-lite — tests

## 검증 범위

- 상태 API의 서비스명·상태·버전
- 유효한 공유 요청의 `202` 응답과 JSON 저장
- 공백 콘텐츠와 잘못된 출처 URL의 `422` 거부
- 저장된 작업의 분석·상태 변경·결과 영속화
- 존재하지 않는 작업의 `404`
- 비 UUID 작업 ID의 `422`
- OpenAI Responses API 요청·응답 변환
- Anthropic Messages API 요청·응답 변환
- 제공자 선택과 외부 오류 비노출
- 분석 결과의 Markdown 렌더링과 저장
- 미분석 작업의 `409` 거부
- Android 공유 제목·본문·URL 추출 단위 테스트
- 공유 접수 후 분석·Markdown 자동 처리 통합 테스트
- URL 전용 공유의 본문 보강 및 ChatGPT·일반 HTML 추출 테스트
- pytest 임시 디렉터리를 사용한 사용자 데이터 격리
