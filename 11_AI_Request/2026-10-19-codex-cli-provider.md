# AI Request: 기존 Codex CLI Provider

- 요청 ID: AI-20261019-CODEX-CLI
- 작성일: 2026-10-19
- 대상 AI: 기존 PC Codex CLI
- 목적: MDE의 기존 개발·테스트·로컬 배포 경로에 실제 AI 연결
- 사용자 선택: 기존 Codex CLI 사용
- 처리 상태: 구현·회귀·실제 CLI acceptance 완료 (TEST-020)

요청: 기존 AIProvider 계약을 재사용해 codex exec를 추가하고 실제 코드와 실패 로그를
전달한다. 기본 동작은 외부 AI 없이 유지한다. 새로운 Agent/RAG/DB Framework를 도입하지 않는다.

제약: 검증 완료 모듈 재작성 금지, 정책/구조 변경 금지, 비밀키 출력 금지,
실패를 mock 성공으로 대체 금지. 실제 코드 적용·테스트·Git·배포는 기존 MDE가 수행한다.

기대 결과: 생성·리뷰·실제 pytest·커밋·로컬 배포 및 실패 수정 후 downstream 재개 확인.
실제 acceptance는 개인 데이터 없는 임시 저장소의 /double?value=int 기능으로 수행한다.
관련 결정·결과: ADR-021, CODE-014, TEST-020.
