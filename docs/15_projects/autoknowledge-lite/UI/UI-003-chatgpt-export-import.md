# UI-003 ChatGPT 세션 가져오기

- 버전: 0.2.2
- 상태: Complete

## 진입

Knowledge Viewer 상단의 `ChatGPT` 메뉴를 선택한다.

## 구성

- ChatGPT Data Export ZIP 선택
- Control API Key 입력
- `로컬로 가져오기` 실행
- 선택적으로 canonical ChatGPT Shared Link 1건 입력
- `공유 링크 가져오기` 명시적 실행
- 발견, 신규 투영, 중복, 격리된 실패 세션 수 표시
- 손상 입력 warning code와 해당 session ID 표시

## 상태

- `imported`: 새 세션 투영 완료
- `partial`: 정상 세션은 투영하고 손상 세션은 격리
- `duplicate`: 동일 export와 세션을 다시 생성하지 않음

Control API Key는 현재 화면 memory에서만 사용한다. Viewer는 ChatGPT account나 최근
세션 목록에 접속하지 않는다. Data Export ZIP은 local upload하며, Shared Link는 사용자가
버튼을 누른 경우에만 local server가 해당 공개 snapshot 1건을 조회한다.
