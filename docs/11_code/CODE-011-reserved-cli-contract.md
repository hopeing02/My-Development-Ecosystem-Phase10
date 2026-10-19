# CODE-011 예약 CLI 계약 분석 및 표시 정정

- 일자: 2026-10-19 (Asia/Seoul)
- 기준 커밋: `8b02705545d35f396de4accee607bdd79857c378`
- 상태: 이번 분석·정합성 수정 STEP 검증 PASS
- generate/inbox 기능 구현 상태: 계속 reserved

## 분석 결과와 재사용 가능성

- CLI에 generate command 및 inbox list의 인자 파서는 있으나 main dispatch는
  공통 run_reserved_command로 이어져 코드 2를 반환한다. IMPLEMENTED_COMMANDS에도 없다.
- 대응하는 tools/mde_generate.py, tools/mde_inbox.py와 generate_command/list_patches
  구현은 현재 저장소에서 찾지 못했다. 주석 처리된 import와 호출은 구현 근거가 아니다.
- 프로젝트·문서 생성용 tools/mde_toolkit/core.py 및 commands/new.py는 다른 계약이므로
  코드·테스트 모듈 생성기로 대체 연결하지 않았다.
- task/model.py의 find_task_manifests/load_pending_tasks는 legacy manifest 자산이다.
  하지만 ensure_tasks_dir를 통해 폴더를 생성하므로 읽기 전용 목록 명령으로 바로
  연결하면 새 부작용이 생긴다. task/queue.py 역시 폴더 생성·이동용이므로 재사용을 보류했다.
- 실제 도움말은 생성·목록 기능이 동작하는 것처럼 설명했다. 두 관리 가이드는 reserved
  상태 표시는 맞지만 최신 codex 및 Knowledge 옵션 등이 누락되어 docs check가 실패했다.
- 기존 tests/test_mde_cli.py의 예약 명령 실행 검사는 문자열 안에 있어 실행되지 않았다.
  관련 계약만 새 활성 검사로 보완하고 무관한 문자열 블록을 일괄 복구하지 않았다.

## 최소 수정 및 기존 코드 재사용

build_parser의 generate/inbox와 해당 하위 명령 4곳에서 help·description만 정정했다.
명령 이름·인자·dispatch·반환 코드·구현 상태는 변경하지 않았다. 새 업무 함수·클래스·
소스 파일은 없다. 기존 run_reserved_command, docs 동기화 도구와 기존 테스트 파일을
재사용했다. 신규 문서는 사용자 요구에 따른 CODE·TEST 기록 2개다.

CLI 테스트 2개 함수의 매개변수 사례 8개로 예약 도움말과 기존 파일·디렉터리 보존을
검증했다. 문서 테스트에는 실제 두 관리 가이드와 parser의 일치 검사 1개 함수/2개
사례를 추가해 다시 오래된 상태가 되면 실패하도록 했다.

## 문서 갱신

Accepted ADR-006에 따라 mde docs update로 diff를 확인한 뒤 --apply로 각 관리
구간만 갱신했다. 전체 MDE 가이드에는 예약 하위 구문의 미구현·무변경 계약을 본문에
별도 설명했다. 다른 본문과 지침·CON/GOV·프로젝트 구조는 보존했다.

## 실행 방법

```powershell
uv run --frozen --python 3.12 mde generate --help
uv run --frozen --python 3.12 mde generate command --help
uv run --frozen --python 3.12 mde inbox --help
uv run --frozen --python 3.12 mde inbox list --help
uv run --frozen --python 3.12 mde docs check
uv run --frozen --python 3.12 mde docs check --target knowledge-guide
uv run --frozen --python 3.12 pytest -q -p no:cacheprovider
uv run --frozen --project apps/autoknowledge-lite --extra test --python 3.12 pytest apps/autoknowledge-lite/tests packages/mde-core/tests/test_mde_core_metadata.py -q -p no:cacheprovider
uv run --frozen --python 3.12 black --check .
uv run --frozen --python 3.12 ruff check .
git diff --check
```

구체적 결과는 `../12_test/TEST-017-reserved-cli-contract.md`를 따른다.

## 기존 기능 영향·미해결 사항·다음 STEP

기존 CLI 실행 동작은 그대로이며 도움말과 실제 상태를 맞췄다. generate/inbox가
구현됐다고 표시하지 않았다. 기존 업무 기능·AI·Workflow·Agent·Capture·Vault·
Android·Viewer 소스와 의존성은 변경하지 않았다.

이번 표시·문서 정합성 STEP의 실패는 없다. 실제 두 예약 기능은 미완료다.
다음 최소 후보는 inbox list를 읽기 전용으로 제공할 입력·출력 계약과 기존 manifest
검색 함수 재사용 범위를 확정하는 것이다. 완료·실패 큐와 legacy patch/manifest의
범위를 구분해야 하며, 새로운 Agent 또는 생성기 프레임워크는 필요하지 않다.
Viewer·Android·실기기 검증은 이번 STEP에서 재실행하지 않았다.

## Git 반영

기존 커밋·푸시 요청에 따라 필수 검증 통과 후 별도 커밋으로 반영한다.
커밋 메시지: `fix(cli): clarify reserved commands and synchronize guides`.
최종 원격 SHA와 전체 수정 파일 내용은 작업 보고서·검토 ZIP에 남긴다.
