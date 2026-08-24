# TEST-003 Android APK 직접 다운로드

- 작성일: 2026-07-23
- 상태: Passed

## 결과

| 검증 | 결과 |
|---|---|
| 설정된 APK 응답 | 200 |
| APK가 없을 때 | 404 |
| Content-Type | `application/vnd.android.package-archive` |
| 다운로드 파일명 | `autoknowledge-lite-v0.2.0.apk` |
| 전체 앱 테스트 | 54 passed |
| Ruff | 통과 |
| Tailscale 실제 GET | 200 |
| 다운로드 크기 | 16,021 bytes |
| 서버 원본과 SHA-256 | 일치 |

실제 검증은 다운로드만 수행했다. Vault 저장 API와 Git 동기화는 실행하지 않았다.
