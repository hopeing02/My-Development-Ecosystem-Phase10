# CODE-018 ChatGPT Export Import API

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

Knowledge Viewer가 사용자가 선택한 ChatGPT Data Export ZIP을 로컬 서버에 안전하게
전달할 수 있도록 인증된 streaming API를 제공한다.

## 구현

- `POST /api/v1/chatgpt/imports` endpoint 추가
- multipart 의존성 없이 `application/zip` 또는 `application/octet-stream` body 처리
- Content-Length 사전 검사와 streaming byte 제한 적용
- Git 제외 local data의 staging 디렉터리에만 임시 저장
- 기존 ChatGPT Import Service에 전달한 뒤 staging 제거
- 정상, 부분 성공과 중복 결과를 기존 CLI와 같은 JSON 요약으로 반환
- 응답에서 원문, 업로드 staging과 raw Archive 절대 경로 제외

## 보안

- `AUTOKNOWLEDGE_CONTROL_API_KEY`가 없으면 endpoint 비활성화
- 설정된 Bearer token을 constant-time 비교로 검증
- 원본 파일명은 basename과 안전 문자만 허용
- 잘못된 content type, 크기 초과와 잘못된 ZIP을 저장 pipeline 전에 거부
- Import 성공·실패와 관계없이 검증된 staging 경로만 제거

## 호환성

`create_app`에 선택적 Import Service 주입 지점만 추가했다. 기존 API, ChatGPT Clip,
Markdown, Codex 수집, Knowledge Graph와 Viewer 동작은 변경하지 않았다.
