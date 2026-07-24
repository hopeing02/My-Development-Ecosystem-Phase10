# AutoKnowledge Lite 사용 가이드

- 프로젝트 ID: `autoknowledge-lite`
- 작성일: 2026-07-23
- 상태: Active

## 1. 저장 경계

- 프로그램 코드: `apps/autoknowledge-lite/`
- 프로젝트 공식 문서: `docs/15_projects/autoknowledge-lite/`
- 개인 지식: `AUTOKNOWLEDGE_VAULT_DIR`로 지정한 개인 Vault
- 작업 JSON: `apps/autoknowledge-lite/data/` 또는 `AUTOKNOWLEDGE_DATA_DIR`
- 실행 로그: `apps/autoknowledge-lite/logs/`

개인 Vault에는 개인 지식만 저장한다. 프로젝트 설계·구현·테스트·사용법은 프로젝트 공식 문서 영역에서만 관리한다. 작업 JSON과 로그는 개인 원문을 포함할 수 있으므로 Git에 추가하지 않는다.

## 2. 설치

MDE 저장소 루트에서 실행한다.

```powershell
uv sync --project apps/autoknowledge-lite --extra test
```

## 3. 서버 실행

수동 실행:

```powershell
uv run --project apps/autoknowledge-lite uvicorn autoknowledge_lite.api:app --host 0.0.0.0 --port 8000
```

상태 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/status
```

Windows 로그인 자동 시작은 `MDE-AutoKnowledge-Lite` 예약 작업을 사용한다. 공식 시작 스크립트는 `apps/autoknowledge-lite/scripts/start-server.ps1`이며 원시 로그는 `apps/autoknowledge-lite/logs/server-autostart.log`에 기록된다.

## 4. Android 앱

Debug APK 생성:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
.\apps\autoknowledge-lite\android\gradlew.bat `
  -p apps/autoknowledge-lite/android assembleDebug
```

APK 위치:

```text
apps/autoknowledge-lite/android/app/build/outputs/apk/debug/app-debug.apk
```

휴대폰 앱에 `http://PC-IP:8000` 형식의 서버 주소를 저장한다. Tailscale을 사용한다면 PC의 Tailscale IPv4 주소를 사용한다.

## 5. 클립보드 저장

1. 저장할 전체 텍스트를 복사한다.
2. AutoKnowledge Lite를 연다.
3. 서버 주소가 저장되어 있는지 확인한다.
4. 개인 Vault의 저장 폴더를 선택한다.
5. `클립보드 내용 저장`을 누른다.
6. 서버가 작업 JSON을 만들고 분석·Markdown·선택한 개인 Vault 폴더 저장을 실행한다.

선택할 수 있는 폴더는 `00_Inbox`, `10_Life`, `20_Learning`, `30_Interests`, `40_Reference`, `90_Archive`로 고정되어 있다. 선택하지 않으면 `00_Inbox`를 사용한다. 앱과 서버는 임의 경로를 받지 않으며 `../` 같은 Vault 이탈 경로를 거부한다. 자세한 절차는 `GUIDE-002-vault-folder-selection.md`를 참고한다.

## 6. Git 동기화

`AUTOKNOWLEDGE_GIT_SYNC=true`이면 생성된 Markdown 한 파일만 현재 설정된 개인 Vault Git 저장소에 동기화한다. 이번 모노레포 통합에서는 기존 동기화 설정과 원격 저장소를 변경하지 않았다.

Git 동기화 정책을 변경할 때에는 별도 ADR·구현·테스트 기록을 작성한다.

## 7. 테스트

```powershell
uv run --project apps/autoknowledge-lite pytest
uv run ruff check apps/autoknowledge-lite
uv run ruff format --check apps/autoknowledge-lite
```

Android:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
.\apps\autoknowledge-lite\android\gradlew.bat `
  -p apps/autoknowledge-lite/android testDebugUnitTest assembleDebug
```

## 8. 문제 해결

`서버 주소와 실행 상태를 확인하세요`가 표시되면 다음을 확인한다.

```powershell
Get-ScheduledTask MDE-AutoKnowledge-Lite
Invoke-RestMethod http://127.0.0.1:8000/v1/status
Get-Content apps/autoknowledge-lite/logs/server-autostart.log -Tail 30
```

노트북이 꺼져 있거나 절전 상태이면 휴대폰에서 서버에 연결할 수 없다.

## 변경 기록

- 2026-07-23: v0.2.0 고정 Vault 폴더 선택, 기본 Inbox, 서버 경로 허용 목록과 Android 재설치 절차를 반영했다.
- 2026-07-23: 프로젝트별 사용법 문서 위치와 갱신 규칙을 확정했다.
- 2026-07-23: 실행 코드의 MDE 모노레포 통합, 공식 서버 경로, Android 빌드, 저장 경계와 문제 해결 절차를 반영했다.
