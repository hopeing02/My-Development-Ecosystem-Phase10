# AutoKnowledge Lite Android Share Target

이 앱은 Android의 텍스트 공유 메뉴와 클립보드에서 받은 제목·본문·URL을 백엔드의 `POST /v1/share`로 전송합니다.

## 사용 순서

1. Android Studio에서 이 폴더를 엽니다.
2. 앱을 휴대폰에 설치합니다.
3. PC와 휴대폰을 같은 네트워크에 연결합니다.
4. 백엔드를 `--host 0.0.0.0`으로 실행합니다.
5. 앱을 열고 `http://PC의-LAN-IP:8000`을 저장합니다.
6. 저장할 개인 Vault 폴더를 선택합니다.
7. 브라우저 등에서 공유 버튼을 누르고 `AutoKnowledge Lite`를 선택합니다.

## 클립보드로 전체 본문 저장

공유 링크가 대화 일부만 포함하면 채팅이나 문서에서 전체 텍스트를 복사합니다. AutoKnowledge Lite 앱을 열고 저장 폴더를 선택한 뒤 `클립보드 내용 저장`을 누르면 전체 텍스트가 서버로 전송되고 AI 분석·Markdown·Obsidian 저장이 자동 실행됩니다.

클립보드는 버튼을 누른 순간에만 읽으며 백그라운드에서 자동으로 감시하지 않습니다.

저장 폴더는 `00_Inbox`, `10_Life`, `20_Learning`, `30_Interests`, `40_Reference`, `90_Archive` 중에서 선택합니다. 마지막 선택을 기기에 저장해 Android 공유 메뉴에서도 사용하며 선택 정보가 없거나 올바르지 않으면 `00_Inbox`로 되돌아갑니다.

API 키는 Android 앱에 저장하지 않습니다. AI 처리는 백엔드가 담당합니다.

## APK 빌드

PowerShell에서 실행합니다.

```powershell
cd C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite\android
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
.\gradlew.bat assembleDebug
```

생성 파일:

```text
app\build\outputs\apk\debug\app-debug.apk
```

폴더 선택 기능은 앱 버전 `0.2.0`부터 제공됩니다. 기존 앱이 설치되어 있으면 새 APK를 빌드한 뒤 휴대폰에 다시 설치해야 합니다.

단위 테스트:

```powershell
.\gradlew.bat testDebugUnitTest
```