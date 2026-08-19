# AutoKnowledge Lite Android Share Target

이 앱은 Android의 텍스트 공유 메뉴와 클립보드에서 받은 제목·본문·URL을 백엔드의 `POST /v1/share`로 전송합니다.

## 사용 순서

1. Android Studio에서 이 폴더를 엽니다.
2. 앱을 휴대폰에 설치합니다.
3. PC와 휴대폰을 같은 네트워크에 연결합니다.
4. 백엔드를 `--host 0.0.0.0`으로 실행합니다.
5. 앱을 열고 `http://PC의-LAN-IP:8000`을 저장합니다.
6. 저장할 개인 Vault 폴더를 선택합니다.
7. 클립보드 저장이라면 상위 주제 문서를 검색해 필요할 때 선택합니다.
8. 브라우저 등에서 공유 버튼을 누르고 `AutoKnowledge Lite`를 선택합니다.

## ChatGPT 실제 세션 가져오기

앱의 `ChatGPT 실제 세션 가져오기` 영역은 PC AutoKnowledge-Lite 서버의 수집 API를
직접 사용합니다. Knowledge Viewer는 가져온 결과를 조회하는 용도입니다.

- 권장: `ChatGPT Data Export ZIP 선택`에서 계정 export ZIP을 고른 뒤
  `선택한 ZIP 가져오기`를 누릅니다.
- 보조: 사용자가 만든 canonical
  `https://chatgpt.com/share/<conversation-ID>`를 입력하고
  `공유 링크 가져오기`를 누릅니다.

두 방식 모두 위 Codex 영역의 `모바일 제어 API 키`를 사용합니다. Shared Link는 최근
세션 목록이 아니라 공개 snapshot 1건만 가져옵니다. ZIP은 휴대폰에 별도 복제하지 않고
Android ContentResolver에서 PC 서버로 streaming 전송합니다. 결과에는 발견, 신규,
중복, 실패와 warning 건수만 표시합니다.

PC 서버 주소는 Viewer의 `:8765`가 아니라 AutoKnowledge-Lite의 `:8000`이어야 합니다.
서버 코드 갱신 후에는 실행 중인 uvicorn을 재시작해야 새 API route가 활성화됩니다.

## 클립보드로 전체 본문 저장

공유 링크가 대화 일부만 포함하면 채팅이나 문서에서 전체 텍스트를 복사합니다. AutoKnowledge Lite 앱을 열고 저장 폴더를 선택한 뒤 `클립보드 내용 저장`을 누르면 전체 텍스트가 서버로 전송되고 AI 분석·Markdown·Obsidian 저장이 자동 실행됩니다.

수동 저장은 버튼을 누른 순간의 클립보드를 읽습니다. `저장 출처`와
`AI 대화 클립보드 자동 저장`을 설정하면 Android 9에서는 포그라운드 서비스가
클립보드 변경을 감지해 같은 저장 파이프라인으로 전송합니다. 서버가 꺼져 있으면
본문을 Android Keystore 기반 AES-GCM으로 암호화해 로컬 대기열에 보관합니다.

## 자동 클립보드 저장

- 출처는 `ChatGPT`, `Codex`, `일반 문서` 중 직접 선택합니다.
- 정규화된 본문의 SHA-256 해시로 최근 100건과 대기 항목의 중복을 검사합니다.
- API 키, 인증 헤더, 비밀번호 값, 개인 키, OTP, 주민등록번호와 카드번호 형태는
  서버로 보내지 않습니다.
- 알림에서 일시 중지, 다시 시작, 자동 저장 끄기를 수행할 수 있습니다.
- 앱 실행과 네트워크 복구 시 대기 항목을 최대 5회 자동 재전송하며, 실패 항목은
  삭제하지 않고 `다시 전송` 버튼으로 재시도할 수 있습니다.

Android 10 이상에서는 운영체제가 백그라운드 앱의 클립보드 접근을 제한합니다.
실제로 텍스트를 읽은 경우에만 저장하며, 앱이 다시 포그라운드로 오면 현재
클립보드를 한 번 확인합니다. 접근성 서비스나 OCR은 사용하지 않으며 수동 저장
버튼을 항상 대체 수단으로 유지합니다.

`상위 주제 검색`에서 기존 문서를 선택하면 해당 문서가 새 문서를 참조하도록
원본 Markdown에 링크를 추가합니다. 선택하지 않으면 직전에 Android 클립보드로
저장하고 색인까지 완료된 문서를 상위 주제로 자동 연결합니다. 첫 저장처럼 이전
문서가 없으면 상위 주제 없이 저장합니다. 공유 메뉴에서 바로 보내는 내용은 자동
상위 주제 연결 대상에서 제외됩니다.

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

ChatGPT 실제 세션 가져오기는 앱 버전 `0.2.4`부터 제공됩니다. 기존 앱이 설치되어
있으면 새 APK를 빌드한 뒤 휴대폰에 다시 설치해야 합니다.

단위 테스트:

```powershell
.\gradlew.bat testDebugUnitTest
```
