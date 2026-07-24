# AutoKnowledge Lite 테스트

## 자동 테스트 범위

- 상태·공유·분석·Markdown API
- 로컬 작업 JSON 저장과 오류 격리
- 로컬·OpenAI·Claude 분석기 변환
- 공개 URL 본문 추출과 안전 제한
- Obsidian 파일명·UTF-8 저장
- Git 동기화 명령과 Vault 외부 경로 차단
- Android 공유·클립보드 payload
- Android Debug APK 빌드
- MDE 전체 회귀

테스트는 임시 디렉터리와 테스트 대역을 사용하며 실제 개인 Vault나 Git 원격에 데이터를 쓰지 않는다.

## 테스트 기록

- `TEST-001-monorepo-integration.md`: 모노레포 통합 및 저장 경계 검증
- `TEST-002-vault-folder-selection.md`: 고정 폴더 선택·기본값·경로 이탈 방지 검증
- `TEST-003-android-apk-download.md`: APK 고정 다운로드·404·Tailscale 실제 파일 검증
- `TEST-004-pc-capture-page.md`: PC 화면·고정 폴더·기존 저장 API 연결 검증
- `TEST-005-obsidian-knowledge-graph.md`: 기존 원문 보존과 자동 그래프 구성 검증
