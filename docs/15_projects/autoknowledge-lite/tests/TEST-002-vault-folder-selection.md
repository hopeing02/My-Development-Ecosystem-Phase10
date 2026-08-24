# TEST-002 Vault 폴더 선택

- 작성일: 2026-07-23
- 상태: Passed

## 결과

| 검증 | 결과 |
|---|---|
| 기본값 `00_Inbox` | 통과 |
| 6개 allowlist | 통과 |
| `../`, 절대경로, 임의 폴더 거부 | 통과 |
| 선택 폴더 Markdown 저장 | 통과 |
| 선택 파일만 Git 동기화 전달 | 통과 |
| 기존 작업 JSON 호환 | 통과 |
| Android 선택 payload·기본값 | 통과 |
| Python 폴더 집중 테스트 | 22 passed |
| Python 전체 앱 테스트 | 52 passed |
| Android 테스트·Debug APK | BUILD SUCCESSFUL |
| MDE 전체 회귀 | 146 passed |
| Ruff | 통과 |
| 앱 formatter | 17 files formatted |
| 로컬·Tailscale 상태 확인 | v0.2.0 응답 |
| 서버 재시작 전후 Vault 보존 | 25/26 files, SHA-256 digest 일치 |
| Git 동기화 설정 보존 | true / main |

## 테스트 격리

Python 저장 테스트는 pytest 임시 Vault와 기록용 Git 동기화 대역을 사용했다. 실제 개인 Vault와 Git 원격에는 테스트 문서를 생성하거나 전송하지 않았다. 운영 서버에는 상태 조회만 수행하고 실제 저장 요청은 보내지 않았다.

## 발견 및 해결

첫 전체 테스트에서 API가 선택 폴더를 작업 레코드에 전달하지 않아 `00_Inbox`로 되돌아가는 결함 1개를 발견했다. `ShareRecord` 생성 지점에 `request.target_folder` 전달을 추가한 뒤 집중 22개와 전체 52개 테스트가 통과했다.

앱 Python으로 MDE 루트에서 pytest를 실행한 첫 명령은 루트 테스트까지 수집해 앱 환경에 없는 PyYAML 오류가 발생했다. 작업 폴더를 앱 루트로 고쳐 앱 테스트와 MDE 회귀를 각각 올바른 환경에서 분리 실행했다.