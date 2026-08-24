# TEST-035 모바일 ChatGPT 실제 세션 검증

## 일자와 환경

- 일자: 2026-08-24
- 휴대폰 네트워크: 외부 LTE
- PC 연결: Tailscale
- PC Tailscale IP: `100.75.235.67`
- Android 기기 모델: `LGE LM-Q815L`
- Android OS 버전: 미확인
- 실기기 설치·검증일: 2026-08-24

## 실기기 확인

- AutoKnowledge Lite APK 다운로드 및 앱 연결 성공
- Tailscale 재인증 후 LTE에서 PC API 연결 성공
- ChatGPT 공개 Shared Link 실제 세션 첫 가져오기: 신규 1, 중복 0, 실패 0
- 같은 Shared Link 재가져오기: 신규 0, 중복 1, 실패 0
- MDE Knowledge Viewer에서 동일 Session의 최신본 1건 표시 확인
- Project Timeline 표시와 ChatGPT/Codex 원본 이동 확인
- ChatGPT Session/Message/Task/Activity Knowledge Graph 표시 확인
- AutoKnowledge Lite와 Viewer 종료·재실행 후 서버 설정과 Session 조회 유지 확인
- MDE Knowledge Viewer Android APK 설치·연결·재실행 확인

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
- Project Timeline: ChatGPT 48개 + Codex Capture 1개
- 선택 ChatGPT Session Graph: node 29개, edge 41개, truncated false
- 통합 Graph: node 81개, edge 128개, warning 0

기존에 snapshot 변동으로 생성된 revision은 원본 보존 원칙에 따라 삭제하지 않았다.
중복 판정 보완 후 동일 공통 projection의 두 번째 요청은 신규 revision을 생성하지 않는다.

## 자동화 회귀

- ChatGPT import 대상 테스트: 11 passed
- AutoKnowledge Lite 전체 Python 회귀: 217 passed, 1 skipped
- Ruff: pass
- 변경 파일 Black 검사: pass

## 판정

- 모바일 ChatGPT Shared Link 획득·중복 방지·Viewer 최신 Session 표시: PASS
- Project Timeline과 Knowledge Graph: PASS
- 앱 종료·재실행 후 설정 유지: PASS
- MDE Knowledge Viewer Android APK 설치·실행: PASS
- 전체 모바일 RC 승인: PASS

Android 상세 버전은 확인되지 않아 추정하지 않고 미확인으로 기록했다. 기능 승인에는
휴대폰 모델 `LGE LM-Q815L`에서 확인한 실제 설치·연결·재실행 결과를 사용했다.
