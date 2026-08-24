# CMD-005 Knowledge Graph API와 Viewer

## Knowledge CLI 연동 계약

```powershell
uv run mde knowledge integration-info --format json
uv run mde knowledge list --format json
uv run mde knowledge source-path personal --format json
uv run mde knowledge index-file --source personal --path "00_Inbox/note.md" --format json
```

민감 work Source를 캡처 대상으로 활성화할 때는 명시적으로 확인한다.

```powershell
uv run mde knowledge update work --capture-write true --confirm-sensitive-write
```

## Viewer 빌드와 실행

```powershell
Set-Location apps/knowledge-viewer
npm install
npm run test
npm run build
Set-Location ../..
uv run mde knowledge serve --no-open
```

`npm run build`는 production Viewer를 `mde-core` 패키지 정적 자산으로 생성한다.
일반 실행은 `uv run mde knowledge serve`이며 브라우저를 열지 않을 때만
`--no-open`을 지정한다. 서버는 외부 바인딩 옵션 없이 `127.0.0.1:8765`에서만
실행된다. personal과 work Source는 화면에서 사용자가 확인 대화상자의 `열기`를
눌러야 조회된다.

Graph API는 Source 목록, 전체·문서 중심 그래프, 문서 상세, 검색과 태그를
`/api/v1/knowledge/` 아래에서 제공한다. 검색 파라미터는 `q`, `sourceId`, `tag`,
`limit`, `confirmSensitive`이며, 전체 그래프가 제한되면 잘림 상태와 전체·반환
문서 수를 함께 반환한다.

편집 가능 Source에서는 문서 상세의 `편집`에서 제목·태그·aliases·Markdown 본문을
변경할 수 있다. `변경 미리보기`는 파일을 쓰지 않으며 `저장`을 누른 경우에만
contentHash 충돌 검사, `.mde-backups` 백업, 원자 저장과 단일 파일 재색인을 수행한다.
미해결 링크의 `연결`은 같은 Source의 기존 문서만 대상으로 하며 원본 Markdown 링크
표현을 고친 뒤 재색인한다. SQLite 링크 행을 직접 강제 수정하지 않는다.
편집 화면의 `본문 링크`에서는 실제 본문 링크를 occurrence별로 삭제할 수 있고,
같은 Source의 기존 문서를 검색해 명시적 경로 Wiki 링크로 추가할 수 있다.

관리자가 `--shared-link-target true`로 허용한 공통 Source는 편집 화면의 링크 검색
Source로 추가된다. 일반 Source 간 연결은 계속 금지하며, 공통 Source 링크는 Source
이름을 포함하는 명시적 Wiki 링크로 원본 Markdown에 저장한다.

```powershell
uv run mde knowledge update mde-docs --shared-link-target true
```

```markdown
[[mde-docs::04_development/DEV-001-development-standard|개발 표준]]
```

공통 Source 링크도 저장 후 재색인하며 양쪽 문서의 그래프와 백링크에 반영된다.
민감 Source에서 들어오는 백링크는 해당 Source 접근을 확인한 요청에서만 노출된다.

## 설치형 앱

프로덕션 Viewer는 PWA 매니페스트와 서비스 워커를 포함한다. 브라우저에
`앱 설치`가 표시되면 독립 창 앱으로 설치할 수 있다. Windows에서는 다음
스크립트가 서버를 자동 시작하고 Edge 앱 모드 창을 연다.

```powershell
powershell -ExecutionPolicy Bypass -File apps/knowledge-viewer/start-app.ps1
```

Windows 자동 시작 감독자는 단일 Viewer를 `0.0.0.0:8765`에 시작하여 localhost,
LAN, Tailscale 연결을 함께 받는다. 포트 점유 여부가 아니라 `GET /`의 HTTP 200
응답을 상태 기준으로 사용하며, 응답하지 않는 관리 대상 프로세스는 자동 재시작한다.

서비스 워커는 정적 앱 셸만 캐시하고 `/api/` 응답은 캐시하지 않는다.

## Android 앱

Android 기기와 PC가 같은 비공개 LAN 또는 Tailscale에 연결된 상태에서 PC의 해당
IP 하나에 서버를 바인딩한다. `0.0.0.0`과 공용 IP는 허용하지 않는다.

```powershell
uv run mde knowledge serve --host 192.168.0.10 --no-open
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
Set-Location apps/knowledge-viewer/android
.\gradlew.bat testDebugUnitTest assembleDebug --no-daemon --console=plain
```

생성 APK는 `app/build/outputs/apk/debug/app-debug.apk`이며 앱에는
`http://192.168.0.10:8765`처럼 PC 서버 주소를 저장한다. 공용 네트워크나 포트
포워딩으로 Graph API를 노출하지 않는다.

빌드 후 휴대폰 브라우저에서 다음 고정 경로로 APK를 다운로드할 수 있다.

```text
http://PC의-LAN-IP-또는-Tailscale-IP:8765/downloads/mde-knowledge-viewer.apk
```

서버는 이 APK 한 파일만 제공하며 요청에서 임의 파일 경로를 받지 않는다.
Android 편집 요청은 현재 서버와 동일 Origin인 private LAN/Tailscale 주소에서만
허용되며 다른 Origin과 공용 Host는 `INVALID_ORIGIN` 또는 `INVALID_HOST`로 거부된다.

## AutoKnowledge Lite CLI

```powershell
uv run --project apps/autoknowledge-lite autoknowledge-lite mde-info
uv run --project apps/autoknowledge-lite autoknowledge-lite sources
uv run --project apps/autoknowledge-lite autoknowledge-lite capture `
  --source personal --folder "20_Learning" --title "학습 기록" --clipboard
uv run --project apps/autoknowledge-lite autoknowledge-lite retry-index `
  --source personal --path "20_Learning/학습-기록.md"
```

MDE를 찾지 못하면 기존 `AUTOKNOWLEDGE_VAULT_DIR`에 파일을 저장하고 색인만
건너뛴다. 색인 실패는 원본 저장을 취소하지 않는다.
