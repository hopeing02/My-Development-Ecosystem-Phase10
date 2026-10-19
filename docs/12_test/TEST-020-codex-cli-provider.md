# TEST-020 실제 Codex CLI 자동 개발 검증

- 일자: 2026-10-19
- 대상: CODE-014 / ADR-021
- 환경: Python 3.12.14, codex-cli 0.163.0-alpha.10.2, 기존 ChatGPT 로그인
- 판정: 이 STEP의 필수 검증 PASS

## 자동 회귀

루트 `pytest -q -p no:cacheprovider`: **281 passed**, 경고 0개, 31.20초.
앱·메타데이터: **226 passed**, 경고 0개, 4.75초.
Black 전체 238개 유지·Ruff 전체·두 docs check·diff 검사 PASS.
CLI subprocess 대역으로 stdin·shell 미사용·read-only·schema·모델 override·명시적
verdict·실행 오류·설치 누락·timeout·자식 종료·응답 누락/오류를 검증했다.
실제 실패 프로세스 출력이 fix context에 포함되고 현재 소스가 전달되는 것을 검증했다.
경로 이탈·없는 파일·잘못된 목록·파일 개수 제한도 거부한다.

## 실제 CLI acceptance 1: 생성부터 배포

별도 임시 저장소에 기존 /health와 /double 테스트를 커밋했다.
공개 `workflow run feature-local --runtime --inputs ... --max-fix-attempts 1` 호출:

1. 실제 codex generate가 service.py 전체 내용을 artifact로 반환.
2. 별도 실제 codex review approved=true.
3. MDE apply → 실제 pytest PASS → commit → push 생략 → FastAPI 배포.
4. GET /double?value=-7 → HTTP 200, `{"result": -14}` 확인.

## 실제 CLI acceptance 2: 실패 수정과 downstream

기존 구현에 `value + 2` 회귀를 별도 커밋해 실제 pytest를 실패시켰다.
기존 fix-loop에 codex Provider, 현재 service.py/test_service.py, 실제 실패 로그를 전달했다.
`test(failed) → ai.fix → apply → retest(PASS) → save → push → deploy` 완료.
HTTP 응답 -14, 로컬 HEAD·임시 bare main·배포 commit 모두
`758ad5dbe369f02b61803fd7528f92c3a928c9a2` 일치를 확인했다.
검증 서비스 종료 및 임시 저장소 clean 상태도 확인했다.

두 acceptance 모두 AI 대역을 사용하지 않았다. 개인 데이터와 기존 실행 서비스는 건드리지 않았다.
초기 acceptance CLI를 잘못된 작업 디렉터리에서 실행한 시도는 context 파일 누락으로
적용 전에 중단됐고, 올바른 임시 저장소에서 재실행하여 성공했다.
첫 AI 목록 회귀의 기대값도 신규 codex 항목을 포함하도록 갱신했다.

## 한계

실제 GitHub push 무인 인증·대규모 기능·Android·Viewer·실기기·DB migration은 검증하지 않았다.
GitHub connector 인증은 shell Git 인증과 다르므로 live push는 임시 bare 원격으로 검증했다.
기존 운영 FastAPI는 이전 배포 커밋으로 정상 유지하며 이번 CLI 변경을 자동 재배포하지 않는다.

## 재실행 명령

```powershell
uv run --frozen --python 3.12 pytest -q -p no:cacheprovider
uv run --frozen --project apps/autoknowledge-lite --extra test --python 3.12 pytest apps/autoknowledge-lite/tests packages/mde-core/tests/test_mde_core_metadata.py -q -p no:cacheprovider
uv run --frozen --python 3.12 black --check .
uv run --frozen --python 3.12 ruff check .
uv run mde docs check
uv run mde docs check --target knowledge-guide
git diff --check
```
