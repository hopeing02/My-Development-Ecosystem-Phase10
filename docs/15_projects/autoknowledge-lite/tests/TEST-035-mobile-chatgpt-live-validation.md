# TEST-035 모바일 ChatGPT 실제 세션 검증

## 일자와 환경

- 일자: 2026-08-24
- 휴대폰 네트워크: 외부 LTE
- PC 연결: Tailscale
- PC Tailscale IP: `100.75.235.67`
- Android 기기 모델과 OS 버전: 미기록

## 실기기 확인

- AutoKnowledge Lite APK 다운로드 및 앱 연결 성공
- Tailscale 재인증 후 LTE에서 PC API 연결 성공
- ChatGPT 공개 Shared Link 실제 세션 첫 가져오기: 신규 1, 중복 0, 실패 0
- 같은 Shared Link 재가져오기: 신규 0, 중복 1, 실패 0
- MDE Knowledge Viewer에서 동일 Session의 최신본 1건 표시 확인

## 서버 측 확인

- ChatGPT Session ID 유지
- 최신 projection revision: 5
- Message: 14
- Task: 1
- Activity: 13
- 격리 warning:
  - `CHATGPT_MESSAGE_CONTENT_DUPLICATE`
  - `CHATGPT_MESSAGE_CONTENT_MISSING`
- Viewer ChatGPT API: HTTP 200
- Tailscale APK 다운로드 endpoint: HTTP 200

기존에 snapshot 변동으로 생성된 revision은 원본 보존 원칙에 따라 삭제하지 않았다.
중복 판정 보완 후 동일 공통 projection의 두 번째 요청은 신규 revision을 생성하지 않는다.

## 자동화 회귀

- ChatGPT import 대상 테스트: 11 passed
- AutoKnowledge Lite 전체 Python 회귀: 217 passed, 1 skipped
- Ruff: pass
- 변경 파일 Black 검사: pass

## 판정

- 모바일 ChatGPT Shared Link 획득·중복 방지·Viewer 최신 Session 표시: PASS
- 전체 모바일 RC 승인: PENDING

Project Timeline, Knowledge Graph, 두 앱 재실행 후 설정 유지와 기기 정보 기록은 별도
실기기 확인이 필요하다.

