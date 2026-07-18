# AutoKnowledge Lite Android Share Target

이 앱은 Android의 텍스트 공유 메뉴에서 `AutoKnowledge Lite` 항목을 제공하고 공유된 제목·본문·URL을 백엔드의 `POST /v1/share`로 전송합니다.

## 사용 순서

1. Android Studio에서 이 폴더를 엽니다.
2. 앱을 휴대폰에 설치합니다.
3. PC와 휴대폰을 같은 네트워크에 연결합니다.
4. 백엔드를 `--host 0.0.0.0`으로 실행합니다.
5. 앱을 열고 `http://PC의-LAN-IP:8000`을 저장합니다.
6. 브라우저 등에서 공유 버튼을 누르고 `AutoKnowledge Lite`를 선택합니다.

API 키는 Android 앱에 저장하지 않습니다. AI 처리는 백엔드가 담당합니다.
