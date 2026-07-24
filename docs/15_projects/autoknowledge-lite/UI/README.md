# AutoKnowledge Lite UI

Android 공유 대상 앱은 `apps/autoknowledge-lite/android/`에서 관리한다.

- `ACTION_SEND`와 `text/*` 공유 이벤트 수신
- 공유 제목·원문·첫 번째 HTTP(S) URL 추출
- 저장된 백엔드 주소의 `POST /v1/share`로 전송
- 버튼을 누른 순간에만 클립보드 전체 텍스트 읽기
- API 키는 Android 앱에 저장하지 않음

v0.2.0부터 `00_Inbox`, `10_Life`, `20_Learning`, `30_Interests`, `40_Reference`, `90_Archive` 중 하나를 선택한다. 선택값은 클립보드 저장과 다른 앱 공유에 함께 적용되며 임의 경로 입력은 허용하지 않는다.

v0.2.1부터 PC 브라우저의 `/pc` 화면에서도 같은 고정 목록과 기존 저장 API를 사용한다.
