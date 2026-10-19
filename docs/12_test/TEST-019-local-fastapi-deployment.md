# TEST-019 로컬 FastAPI 배포·리뷰 gate 검증

- 일자: 2026-10-19 (Asia/Seoul)
- 기준: `3193b41` 이후 CODE-013 및 ADR-020
- 판정: 자동 검증 PASS, 실 AI live 전체 검증은 미수행

## 환경과 방법

Python 3.12.14, 기존 frozen 환경 및 신규 psutil 7.2.2를 사용했다.
임시 Git 저장소·bare 원격·실제 FastAPI/Uvicorn 프로세스·HTTP 요청으로 검증했다.
테스트 fixture는 자신이 시작한 서비스만 종료한다. 운영 서비스·개인 Vault는 사용하지 않았다.

## 핵심 검증

- 신규 배포·현재 상태·커밋 snapshot 분리·정상 이전 버전 유지·rollback·stop.
- import 실패·health 404·제한 시간·state write 실패에서 후보 종료와 이전 상태 보존.
- app/health/name/python/timeout/path 입력 검증, dirty worktree 및 동시 배포 거부.
- 없는 배포 status 조회의 무변경, 이전 버전 없는 rollback 거부, 손상 state 보존.
- 생성 시각 또는 command가 일치하지 않는 PID는 종료하지 않음.
- Windows MAX_PATH를 넘는 tracked 경로의 snapshot 추출. 실제 monorepo 배포에서 발견한 오류를 확장 경로로 수정.
- CLI 호출 프로세스가 종료돼도 서비스 유지, 별도 CLI status/stop 정상.
- 실제 공개 workflow CLI: 입력 JSON → mock 생성 → pytest → 커밋 → 선택적 push 생략 →
  실제 배포 → version=two HTTP 응답. source worktree clean.
- 기존 fix-loop 통합을 확장해 실제 실패·수정·pytest·커밋·bare push 뒤 배포·answer=42 확인.
- 리뷰 입력은 실제 생성 코드. true만 적용하며 false/null/string은 적용 이전에 중단.
- HTTP provider는 boolean verdict를 metadata로 보존하고 누락·문자열은 오류.

초기 통합에서 Task 패키지 초기화의 import 순환을 발견해 잠금을 실행 시점에
재사용하도록 수정했다. 기존 Task/Plugin 패키지 초기화 구조는 바꾸지 않았다.
첫 전체 회귀의 기존 Workflow 4개 목록 기대값도 신규 명시적 변형을 포함하도록 보완했다.

## 최종 결과

| 검증 | 결과 |
|---|---|
| root 전체 | 266 passed, 경고 0개 (Windows 긴 경로 회귀 포함) |
| 앱·메타데이터 전체 | 226 passed, 경고 0개, 5.41초 |
| Black 전체 | 236개 파일 유지, PASS |
| Ruff 전체 | PASS |
| root/app lock 검사 | 모두 PASS |
| 두 docs check | 모두 PASS |
| diff 검사 | PASS |
| core wheel 빌드 | PASS, deployment.py 및 feature-local.yaml 포함 |

검증 명령:

```powershell
uv run --frozen --python 3.12 pytest -q -p no:cacheprovider
uv run --frozen --project apps/autoknowledge-lite --extra test --python 3.12 pytest apps/autoknowledge-lite/tests packages/mde-core/tests/test_mde_core_metadata.py -q -p no:cacheprovider
uv run --frozen --python 3.12 black --check .
uv run --frozen --python 3.12 ruff check .
uv lock --check --python 3.12
uv lock --check --project apps/autoknowledge-lite --python 3.12
uv run mde docs check
uv run mde docs check --target knowledge-guide
git diff --check
uv build --wheel --project packages/mde-core
```

## 범위와 남은 검증

Mock AI와 전송 대역을 사용했으므로 실제 AI 작성 품질·인증·비용·실패 수정의 live
검증을 완료했다고 주장하지 않는다. 현재 PC의 기존 AutoKnowledge 앱 실배포 결과는
커밋 후 최종 작업 보고서에 기록한다. 로컬 배포에는 데이터 migration·고정 URL·
재부팅 자동 시작이 포함되지 않는다. Android·Viewer·실기기 회귀도 재실행하지 않았다.
