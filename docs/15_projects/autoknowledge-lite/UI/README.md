# autoknowledge-lite · UI

Android 공유 대상 앱은 `apps/autoknowledge-lite/android/`에 있습니다.

- `ACTION_SEND`와 `text/*` 공유 이벤트 수신
- 공유 제목, 원문, 첫 번째 HTTP(S) URL 추출
- 사용자가 저장한 백엔드 주소의 `POST /v1/share`로 전송
- API 키는 모바일 앱에 저장하지 않고 백엔드에서만 사용
- 사용자 버튼 동작으로 클립보드 전체 텍스트 저장

공유 링크가 스냅샷이거나 본문 접근을 제한하는 경우 전체 내용을 복사한 뒤 앱의 `클립보드 내용 저장`을 사용합니다. 개인정보 보호를 위해 클립보드를 백그라운드에서 읽지 않습니다.

앱 최초 실행 시 PC의 LAN 주소(예: `http://192.168.0.10:8000`)를 저장합니다. 이후 브라우저나 뉴스 앱의 공유 메뉴에서 `AutoKnowledge Lite`를 선택합니다.
