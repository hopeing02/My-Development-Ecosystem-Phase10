# CODE-008 기존 Black 서식 기준 복구

- 일자: 2026-10-19 (Asia/Seoul)
- 기존 검증 완료 기준: `3aa9ac3a5b139da972872058efbc87844b22244b`
- 시작 상태: CODE-007의 환경·버전 수정 반영, Black 67개 불일치로 검증 미통과
- 현재 상태: 이번 유지보수 STEP 검증 PASS. 커밋·push·릴리스는 수행하지 않음.

## 변경 및 이유

기존 Black 필수 검증을 통과하도록 67개 기존 Python 파일의 줄바꿈·빈 줄·괄호 등
서식만 정리했다. 새 기능, API 변경, 함수·클래스 추가, 모듈 이동은 없다.
이전 분석의 제품 로직 변경 금지 범위를 유지한다. 신규 프레임워크도 도입하지 않았다.

최소 수정 범위를 알린 후 다음 순서로 나누어 적용했다.

| 묶음 | 파일 수 | 범위 |
|---|---:|---|
| 도구 | 10 | `mde_cli.py`, `tools/mde_*.py` 호환 래퍼 |
| 실행 모듈 | 37 | 기존 AI·Knowledge·Git·Plugin·Task·Sync·Workflow 모듈 |
| 테스트·앱 | 20 | 기존 core 테스트와 앱 Python 파일 3개 |

변경 전 전체 파일 내용을 작업용 baseline으로 보관하고, Black 제안 결과의 AST 및
주석을 비교한 후 각 묶음에 적용했다. 적용 직후 다시 67개 전부의 AST와 주석 문자열
목록이 변경 전과 동일함을 확인했다. 줄 번호가 달라질 수 있으므로 AST의 위치 속성은
비교하지 않았다. 해시·경로·검증 결과는 검토 산출물의 JSON 명세에 포함한다.

## 기존 코드 재사용 및 신규 파일 필요성

기존 Black 26.10.1, pytest, Ruff, 기존 루트·앱 테스트를 그대로 사용했다.
서식 변경을 그대로 반복하는 신규 테스트는 추가하지 않았다. 검증용 스크립트와 baseline은
저장소 밖 `work/`에만 두었다. 신규 저장소 파일은 이번 STEP의 CODE·TEST 기록 2개다.
전체 수정 파일 내용은 검토용 ZIP으로 제공한다.

## 실행 방법과 검증 결과

저장소 루트에서 다음을 실행한다. 실제 검증에는 Python 3.12.14와 이전 STEP에서
각 frozen lock으로 구성한 저장소 밖 격리 환경을 재사용했다.

```powershell
uv run --frozen --python 3.12 black --check .
uv run --frozen --python 3.12 ruff check .
uv run --frozen --python 3.12 pytest -q -p no:cacheprovider
uv run --frozen --project apps/autoknowledge-lite --extra test --python 3.12 pytest apps/autoknowledge-lite/tests packages/mde-core/tests/test_mde_core_metadata.py -q -p no:cacheprovider
uv lock --check --python 3.12
uv lock --check --project apps/autoknowledge-lite --python 3.12
git diff --check
```

상세 결과는 `../12_test/TEST-014-black-baseline-recovery.md`를 따른다.
전체 Black 234개, Ruff, 루트 215개와 앱·메타데이터 224개 테스트, 두 lock과 diff 검사
모두 통과했다. 초기 CODE-007의 미통과 원인이 해소됐으며 원래 실패 기록은 남겼다.

## 기존 기능 영향 및 제한

기존 Python 함수·클래스·상수·주석을 유지했다. 서식이 바뀐 Python 모듈에는 제품 모듈이
포함되지만 동작 AST는 동일하고 기존 회귀가 통과했다. 원본 Vault·Markdown·Capture
Schema·projection·ChatGPT archive·Android·Viewer 소스·정적 자산은 변경하지 않았다.
AST 및 테스트는 모든 외부 운영 환경의 동작을 증명하지 않으므로 릴리스 승인으로
확대하지 않는다. Viewer·Android·APK·실기기 검증은 재실행하지 않았다.

## 미해결 문제와 다음 STEP

- 추적 중인 `mde_core.egg-info/`가 설치 시 변경되는 문제는 남아 있다.
- 기존 Starlette deprecation 경고는 실패 없이 유지된다.
- 다음 최소 STEP: 생성 egg-info 추적을 정리할 영향 범위를 확인하고, 설치 전후 작업
  트리·패키지 import·CLI를 검증한다. 새 제품 기능은 아직 선정하지 않았다.

## Git 검토

이전 STEP 변경과 이번 서식 변경은 아직 커밋하지 않았다. 검토 ZIP의
`COMMIT-COMMANDS.ps1`은 검증된 변경 파일 목록을 명시적으로 stage하고 커밋하는
명령 예시다. 자동 실행하지 않았으며 push 명령도 포함하지 않는다.
