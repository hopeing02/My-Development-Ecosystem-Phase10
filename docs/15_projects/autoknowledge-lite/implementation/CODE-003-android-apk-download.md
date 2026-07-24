# CODE-003 Android APK 직접 다운로드

- 작성일: 2026-07-23
- 버전: 0.2.0
- 상태: Complete

## 구현

- `GET /downloads/autoknowledge-lite.apk`를 추가했다.
- 서버 코드 기준으로 고정된 Android Debug APK 한 파일만 제공한다.
- 요청 경로나 파일명을 입력받지 않는다.
- APK가 없으면 안전한 404 응답을 반환한다.
- 응답 파일명을 `autoknowledge-lite-v0.2.0.apk`로 고정했다.

Vault, 작업 JSON, 로그와 임의 로컬 파일을 제공하는 기능은 추가하지 않았다.
