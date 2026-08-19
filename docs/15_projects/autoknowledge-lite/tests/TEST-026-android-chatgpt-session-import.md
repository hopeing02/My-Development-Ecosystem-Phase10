# TEST-026 Android ChatGPT 실제 Session 가져오기 검증

- 실행일: 2026-08-19
- 상태: Passed

## Android 단위 테스트 및 APK

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite\android

.\gradlew.bat testDebugUnitTest
# 24 tests passed, 0 failed

.\gradlew.bat assembleDebug
# BUILD SUCCESSFUL

.\gradlew.bat lintDebug
# BUILD SUCCESSFUL
```

- APK: `app/build/outputs/apk/debug/app-debug.apk`
- 크기: 101,765 bytes
- SHA-256: `B5235A81639C692344F7CCD4705F7BD5E7ECC1FAA26E514AA46796A557F875B7`
- 서버 download route와 Tailscale 주소에서 HTTP 200 및
  `autoknowledge-lite-v0.2.4.apk` filename 확인

## Shared Link 호환성 회귀

- canonical `https://chatgpt.com/share/<conversation-ID>` 허용
- 모바일 복사 query/fragment와 zero-width 문자 제거 후 canonical URL 생성
- canonical URL만 PC API와 ChatGPT snapshot request에 전달
- lookalike host, HTTP, credential, 비정상 path 거부
- query와 fragment는 archive metadata와 outbound request에 미보존

## Python 전체 회귀

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest -q
# 199 passed, 1 skipped

uv run ruff check .
# passed
```

## 검증 환경 주의

첫 전체 회귀는 운영 셸에 설정된 `AUTOKNOWLEDGE_CONTROL_API_KEY` 때문에 기존 무인증
관계 API 테스트 1건이 401을 받았다. 테스트 환경에서 운영 key만 비운 뒤 동일 전체
suite를 재실행해 199 passed, 1 skipped를 확인했다. 저장공간 확보 후 `lintDebug`도
재실행해 실제 분석과 HTML report 생성까지 성공했다.
