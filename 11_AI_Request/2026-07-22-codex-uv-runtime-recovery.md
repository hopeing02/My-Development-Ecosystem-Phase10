# uv 실행 환경 복구 요청

- 요청 ID: MDE-UV-RECOVERY-20260722
- 작성일: 2026-07-22
- 대상 AI: Codex
- 처리 상태: Completed

## 목적

MDE 공식 실행 명령인 `uv run mde`를 사용할 수 있도록 uv 실행 환경을 복구한다.

## 요청 내용

기존 uv 설치 여부를 확인하고 없으면 공식 사용자 로컬 설치를 수행한 뒤 PATH와 Knowledge 증분 스캔을 검증한다.

## 제약 조건

시스템 전역 설치를 피하고 사용자 PATH만 변경한다. 기존 Python 환경과 프로젝트 데이터를 삭제하거나 초기화하지 않는다.

## 기대 결과

새 터미널에서 uv를 인식하고 `uv run mde knowledge scan mde-docs`가 오류 없이 실행된다.
