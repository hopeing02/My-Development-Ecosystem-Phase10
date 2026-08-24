# RELEASE-002 AutoKnowledge Lite v0.2.1

- 릴리스일: 2026-07-24
- 상태: Ready

## 추가

- PC 브라우저용 `/pc` 저장 화면
- 클립보드 붙여넣기와 직접 입력
- 고정 6개 Vault 폴더 선택
- 저장 성공·실패 상태 표시

## 보안

- 임의 폴더와 파일 경로 입력 없음
- 기존 서버 allowlist 재검증
- 백그라운드 클립보드 감시 없음

## 검증

- Python: 55 passed
- Ruff: 통과
- 앱 formatter: 18 files formatted
- MDE 회귀: 146 passed
