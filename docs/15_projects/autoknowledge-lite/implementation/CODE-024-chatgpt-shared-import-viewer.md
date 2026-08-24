# CODE-024 ChatGPT Shared Link Import Viewer

- 작성일: 2026-08-18
- 상태: Complete

## 구현

- 기존 ChatGPT Import 화면의 Data Export를 주 경로로 유지
- 같은 화면에 `공개 Shared Link 1건` 보조 입력 추가
- 최근 세션 목록 조회가 아님을 실행 버튼 바로 위에 표시
- 사용자가 버튼을 누를 때만 local Shared Import API 호출
- Export와 Shared Link가 메모리 전용 Control API Key와 안전한 결과 표시 재사용
- imported, partial, duplicate와 격리 warning 표시 유지

기존 Documents와 Capture 메뉴, Export ZIP 입력과 Knowledge Viewer 배포 구조는
변경하지 않았다.
