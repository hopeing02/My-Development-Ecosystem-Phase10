# RELEASE-001 AutoKnowledge Lite v0.2.0

- 릴리스일: 2026-07-23
- 상태: Ready

## 추가

- Android 개인 Vault 고정 폴더 선택 UI
- `target_folder` API 필드와 `00_Inbox` 기본값
- 서버 allowlist와 Vault 외부 경로 차단
- 클립보드·공유 메뉴의 선택값 공통 적용
- 선택된 Markdown 한 파일의 기존 Git 동기화
- Tailscale에서 접근하는 고정 Android APK 다운로드

## 호환성

- 기존 Android 앱과 기존 작업 JSON은 폴더 필드가 없어도 동작한다.
- 기본 저장 폴더는 `00_Inbox`다.
- 기존 `AutoKnowledge/` 문서는 자동 이전하지 않는다.

## 검증

- Python: 54 passed
- Android: unit test 및 Debug APK BUILD SUCCESSFUL
- MDE 회귀: 146 passed
- Ruff: 통과
- 앱 formatter: 17 files formatted

## 설치

휴대폰 Tailscale 연결 후 `http://100.75.235.67:8000/downloads/autoknowledge-lite.apk`에서 받아 기존 앱 위에 설치하고 저장 폴더를 선택한다.
