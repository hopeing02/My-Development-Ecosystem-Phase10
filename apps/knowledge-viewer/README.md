# MDE Knowledge Viewer

Knowledge Plugin의 조회 API와 명시 저장 Command API를 사용하는 React·TypeScript·Vite 앱입니다.
Markdown 폴더나 SQLite를 직접 읽지 않습니다.

```powershell
npm install
npm run test
npm run build
```

개발 서버는 `127.0.0.1:5173`에서 실행하고 `/api`를 `127.0.0.1:8765`로
프록시합니다. 프로덕션 빌드는
`packages/mde-core/src/mde/knowledge/viewer/`에 생성되어 Python 패키지에
포함됩니다. 저장소 루트에서 `uv run mde knowledge serve`만 실행하면 됩니다.

## 앱으로 실행

프로덕션 Viewer는 설치 가능한 PWA입니다. 브라우저에 `앱 설치`가 표시되면
선택해 독립 창으로 설치할 수 있습니다. Windows에서는 다음 명령으로 서버를
자동 시작하고 Edge 앱 모드 창을 열 수 있습니다.

```powershell
powershell -ExecutionPolicy Bypass -File apps/knowledge-viewer/start-app.ps1
```

Windows 로그인 자동 시작 스크립트는 단일 Viewer를 `0.0.0.0:8765`에 시작한다.
따라서 PC에서는 `127.0.0.1:8765`, 모바일에서는 PC의 LAN 또는 Tailscale 주소로
같은 서버에 연결한다. 서버는 Tailscale보다 먼저 시작되며, Tailscale 주소가 나중에
준비되어도 재시작할 필요가 없다. 실제 HTTP 상태 확인에 실패하면 자동 재시작된다.

서비스 워커는 정적 앱 셸만 캐시하며 `/api/` 요청은 항상 로컬 Graph API로
전달합니다. 따라서 오프라인 셸이 민감 Source 데이터를 저장하지 않습니다.

Viewer는 비민감 Source 자동 선택, Source별 검색·태그, 전체·문서 중심 그래프,
깊이·방향 필터, 끊어진 링크 가상 노드, 문서 관계와 2,000자 미리보기를 제공합니다.
편집 허용 Source에서는 저장 전 변경 미리보기, contentHash 충돌 방지, Markdown 편집과
기존 문서로의 미해결 링크 연결을 제공합니다. Viewer는 파일이나 SQLite에 직접
접근하지 않으며 Command API가 원본 Markdown을 저장한 뒤 단일 파일을 재색인합니다.
