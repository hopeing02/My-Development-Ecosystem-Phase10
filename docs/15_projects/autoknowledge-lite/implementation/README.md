# AutoKnowledge Lite 구현

## 구현 범위

- FastAPI 상태·공유·분석·Markdown API
- Pydantic 요청·응답 모델과 로컬 JSON 저장소
- 로컬·OpenAI·Claude 분석기 경계
- 공개 URL 본문 수집과 내부망 접근 차단
- Obsidian 호환 Markdown 원자적 저장
- 선택적 개인 Vault Git 동기화
- Android 공유 대상과 클립보드 저장
- Windows 로그인 자동 시작 스크립트

## 공식 코드

실행 가능한 Python·Android 구현과 테스트는 `apps/autoknowledge-lite/`에서 관리한다. 별도 `.runtime/autoknowledge-lite/`는 통합 검증용 복구 원본이며 공식 개발 위치가 아니다.

## 구현 기록

- `CODE-001-monorepo-integration.md`: 별도 저장소의 실행 코드와 자동 시작 경로 통합
- `CODE-002-vault-folder-selection.md`: 고정 개인 Vault 폴더 선택과 경로 보호
- `CODE-003-android-apk-download.md`: 고정 APK 한 파일의 휴대폰 다운로드
- `CODE-004-pc-capture-page.md`: PC 클립보드·직접 입력과 고정 폴더 저장 화면
- `CODE-005-obsidian-knowledge-graph.md`: Obsidian 메타데이터·MOC·Bases 자동화
