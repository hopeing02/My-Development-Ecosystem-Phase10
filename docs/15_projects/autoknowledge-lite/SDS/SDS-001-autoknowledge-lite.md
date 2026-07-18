# SDS-001 — autoknowledge-lite

## 1. 프로젝트 개요

- 프로젝트명: `autoknowledge-lite`
- 기술 유형: `python`
- 상태: MVP 3단계 구현

## 2. 목표

모바일 공유 또는 API로 전달된 콘텐츠를 검증하고 작업으로 접수한 뒤, AI 분석·Markdown 생성·Obsidian 저장·Git 동기화 흐름의 입력으로 사용합니다.

## 3. MVP 범위

- [x] Android `ACTION_SEND` 텍스트 공유 이벤트 수신
- [x] 공유 제목·본문·출처 URL의 백엔드 전송
- [x] 공유 접수 후 AI 분석·Markdown 생성 백그라운드 자동 처리
- [x] `GET /v1/status` 서비스 상태 조회
- [x] `POST /v1/share` 공유 콘텐츠 검증 및 작업 접수
- [x] UUID 작업 ID와 UTC 접수 시각 생성
- [x] 작업별 UTF-8 JSON 로컬 저장
- [x] 주입 가능한 AI 분석 인터페이스와 결정론적 로컬 분석기
- [x] `POST /v1/ai/process` 작업 분석 및 결과 저장
- [x] API 단위 테스트
- [x] 실제 OpenAI·Claude 제공자 연결
- [x] `POST /v1/markdown` Markdown 생성 및 작업 저장
- [ ] Obsidian 저장과 Git 동기화

## 4. 문서 연결

- 설계: `../design/`
- API: `../API/`
- DB: `../DB/`
- UI: `../UI/`
- 구현: `../implementation/`
- 테스트: `../tests/`
- 릴리스: `../releases/`
