# autoknowledge-lite — implementation

## MVP 1: 접수

- FastAPI 애플리케이션 팩토리와 실행 엔트리포인트
- Pydantic 기반 공유 요청·응답 검증
- UUID 작업 ID와 UTC 접수 시각 생성
- 주입 가능한 로컬 JSON 저장소

## MVP 2: AI 처리 경계

- `KnowledgeAnalyzer` 프로토콜로 외부 AI 제공자와 API 계층 분리
- 테스트와 로컬 실행에 사용하는 결정론적 분석기
- 저장된 작업 조회·갱신 및 분석 결과 영속화
- 저장소·분석기 오류를 안전한 HTTP 응답으로 변환

## MVP 3: 실제 AI 제공자

- OpenAI Responses API 제공자
- Anthropic Messages API 제공자
- 환경변수 기반 제공자·모델 선택
- 외부 응답의 JSON 검증과 안전한 오류 변환

## MVP 4: Markdown 생성

- YAML 호환 메타데이터와 지식 본문 렌더링
- 분석 선행 조건 검증
- 완성된 Markdown의 작업 레코드 저장

Obsidian, Git 연동은 후속 구현 단위입니다.
