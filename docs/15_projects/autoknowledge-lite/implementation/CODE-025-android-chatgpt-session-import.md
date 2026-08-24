# CODE-025 Android ChatGPT 실제 Session 가져오기

- 작성일: 2026-08-18
- 버전: 0.2.4
- 상태: Complete

## 원인 수정

ChatGPT Import UI가 Knowledge Viewer `:8765`에 있었지만 실제 Import API는
AutoKnowledge-Lite `:8000`에 설치되어 있었다. Viewer origin으로 보낸 요청은
`404 Not Found`였고 프런트엔드는 network fallback 문구를 표시했다.

원본 수집 책임에 맞춰 Android AutoKnowledge-Lite 앱에 실제 Session 가져오기 UI를
추가했다. Viewer는 저장된 Session/Message 조회 역할을 유지한다.

## Android 구현

- 기존 PC 서버 주소와 Control API Key 재사용
- canonical public ChatGPT Shared Link local validation
- 모바일 복사 시 붙는 zero-width 문자와 query/fragment를 제거한 뒤 canonical URL만 전송
- `/api/v1/chatgpt/shared-imports` authenticated JSON 요청
- Android Document Provider에서 Data Export ZIP 선택
- `/api/v1/chatgpt/imports`로 64 KiB chunk streaming upload
- imported, partial, duplicate와 발견/신규/중복/실패/warning 건수 표시
- import ID, raw path, 원문과 Shared Link token을 상태 문구에 표시하지 않음
- 별도 ChatGPT executor로 UI thread와 Codex 작업 분리

## 운영 반영

- Android `versionCode=5`, `versionName=0.2.4`
- AutoKnowledge-Lite package/API version `0.2.4`
- PC uvicorn을 재시작하여 `/v1/status` 0.2.4와 Shared Import 인증 route 확인

## Shared Link 호환성 보완

링크의 HTTPS, `chatgpt.com` host, `/share/<conversation-ID>` 경로 검증은 유지한다.
복사 과정에서 들어오는 zero-width 문자와 query/fragment는 Android와 서버에서
제거하고 `https://chatgpt.com/share/<conversation-ID>`만 실제 요청 및 원본 metadata에
사용한다. 따라서 추적 parameter가 외부 요청이나 archive에 남지 않는다.
