# TEST-024 MDE-D3 실제 TaskStore와 D2 실적 연결

- 일자: 2026-11-01 (Asia/Seoul)
- 대상: CODE-018 / tools/mde_daily_task_link.py
- 사전 조건: Python 3.12.14, 기존 uv.lock 고정 환경, codex/mde-d1-daily-plan / 1dd8142.
- 판정: 구현·격리 통합·회귀 검사 PASS. 실제 운영 결과 연결은 미실행(결과 없음, 사용자 확인).

## 절차와 예상 결과

1. 임시 저장소에 D2 실적을 기록하고 실제 TaskStore.claim/complete/fail로 결과를 준비한다.
2. 미리보기의 프로젝트·STEP·Task ID·상태·메타데이터 연결 구분을 확인한다.
3. 미리보기는 파일과 폴더를 변경하지 않고, 기록은 D3 한 줄 외에 모든 바이트를 보존해야 한다.
4. D2 검증 상태, D1 계획·D2 보완, 원본 Task 및 결과는 변경하지 않아야 한다.
5. 동일 Task 중복 연결·없는 실적·미종료 작업·잘못된 YAML·별칭 충돌·경로 이탈을 거부한다.
6. 저장 실패·동시 기록·조회 후 외부 변경에서 기존 일지와 결과를 보존한다.
7. 현재 실제 저장소의 W1 JSON은 YAML TaskStore 연동 대상이 아님을 확인한다.
8. 전체 pytest·Ruff·Black·관리 문서 검사와 기존 파일 보존을 확인한다.

## 실제 결과

| 항목 | 실제 결과 |
|---|---|
| D3 + D1 + 실제 일지 D2 | 76 passed, 102 subtests passed, 9.03초 |
| D3 전용 검사 | 실제 TaskStore/loader 사용 29개 테스트 모두 통과 |
| 현재 브랜치 전체 pytest | 424 passed, 1 skipped, 151 subtests passed, 61.38초 |
| 전체 Ruff | All checks passed |
| 전체 Black | 255 files unchanged, PASS |
| 관리 문서 검사 두 건 | 각각 PASS |
| 기존 D1/D2/보류 연동·TaskStore·앱·의존성 | 변경 없음 |
| 실제 저장소 W1 JSON 미리보기 | exit 1, YAML Task ID 없음 안내 |
| 같은 W1 JSON --write | exit 1, 일지·작업 파일·디렉터리 변화 없음 |
| 실제 완료/실패 YAML 결과 연결 E2E | 미실행. 사용자가 운영 연동에 쓸 결과가 아직 없다고 확인 |

전체 skip 1건은 기존 W1의 Windows symlink 권한 검사다.
신규 D3의 링크 차단 검사는 실행되어 통과했다. 가짜 mde 모듈로 TaskStore를 대체하지 않았다.
실제 TaskStore가 임시 저장소에 작성한 완료·실패 결과를 연결했으며, 이는 운영 실행 이력이 아니다.

첫 회귀 실행에서는 Windows의 짧은 임시 경로와 실제 경로 표기 차이로 테스트 비교 1건이 실패했다.
테스트 루트를 resolve로 정규화한 뒤 관련 76건과 전체 검사를 통과했다.
기능 변경이나 D1/D2 수정으로 회피하지 않았다.

## 실제 저장소 보존 근거

운영 저장소에는 tasks/README.md와 tasks/pending/DOC-PARSER-1.json만 있고 종료 YAML은 없다.
실제 2026-11-01.md의 mde-core / MDE-D1 실적을 지정해 기존 W1 ID의 미리보기와 --write를 실행했다.
두 실행 모두 오류 종료하며 기존 모든 개발일지 바이트, Task 파일, 상태 폴더 목록이 동일했다.
누락된 pending/processing/completed/failed 디렉터리를 새로 생성하지 않았다.

작업 전부터 있던 실제 2026-11-01.md 파일의 작업 전후 SHA-256:

```text
04be68e2992eb667b6c5be6f71750b02a31f98434919997437242bcc840c3667
```

명령·stdout·stderr·종료 코드는 배포 ZIP의 evidence/live-guard.json에 포함한다.
이 검사는 실제 결과가 없는 상태의 거부·보존 검사이며 성공 연동 E2E가 아니다.
새 Task를 실행하거나 결과를 만들어 운영 성공으로 처리하지 않았다.
원본 일지의 검증 상태를 변경하지 않았고 Git commit/push도 수행하지 않았다.

## 운영 결과가 생긴 뒤

CODE-018의 명령에서 실제 Task ID, D2 기록 날짜·프로젝트·STEP을 지정한다.
미리보기에서 저장된 ID/상태/연결 근거를 확인한 뒤 --write를 사용하고,
재조회·한 줄 외 원본 보존·중복 거부를 확인한다. 그 전에는 D4 운영 검증으로 진행하지 않는다.
