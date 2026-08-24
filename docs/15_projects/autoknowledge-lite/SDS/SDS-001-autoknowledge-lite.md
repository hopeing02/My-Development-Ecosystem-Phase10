# SDS-001 · autoknowledge-lite

## 1. 프로젝트 개요

- 프로젝트명: `autoknowledge-lite`
- 기술 유형: `python`
- 상태: Active

## 2. 목표

Android 공유 메뉴 또는 클립보드로 전달된 콘텐츠를 로컬 API에서 접수하고, 분석·Markdown 생성·개인 Obsidian Vault 저장 흐름을 제공한다.

## 3. MVP 범위

- [x] FastAPI 상태·공유·분석·Markdown API
- [x] 로컬 JSON 작업 저장
- [x] 로컬 결정론적 분석과 선택적 OpenAI·Claude 분석
- [x] Obsidian 호환 Markdown 저장
- [x] 선택적 개인 Vault Git 동기화
- [x] Android 공유 대상과 클립보드 저장
- [x] Python 단위·API 통합 테스트
- [x] Android payload 단위 테스트

## 4. 저장 경계

- 공식 코드: `apps/autoknowledge-lite/`
- 공식 프로젝트 문서: `docs/15_projects/autoknowledge-lite/`
- 개인 지식: 사용자 전용 Personal Vault
- 실행 데이터·로그: Git 제외 로컬 경로

개인 Vault에는 개인 지식만 저장한다. 프로젝트 설계·구현·테스트·사용법은 프로젝트 문서 영역에 저장하며 개인 Vault로 복사하지 않는다.

## 5. 문서 연결

- 설계: `../design/`
- API: `../API/`
- DB: `../DB/`
- UI: `../UI/`
- 구현: `../implementation/`
- 테스트: `../tests/`
- 릴리스: `../releases/`
- 관련 결정: `../../../09_decisions/ADR-011-autoknowledge-lite-monorepo-integration.md`
