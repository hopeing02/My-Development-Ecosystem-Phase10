# CODE-015 ChatGPT Raw Archive Store

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

발견이 완료된 ChatGPT Export ZIP을 기존 로컬 데이터 정책 아래 불변 원본으로 보관하고
manifest와 Archive hash를 통해 중복 Import를 방지한다. Adapter, API와 Viewer에는
아직 연결하지 않는다.

## 구현

- 기존 `AUTOKNOWLEDGE_DATA_DIR` 설정과 Git 제외 데이터 경로 재사용
- `raw/chatgpt/imports/{hash 기반 import_id}` 저장 구조 추가
- 원본 ZIP을 `export.zip`, 메타데이터를 `manifest.json`으로 저장
- SHA-256, byte 크기, 원본 파일명, Import 시각, Session/warning 수 기록
- 원본 conversations member와 warning code 집합 기록
- staging 디렉터리에 기록한 뒤 동일 filesystem에서 원자적으로 확정
- Archive와 manifest에 사용자 전용 파일 권한 적용
- 동일 Archive 재요청은 기존 manifest와 저장 ZIP을 검증하고 duplicate 반환

## 무결성

- discovery 이후 source hash가 바뀌면 저장하지 않음
- 복사 중 계산한 hash가 원본 hash와 다르면 staging 정리 후 실패
- 기존 manifest 또는 저장 ZIP이 손상되면 덮어쓰지 않고 오류 반환
- schema, source type과 acquisition method를 고정값으로 검증
- 입력 ZIP을 수정하거나 삭제하지 않음

## 호환성

기존 Share Store, ChatGPT Clip, Markdown, Capture API, Codex 수집, Knowledge Graph와
Viewer는 수정하지 않았다.
