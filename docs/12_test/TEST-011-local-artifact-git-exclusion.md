# TEST-011 로컬 생성물 Git 제외 검증

- 상태: Passed
- 작성일: 2026-07-23

## 대상

- 에이전트 작업 영역과 로컬 의존성
- Android 캐시·빌드 결과·로컬 설정
- AutoKnowledge 로컬 데이터와 Vault 복구본
- Python egg-info와 heartbeat
- 미래 Android 실제 소스의 추적 가능성
- 기존 `agent-test-target.txt` 삭제 상태 보존

## 절차

1. `git check-ignore -v`로 각 제외 대상의 규칙을 확인한다.
2. `git status --short`에서 제외 대상이 사라지는지 확인한다.
3. 가상의 `apps/autoknowledge-lite/android/app/src/main/AndroidManifest.xml`이 제외되지 않는지 확인한다.
4. `apps/autoknowledge-lite/vault/`와 첨부·incoming 파일이 삭제되지 않았는지 확인한다.
5. `agent-test-target.txt` 삭제가 그대로 남아 이번 커밋에 포함되지 않는지 확인한다.
6. 문서 구조 테스트와 Ruff를 실행한다.

## 예상 결과

- 로컬 생성물과 복구본은 Git 상태에서 숨겨진다.
- Android 실제 소스 경로는 추적 가능하다.
- 어떤 원본 파일도 삭제·이동되지 않는다.
- 기존 사용자 변경은 이번 작업에서 커밋되지 않는다.

## 실제 결과

```text
Ignore rule representatives checked: 11
Android app/src ignored: false
Attachments preserved: true
Incoming preserved: true
Runtime preserved: true
AutoKnowledge data files preserved: 18
Nested Vault files preserved: 120
agent-test-target.txt deletion preserved and unstaged: true
Full regression tests: 146 passed
ruff check .: passed
ruff format --check .: existing 52 files require formatting
Python files changed by this task: 0
```

결과: Passed

전체 formatter 실패는 이번 변경이 만든 오류가 아니라 기존 저장소의 포맷 부채다. 범위를 벗어난 52개 파일은 자동 수정하지 않았다.
