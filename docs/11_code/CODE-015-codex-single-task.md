# CODE-015 MDE-CODEX-W1 — Codex 단일 개발 Workflow 자동화

- 일자: 2026-10-21 (Asia/Seoul)
- 기준: CODE-014 / TEST-020, 기존 Codex CLI Provider
- 범위: 독립 `tools/automation` 실행기, DevelopmentTask JSON → Codex → 경로 검사 → 검증 → result.json
- 상태: W1 구현·실 CLI 1건·회귀 검증 PASS, TEST-021 참조

## 이번 구현 목표

하나의 명시적 개발 요청을 기존 로그인된 Codex CLI로 실행하고 성공 여부를 JSON으로 남긴다.
W2의 Workflow/task_runner 연결, mde save, commit/push, 배포, 실패 자동수정 반복,
멀티에이전트는 연결하지 않는다. 실패 시 변경을 되돌리지 않고 검토 증거로 보존한다.

## 생성·수정 파일

- `tools/automation/run_codex_single_task.py`: 운영 실행기.
- `tools/automation/__init__.py`: 독립 도구 패키지.
- `tools/automation/request.codex-task.example.json`: 입력 예제.
- `tools/tests/test_codex_single_task.py`: 실제 Git·프로세스·검증 명령을 사용하는 회귀 검사.
- CODE-015, TEST-021, 개발일지, AI 요청서, CHANGELOG.

## 기존 검증 코드 재사용

로컬의 기존 MDE 저장소에서 CODE-014 및 TEST-020과 실제 Provider를 확인했다.
`mde.git.repository.ensure_repository`, `ensure_clean_worktree`, `get_local_head`와
`mde.codex_capture.security.redact_text`를 직접 import하여 재사용한다.
기존 CodexCLIProvider 및 Workflow/task_runner 소스는 수정하지 않는다.

기존 Provider의 계약은 읽기 전용 Codex가 파일 변경안을 artifact로 반환하고 MDE가
적용하는 방식이다. W1은 workspace-write로 실제 파일을 변경하므로 기존 Provider의
응답 계약을 억지로 바꾸지 않고 별도 실행 진입점만 추가한다. 실행 파일은 기존과 같은
`MDE_CODEX_EXECUTABLE` 또는 PATH의 codex, 인증과 모델은 기존 CLI 설정을 사용한다.
프로세스 종료는 기존 Provider에서 검증된 psutil 자식 종료 방식을 따른다.
psutil은 이미 잠긴 런타임 의존성으로 새 SDK·Framework·의존성을 추가하지 않는다.

## 제공된 초안에서 보완한 문제

1. 현재 설치 CLI에 맞게 `codex -a never exec --sandbox workspace-write` 순서를 사용한다.
2. 폴더 허용 목록의 마지막 `/`를 보존하며 형제 폴더의 접두사 일치를 허용하지 않는다.
3. 절대 경로·드라이브 상대 경로·상위 이동·Git 메타데이터·Windows 예약 이름을 거부한다.
4. JSON 구조·필드 타입·ID·명령 배열·30~1800초 제한을 검증한다.
5. Git 변경 파일은 NUL 구분으로 읽어 공백·한글·rename 이전/이후 경로를 보존한다.
6. clean worktree와 HEAD를 기준으로 Codex 직후 및 각 검증 명령 후 변경을 재검사한다.
7. 실패·시간 초과에도 변경 파일을 수집하며 검증 실패 다음 명령은 실행하지 않는다.
8. 초기 입력 오류와 dirty worktree도 실패 JSON으로 남긴다.
9. 요청·추적 소스 파일 덮어쓰기를 거부하고, 저장소 내부 결과는 ignored/untracked 경로만 허용한다.
10. 로그 민감정보 가리기, 원자적 result 교체, 실행별 임시 응답 파일을 사용한다.

## 실행 및 테스트 명령

기존 MDE 의존성 환경에서 실행한다. 설치 후 직접 스크립트 실행 또는 모듈 실행 모두 가능하다.
JSON의 projectPath와 실제 요구사항·허용 파일·검증 명령은 대상 프로젝트에 맞게 바꾼다.
검증 명령은 shell 문장이 아닌 argv 배열이며 작업 폴더는 projectPath다.
2026-10-25 호환 보완: `projectPath`는 기존 절대 경로 외에 `"."`도 지원한다.
`"."`은 요청 JSON 파일의 폴더가 아닌 실행 명령의 현재 작업 폴더를 뜻하므로 저장소 루트에서 실행한다.
그 외 상대 경로는 계속 거부한다. 이 변경은 DOC-PARSER-1의 이식 가능한 요청 실행에 필요한
입력 해석 보완이며 Codex CLI 연결부와 Workflow/task_runner는 변경하지 않는다.
Windows에서 uv가 PATH에 없다면 각 명령 첫 항목에 uv.exe 절대 경로를 지정한다.
별도 Python 환경이면 해당 python.exe와 `-m pytest`, `-m ruff`, `-m black`도 사용할 수 있다.

```powershell
uv run --frozen python tools/automation/run_codex_single_task.py `
  --request tools/automation/request.codex-task.example.json `
  --result .mde/codex-development/result.json

uv run --frozen pytest tools/tests/test_codex_single_task.py -q -p no:cacheprovider
uv run --frozen pytest -q -p no:cacheprovider
uv run --frozen ruff check .
uv run --frozen black --check .
uv run --frozen mde docs check
uv run --frozen mde docs check --target knowledge-guide
git diff --check
```

예제 요청은 사용법을 보여주는 템플릿이며 그 상태로 운영 요청이 완성된 것은 아니다.
runner 소스 자체를 수정 중인 dirty MDE 저장소를 개발 대상으로 지정하면 사전 검사에서 중단된다.
이번 실 CLI 검증은 별도 clean 복제본을 대상으로 수행한다.

## 결과 계약

`success`, `taskId`, `stepId`, `codexExitCode`, `changedFiles`, `disallowedFiles`,
`validationResults`(command/exitCode/success/stdout/stderr), `codexSummary`,
`codexStderr`, `error`를 기록한다. 성공 exit 0, 기록 가능한 작업 실패 exit 1,
안전하지 않은 출력 경로나 결과 쓰기 불가 등 CLI 사용 오류는 stderr와 exit 2다.
손상된 입력은 식별자를 신뢰할 수 없어 ID가 null일 수 있다.
각 subprocess의 제한 시간은 timeoutSeconds이며 전체 작업의 총 시간 예산은 아니다.

## 실제 결과와 기존 기능 영향

최종 수치·실 CLI 결과는 TEST-021에 기록한다. 기존 Provider·기본 mock·Workflow·Task
정책과 앱 코드는 변경하지 않는다. 기존 서버나 개인 Vault를 실행·중단하지 않는다.
자동 commit/push/save/배포를 실행기에 추가하지 않는다. W1 소스의 GitHub 반영은
검증 후 사용자가 별도로 요청한 commit/push 작업으로 수행한다.

## 한계와 다음 STEP

allowedFiles는 프롬프트 지시와 Git 사후 검사다. OS의 파일별 쓰기 차단 장치가 아니다.
ignored 파일·저장소 밖 파일·Git 메타데이터의 모든 변조를 추적하거나 원격 push를
기술적으로 차단하지 않으므로, 신뢰하는 요청과 검증 명령을 격리된 복제본에서 실행한다.
기존 ignored 파일을 허용 목록에 넣어도 그 내용 변화를 Git으로 판정할 수 없다.
timeout 자식 종료 역시 모든 탈출·분리 프로세스에 대한 보안 격리를 뜻하지 않는다.
성공은 CLI 종료·경로 검사·주어진 검증 명령의 통과이며 임의 요구사항의 의미적 완전성을 보장하지 않는다.

W1의 실제 1건 성공 후 다음 STEP은 **MDE-CODEX-W2 — 기존 MDE Workflow/task_runner 연결**이다.
이번 STEP에서는 해당 연결을 시작하지 않는다.

## 검토 후 사용자가 실행할 Git 명령

테스트 결과를 검토한 뒤 이 STEP 파일만 선택한다. runner는 아래 명령을 실행하지 않는다.

```powershell
git add tools/automation tools/tests/test_codex_single_task.py docs/11_code/CODE-015-codex-single-task.md docs/12_test/TEST-021-codex-single-task.md docs/14_operations/DevelopmentLog/2026-10-21.md 11_AI_Request/2026-10-21-codex-single-task.md CHANGELOG.md
git commit -m "feat(automation): add guarded single Codex development task"
```

## 공식 실행 계약

[OpenAI Codex 비대화형 실행 예제](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex)
및 실제 설치된 `codex --help`, `codex exec --help`를 함께 확인했다.
공식 예제의 반복 수정 흐름은 이번 W1에 연결하지 않는다.
