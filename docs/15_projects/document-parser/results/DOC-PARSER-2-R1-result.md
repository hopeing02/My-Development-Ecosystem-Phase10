# DOC-PARSER-2 G2-R1 — 실제 연속 실행 검증 결과

## 판정

**PASS — MDE가 2A-R1 → 검증 → 커밋 → 2B-R1 → 검증 → 커밋을 단 한 번의 Agent 실행으로 완료했다.**

- 실행일: 2026-11-02, Asia/Seoul.
- 실제 시작/종료: 08:06:39 ~ 08:10:26, 226.22초.
- 실제 Agent 종료 코드: 0. Completed=2, Failed=0, Pushed=False, Recovered=0.
- 원격 main: 16a5b5cb75a00bce392e22ee8487a9ff99fa7fd3 (실행 전후 동일).
- 원래 준비 기준: 99eb8bbce0acd767ec83c5af873bccd65d3950a7.
- 원격 R1 준비 브랜치: validation/doc-parser-2-r1-base.
- 원격 R1 준비 커밋: ec6ef16d2808850421c5904fb710b824e6bcec3b.
- 로컬 실행 브랜치: validation/doc-parser-2-r1-exec.
- 최종 개발 HEAD: b2a7e20197dac3320a89b9d315c7da0655581ab1.

사용자 승인 후에만 준비 브랜치를 등록했다. 로컬 원래 준비 커밋 ab3d900과 원격 준비 커밋 ec6ef16은
내용이 같음을 diff로 확인하고 준비 브랜치를 동기화했다. 원격 실행 브랜치는 생성하지 않았다.

## STEP별 실제 결과

| 항목 | DOC-PARSER-2A-R1 | DOC-PARSER-2B-R1 |
|---|---|---|
| 최종 판정 | PASS | PASS |
| TaskStore | completed | completed |
| Review | approved=true | approved=true |
| artifact-allowlist | 통과 | 통과 |
| change.apply | 통과 | 통과 |
| pytest | 55 passed, 0.10초 | 99 passed, 1.00초 |
| Ruff | 통과 | 통과 |
| Black 26.10.1 | 통과, 8 files unchanged | 통과, 9 files unchanged |
| changed-files | 통과 | 통과 |
| Checkpoint | completed, complete까지 | completed, complete까지 |
| STEP 커밋 | 2916a8631582f305c11e97dc081e4acac0a8aa8f | b2a7e20197dac3320a89b9d315c7da0655581ab1 |

두 결과 YAML의 10개 Workflow STEP은 모두 completed, attempts=1이다. 미실행/실패 STEP 없음.
자동 수정 반복, 검토 우회, 수동 후보 수정, Agent 재실행은 없었다.

## 실제 실행 환경과 경로

Codex CLI는 ChatGPT 로그인 상태였다. 실행 직전 사용량 조회는 사용 가능,
5시간 한도 사용 6% / 주간 사용 26%였다. 모델은 기존 CLI 설정을 사용했으며 임의 변경하지 않았다.

Python 3.12 검증 환경을 재사용했다. UV_PROJECT_ENVIRONMENT는 이전 준비 폴더의 .venv이며,
PYTHONPATH는 새 R1 worktree의 packages/mde-core/src와 apps/document-parser/src를 우선했다.
실행 전 실제 mde.sync.engine.__file__이 R1 worktree를 가리킴을 사전 검사했다.
UV_NO_SYNC=1, PYTHONUTF8=1, BLACK_NUM_WORKERS=1, MDE_CODEX_TIMEOUT=1800으로 실행했다.

```powershell
uv run mde agent --once --auto-save --no-push
```

MDE Agent → 기존 G2 Sync → TaskStore → execute_task → doc-parser-2-r1 Workflow → CodexCLIProvider
경로를 그대로 사용했다. Workflow 내부 git.save/git.push 없이 G2가 각 완료 STEP을 저장했다.
W1, 직접 Codex 대체 실행기, mock AI는 사용하지 않았다.

## 코드 누적과 실제 변경 파일

2A 커밋에서 추가:
- apps/document-parser/src/document_parser/paragraphs.py
- apps/document-parser/tests/test_paragraphs.py

2B 커밋에서 추가:
- apps/document-parser/tests/test_paragraphs_edge_cases.py

2B 생성 문맥은 실제 2A의 paragraphs.py와 test_paragraphs.py를 포함한다.
2B 테스트는 document_parser.paragraphs를 import하여 실제 함수를 호출한다.
2A 커밋 대비 최종 커밋에서 paragraphs.py와 test_paragraphs.py의 diff가 없음을 확인했다.
따라서 2B는 2A 결과를 보존한 상태에서 경계 테스트를 누적했다.
기존 Parser 테스트 47개에 2A 테스트 8개, 2B 테스트 44개가 추가되어 최종 99개가 통과했다.

기능은 inspect_document_source를 재사용해 HWPX p 문단별 문자열을 반환한다.
구역 숫자 정렬, 네임스페이스, 문단 순서, 빈 문단/섹션, 공백/한글,
정확한 section 경로, 잘못된 ZIP/XML, 입력 오류 및 원본 불변을 합성 fixture로 검증한다.
표/서식 복원, OCR, 실제 기관 문서 검증, DOC-PARSER-3는 범위 밖이다.

Git 기록의 추가 bookkeeping:
- tasks/pending의 R1 YAML 두 개가 tasks/completed로 이동 (R100, 정의 동일).
- tasks/completed/DOC-PARSER-2A-R1.result.yaml, DOC-PARSER-2B-R1.result.yaml 생성.
- status/mobile-summary.json 갱신.

이외 허용 외 변경은 없다. TaskStore, Agent, Sync Engine, W1, source.py, hwpx.py,
__init__.py, 기존 테스트, 확정 DOC-PARSER-2.md 및 R1 지침/Workflow는 실행 중 변경되지 않았다.
보고서는 외부 검증이 끝난 후 별도로 작성했으며 AI 생성 artifacts나 STEP 완료 커밋에 넣지 않았다.

## 외부 검증

Agent 종료 뒤 원래 준비 브랜치로 자동 복귀했고 worktree는 clean이었다.
외부 검증을 위해 성공한 실행 브랜치로 전환해 다음을 확인했다.

- Parser pytest: 99 passed (0.24초).
- Parser Ruff: All checks passed.
- Parser Black: 9 files would be left unchanged.
- 저장소 전체 회귀 pytest: 348 passed, 1 skipped (62.00초).
- Review 두 건 approved=true, 모든 Gate completed/attempts=1 확인.
- G2 실행 브랜치의 STEP 완료 커밋 정확히 2개 확인.
- 원래 실패 증거 파일 8개의 SHA-256 동일, 원래 실패 브랜치/HEAD/git status 동일.
- 원격 main과 원래 준비 브랜치 불변, 원격 R1 실행 브랜치 없음 확인.

외부 검증 종료 시점의 개발 HEAD는 실행 브랜치의 b2a7e20이다.
이 보고서는 개발 STEP 커밋 2개 이후 별도의 문서 커밋으로 기록한다.
이전 failed/checkpoint/artifacts/result YAML을 삭제하거나 덮어쓰지 않았다.
main 병합, 실행 결과 원격 Push, 배포, G3/DOC-PARSER-3 착수는 하지 않았다.

## 해석 범위

이번 PASS는 주어진 두 STEP에 대한 실제 생성·독립 검토·테스트·커밋·의존성 누적의 성공을 뜻한다.
임의 작업 전체의 안전성이나 완전한 자동 복구를 보장하지 않는다.
파일 제한 Gate와 실 Git 변경 범위를 확인했으며 별도의 OS 격리 기능을 새로 구현한 것은 아니다.
