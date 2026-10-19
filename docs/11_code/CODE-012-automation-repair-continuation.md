# CODE-012 자동 수정 후 Workflow 후속 실행 복구

- 일자: 2026-10-19 (Asia/Seoul)
- 기준: `e56629271a3a9bc7ed762c8f5813b569b576842e`
- 이번 최소 STEP: 재테스트 후 조기 완료 오류 제거, 검증 PASS
- 전체 목표: AI 개발 → 테스트·자동 수정 → 저장·전송 → 배포·상태 확인
- 전체 목표 상태: 미완료, 실제 AI/배포 대상 검증 전

## 원인과 최소 수정

execute_workflow_with_fix_loop가 repair의 test.run 성공 직후 completed를 반환했다.
원래 Workflow의 나머지 save/push/complete 및 사용자 정의 후속 단계가 실행되지
않았고, 후속 실패도 보고할 수 없었다. 복구용 합성 step ID가 원래 checkpoint의
완료 목록을 덮어써 재시도에서 이전 진행 지점을 잃는 문제도 재현했다.

기존 fix_loop.py만 수정한다. 새 실행기·Agent·프레임워크는 만들지 않는다.

- 실제 실패한 test step을 ID로 찾아 동일 args·정책으로 재검증한다.
- 임시 repair 실행 중 원래 Workflow의 checkpoint 기록은 보존한다.
- 성공한 재테스트를 원래 test ID의 output·결과·checkpoint에 연결한다.
- 기존 execute_workflow의 completed_steps 복구 기능으로 원래 Workflow를 재개한다.
- 이미 끝난 생성·적용·테스트는 중복 실행하지 않으며 후속 enabled/condition을 유지한다.
- 후속 실패는 원래 오류와 누적 결과를 보존해 전달하고 AI 수정을 다시 시작하지 않는다.
- 임시 completed_steps 설정은 후속 실행 성공·실패 모두에서 원복한다.

## 기존 코드 재사용과 신규 코드 필요성

기존 execute_workflow, dataclasses.replace, WorkflowContext/Result, checkpoint callback,
AIEngine·artifact 적용·Testing/Git/Core Plugin과 feature.yaml을 재사용했다.
기존 자동화·Git 통합 테스트 파일에 실제 버그와 회귀를 검출하는 검사만 추가했다.
새 업무 함수·클래스·소스 파일·의존성은 없다. 새 저장소 파일은 CODE·TEST 기록이다.

## 실제 연결 검증

임시 Git 저장소와 로컬 bare 원격을 만들고, 기존 feature Workflow와 실제 runtime
Plugin을 실행했다. 결정적 MockAIProvider만 테스트에서 응답을 제어했다.
첫 answer.py는 테스트에 실패하고 수정 응답은 테스트를 통과한다.
실제 pytest 두 번, artifact 보관·적용·백업, 실제 커밋과 bare 원격 push, complete
도달 및 작업 트리 clean을 확인했다. 이는 실 AI 성능이나 운영 배포 검증이 아니다.

실행:

```powershell
uv run --frozen --python 3.12 pytest packages/mde-core/tests/automation/test_fix_loop.py packages/mde-core/tests/integration/test_git_plugin.py -q -p no:cacheprovider
uv run --frozen --python 3.12 pytest -q -p no:cacheprovider
uv run --frozen --project apps/autoknowledge-lite --extra test --python 3.12 pytest apps/autoknowledge-lite/tests packages/mde-core/tests/test_mde_core_metadata.py -q -p no:cacheprovider
uv run --frozen --python 3.12 black --check .
uv run --frozen --python 3.12 ruff check .
uv run --frozen --python 3.12 mde docs check
uv run --frozen --python 3.12 mde docs check --target knowledge-guide
git diff --check
```

## 기존 기능 영향과 제한

실패 없는 기존 Workflow와 max_fix_attempts=0 경로는 그대로다. 재테스트 성공 이후의
조기 종료만 제거했다. Task 엔진이 기존 정책으로 비활성화한 Git 단계는 활성화하지
않는다. 해당 저장·푸시는 기존 외부 Sync 책임을 유지한다. 운영 Vault·Android·Viewer·
API·Capture 형식·의존성에는 변경이 없다. 외부 AI API·운영 서비스는 호출하지 않았다.

## 미완료 및 다음 필수 STEP

전체 자동 개발·배포를 사용 가능하다고 판정할 수는 없다.

1. AIWorkflowPlugin.review가 실제 AI의 거절을 해석하지 않고 approved=True를 기록한다.
   실제 승인·거절·중단 계약 및 artifact 검토 입력이 필요하다.
2. AI 전달 문맥은 주로 prompt와 artifacts다. 기존 코드 및 테스트 실패 로그 내용을
   명시적으로 전달하는 최소 입력 계약이 필요하다.
3. deploy CLI는 예약 상태다. 배포 대상, 실행 명령, 상태 확인과 실패 복구 계약이 필요하다.
4. 실제 AI provider를 통한 개발·수정과 지정 대상 배포의 end-to-end 검증은 미수행이다.

배포 대상은 사용자에게 질문했으며 응답 전 운영 배포를 임의로 구성하지 않는다.
다음 독립 작업은 리뷰의 실제 승인·거절 계약 보완이다. 새로운 Agent/RAG/Vector DB/
오케스트레이션 프레임워크는 필요하지 않다.

## Git 기록

필수 검증 통과한 이 최소 수정만 기존 요청에 따라 별도 커밋·원격 반영한다.
메시지: `fix(workflow): resume remaining steps after automatic repair`.
최종 원격 SHA와 전체 수정 파일 내용은 작업 결과 보고서·검토 ZIP에 포함한다.
