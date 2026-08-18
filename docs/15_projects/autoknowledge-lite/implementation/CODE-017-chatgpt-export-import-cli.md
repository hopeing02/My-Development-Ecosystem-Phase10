# CODE-017 ChatGPT Export Import CLI

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

사용자가 명시적으로 지정한 ChatGPT Data Export ZIP을 기존 Source, Archive와
Projection 서비스에 연결하는 로컬 CLI 진입점을 제공한다.

## 구현

- `autoknowledge-lite chatgpt-import <archive>` 명령 추가
- 기존 `AUTOKNOWLEDGE_DATA_DIR` 또는 `--data-dir` 지원
- 정상 Import, 부분 성공, 중복 Import를 `imported|partial|duplicate`로 구분
- 발견, 신규 projection, 중복, 실패 Session 수와 warning code를 JSON으로 출력
- Archive 자체 오류는 구조화된 error code와 종료 코드 1 반환
- 개별 Session 실패는 raw Archive 저장 성공을 유지하고 종료 코드 0 반환
- CLI 출력에서 원본 content와 raw Archive 절대 경로 제외

## 호환성

기존 `mde-info`, `sources`, `capture`, `retry-index`, `capture-relations` 명령은
변경하지 않았다. ChatGPT Clip, Markdown, API와 Viewer에도 영향이 없다.
