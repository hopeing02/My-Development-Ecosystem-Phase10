# CODE-014 기존 Codex CLI 연결

- 일자: 2026-10-19
- 이전 검증: CODE-013 / TEST-019, `04d75f2`
- 결정: ADR-021, 사용자 선택: 기존 Codex CLI

## 최소 변경과 재사용

AIProvider·AIRequest·AIResponse·JSON parser·artifact writer·AIWorkflowPlugin·
WorkflowExecutor·fix-loop·TestingPlugin·GitPlugin·LocalDeploymentPlugin을 재사용한다.
기존 Provider 등록부에 codex 하나를 추가하고 기본 mock은 유지했다.
새 codex.py는 기존 HTTP transport로 실행할 수 없는 CLI 프로세스·구조화 응답·
시간 제한 처리를 위해 필요하다. 새 SDK나 Framework는 도입하지 않았다.

AIWorkflowPlugin은 명시한 context_files의 현재 코드를 전달한다. TestingPlugin은
실패 로그 위치를 context에 기록하고 fix 호출은 실제 로그 끝 64KiB를 읽는다.
기존 모듈 재설계·CON/GOV 수정·Workflow 순서 변경은 없다.

## 파일과 실행

- `ai/providers/codex.py`, providers export/engine 등록.
- `plugins/builtin/ai.py`, `testing.py`: 기존 코드·실패 로그 문맥.
- `tests/ai/test_codex.py`, 기존 CLI/engine/plugin 회귀 보완.
- ADR-021, TEST-020, AI-PROVIDERS 사용법, 개발일지, CHANGELOG, AI 요청서.

실행 예제와 환경변수는 `docs/AI-PROVIDERS.md`를 따른다.
`codex login status`로 기존 로그인을 확인한 뒤 `inputs.ai.provider=codex`로
명시적으로 선택한다. 읽기 전용 sandbox와 JSON 산출물을 사용하고 적용은 MDE가 수행한다.

## 검증과 영향

TEST-020: root 281개·app/metadata 226개 PASS, Black 238개·Ruff·docs check PASS.
실제 Codex CLI가 별도 임시 Git 저장소에서 /double 기능 생성·리뷰를 수행했고,
실제 pytest·커밋·FastAPI 배포·HTTP result=-14 응답까지 확인했다.
별도 기존 산술 오류를 주입한 뒤 실제 pytest 실패 로그로 Codex fix를 실행하여
재테스트·커밋·임시 bare push·배포까지 완료했다. Mock AI를 사용하지 않았다.
검증용 서비스는 종료했고 기존 AutoKnowledge 서비스는 유지한다.

기본 Provider/Workflow/Task·기존 앱·Android·Viewer는 수정하지 않았다.
context_files는 opt-in이며 외부 Provider에도 동일하게 전달된다.
클라이언트 로그인·모델 접근·실행 시간은 PC 설정과 계정 상태에 의존한다.

## 미해결과 다음 STEP

작은 수치 연산 기능으로 경로를 검증했으며 임의 기능의 무제한 자동 성공을 의미하지 않는다.
라이브 push 대상은 임시 bare 원격이다. 현재 PC shell Git의 GitHub 인증은 별도로 준비해야
실제 사용자 프로젝트의 push=true를 무인 실행할 수 있다. MDE 자체 커밋은 연결된 GitHub로 반영한다.
실패 수정은 기존 fix-loop 정책대로 적용·재테스트하며 별도 reviewer 단계는 추가하지 않았다.
데이터 migration·재부팅 자동 실행·고정 URL은 이전 STEP과 같이 범위 밖이다.
다음은 사용자의 실제 작은 기능 요청을 선택해 해당 프로젝트의 명시적 코드 문맥·테스트·
배포 입력으로 실행하는 것이다. GitHub push가 필요하면 shell 인증 상태를 먼저 검증한다.
