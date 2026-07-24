# CODE-002 Vault 폴더 선택

- 작성일: 2026-07-23
- 버전: 0.2.0
- 상태: Complete

## 구현

- 서버 모델에 `target_folder` allowlist와 `00_Inbox` 기본값을 추가했다.
- 기존 클라이언트 요청과 기존 작업 JSON에서 폴더 필드가 없으면 `00_Inbox`를 사용한다.
- Vault 저장소는 선택 폴더를 Vault 루트 아래에서 다시 검증하고 심볼릭 링크를 포함한 외부 경로 이탈을 차단한다.
- Android 앱에 6개 고정 폴더 Spinner와 선택값 보존 기능을 추가했다.
- 클립보드 저장과 다른 앱 공유 모두 마지막 선택 폴더를 `target_folder`로 전송한다.
- 선택 폴더에 생성된 Markdown 한 파일만 기존 Git 동기화에 전달한다.
- Python·Android 버전을 0.2.0으로 올렸다.

## 데이터 보호

- 기존 `AutoKnowledge/` 문서를 이동하거나 수정하지 않았다.
- 실제 개인 Vault를 사용하는 쓰기 테스트를 실행하지 않았다.
- 임의 경로 입력 UI를 제공하지 않고 서버에서 allowlist 밖의 값을 `422`로 거부한다.

## 관련 문서

- `../SDS/SDS-002-vault-folder-selection.md`
- `../API/API-001-vault-folder-selection.md`
- `../UI/UI-001-vault-folder-selection.md`
- `../tests/TEST-002-vault-folder-selection.md`
- `../usage/GUIDE-002-vault-folder-selection.md`
