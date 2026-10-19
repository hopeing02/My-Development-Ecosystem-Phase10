# ADR-021 기존 Codex CLI Provider 연결

- 일자: 2026-10-19
- 상태: Accepted
- 기준: CON-006, GOV-006/009, DEV-001, CODE-013

사용자는 실제 AI 실행 방식으로 현재 PC의 기존 Codex CLI를 선택했다.
기존 AIProvider/AIRequest/AIResponse 계약에 codex Provider만 추가한다.
Codex exec는 read-only sandbox, 승인 대기 없음, ephemeral, stdin 요청,
JSON Schema 및 마지막 응답 파일로 실행한다. 기존 CLI 로그인과 기본 모델을 재사용한다.
CLI가 직접 Git·배포를 수행하지 않고 MDE의 기존 artifact/review/apply/test/save/deploy를 따른다.
실패·시간 초과·응답 누락·잘못된 JSON은 실패하며 mock으로 대체하지 않는다.

명시적인 ai.context_files는 저장소 내부 UTF-8 파일만 읽는다. 파일별 64KiB,
최대 20개·전체 256KiB로 제한한다. fix 입력에는 실제 실패 로그 끝 64KiB를 포함한다.
외부 Provider에도 동일한 문맥 계약을 사용하며 기존 기본값 mock은 유지한다.
설치·로그인이 없는 PC는 명확한 설정 오류를 반환한다. 새 SDK·프레임워크는 추가하지 않는다.

검증은 subprocess 대역 회귀와 실제 Codex CLI를 이용한 별도 임시 Git 저장소의
생성·리뷰·실패 수정·실제 pytest·커밋·bare push·로컬 FastAPI 배포로 구분한다.
운영 앱과 개인 데이터는 acceptance에 사용하지 않는다.

근거: https://learn.chatgpt.com/docs/non-interactive-mode
