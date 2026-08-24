# AutoKnowledge Lite

Android 공유 메뉴와 클립보드로 받은 콘텐츠를 로컬 API에서 접수하고 Markdown으로 만들어 개인 Obsidian Vault에 저장하는 MDE 프로젝트입니다.

Android 앱에서 `00_Inbox`, `10_Life`, `20_Learning`, `30_Interests`, `40_Reference`, `90_Archive` 중 저장 폴더를 선택할 수 있습니다. 선택값이 없으면 `00_Inbox`를 사용하며 서버는 이 목록 밖의 경로를 거부합니다.

## 공식 위치

- 코드와 테스트: 이 폴더
- 프로젝트 문서: [`docs/15_projects/autoknowledge-lite/`](../../docs/15_projects/autoknowledge-lite/)
- 개인 지식: `AUTOKNOWLEDGE_VAULT_DIR`로 지정한 개인 Vault
- 작업 JSON과 로그: Git에서 제외되는 로컬 `data/`, `logs/`

프로젝트 설계·구현·테스트·사용법은 개인 Vault에 저장하지 않습니다.

## 설치와 실행

```powershell
uv sync --project apps/autoknowledge-lite
uv run --project apps/autoknowledge-lite uvicorn autoknowledge_lite.api:app --host 0.0.0.0 --port 8000
```

상태 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/status
```

## PC 저장 화면

브라우저에서 다음 주소를 열어 클립보드 또는 직접 입력 내용을 고정 Vault 폴더에 저장합니다.

```text
http://127.0.0.1:8000/pc
```

저장 전에 기존 문서를 상위 주제로 검색·선택할 수 있습니다. 선택하지 않으면 직전에
이 화면에서 저장한 문서가 새 문서를 참조하도록 자동 연결됩니다. 연결은 원본
Markdown 수정, 백업, 단일 파일 재색인 순서로 처리됩니다.

## Android APK 다운로드

휴대폰이 노트북과 같은 Tailscale 네트워크에 연결돼 있으면 다음 주소에서 v0.2.2 APK를 직접 받습니다.

```text
http://100.75.235.67:8000/downloads/autoknowledge-lite.apk
```

서버는 빌드된 APK 한 파일만 제공하며 임의 파일 경로는 받지 않습니다.

## 선택 설정

- `AUTOKNOWLEDGE_DATA_DIR`: 로컬 작업 JSON 경로
- `AUTOKNOWLEDGE_VAULT_DIR`: 개인 Vault 최상위 경로
- `AUTOKNOWLEDGE_AI_PROVIDER`: `local`, `openai`, `claude`
- `AUTOKNOWLEDGE_GIT_SYNC`: 개인 Vault Git 동기화 사용 여부
- `AUTOKNOWLEDGE_GIT_BRANCH`: 동기화 브랜치

비밀키는 저장소 파일에 기록하지 않습니다. 전체 사용법은 [`GUIDE-001-usage.md`](../../docs/15_projects/autoknowledge-lite/usage/GUIDE-001-usage.md), 폴더 선택은 [`GUIDE-002-vault-folder-selection.md`](../../docs/15_projects/autoknowledge-lite/usage/GUIDE-002-vault-folder-selection.md)를 확인합니다.

## MDE Knowledge Plugin 연동

AutoKnowledge Lite는 MDE 모듈이나 SQLite를 직접 사용하지 않고 버전이 명시된
JSON CLI 계약으로 Source 조회, 문서 검색, 단일 파일 색인과 명시적 상위→하위 링크
추가를 요청합니다.

```powershell
uv run --project apps/autoknowledge-lite autoknowledge-lite sources
uv run --project apps/autoknowledge-lite autoknowledge-lite capture `
  --source personal --folder "00_Inbox" --title "새 지식" --clipboard
```

색인에 실패해도 Markdown 원본은 유지되며 `retry-index`로 다시 시도할 수 있습니다.
