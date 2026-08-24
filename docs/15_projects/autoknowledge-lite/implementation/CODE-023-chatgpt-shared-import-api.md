# CODE-023 ChatGPT Shared Link Import API

- 작성일: 2026-08-18
- 상태: Complete

## 구현

- 인증된 `POST /api/v1/chatgpt/shared-imports` 추가
- 기존 Export Import의 `AUTOKNOWLEDGE_CONTROL_API_KEY` 인증 재사용
- 4 KiB 이하 JSON body에서 URL만 직접 검증
- 잘못된 request에 URL token이 validation response로 반사되지 않게 처리
- 기존 Shared Import Service의 imported, partial, duplicate 결과 반환
- fetch, 크기, content type, local Archive 오류를 구분된 HTTP 상태로 변환
- `create_app`에 선택적 Shared Import Service 주입 지점 추가

기존 Export endpoint와 응답 형식은 공통 안전 serializer로 유지하며, raw path와 원문은
두 API 모두 반환하지 않는다.
