# CODE-004 PC 저장 화면

- 작성일: 2026-07-24
- 버전: 0.2.1
- 상태: Complete

## 구현

- `pc_ui.py`에 의존성 없는 정적 HTML·CSS·JavaScript 화면을 추가했다.
- `GET /pc`가 `HTMLResponse`로 화면을 제공한다.
- 고정된 6개 폴더만 `select` 항목으로 제공한다.
- 클립보드는 버튼 클릭 시 `navigator.clipboard.readText()`로 읽는다.
- 저장은 기존 `POST /v1/share`를 호출한다.
- 성공 후 제목과 내용만 비우고 상태를 표시한다.

별도 웹 프레임워크, 빌드 도구와 외부 CDN은 추가하지 않았다.
