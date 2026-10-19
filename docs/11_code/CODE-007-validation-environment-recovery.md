# CODE-007 개발 재개 검증 환경 및 패키지 정합성 복구

- 일자: 2026-10-19 (Asia/Seoul)
- 기준 커밋: `3aa9ac3a5b139da972872058efbc87844b22244b`
- 상태: 구현 반영, 전체 검증 미통과. STEP 완료·save·commit·push 대상 아님.

> 위 상태는 최초 검증 시점의 기록이다. 2026-10-19 후속 서식 정리로 전체 검증이
> 통과했다. 현재 판정은 `CODE-008-black-baseline-recovery.md`와
> `../12_test/TEST-014-black-baseline-recovery.md`를 따른다. 아래 초기 결과는 보존한다.

## 목표와 최소 수정

기존 STEP 10과 2026-08-24 실기기 승인 이후 개발을 재개하기 위해 누락된 검증 도구와
패키지 버전 불일치를 수정한다. 새 제품 기능이나 STEP 11 명세를 추가하지 않는다.

- 루트 `pyproject.toml`: 개발 의존성에 `black==26.10.1` 추가.
- 루트 `uv.lock`: Black과 필요한 전이 의존성 고정.
- `packages/mde-core/pyproject.toml`: 0.6.0을 기존 런타임 버전 0.10.0과 일치시킴.
- `apps/autoknowledge-lite/uv.lock`: 로컬 mde-core 버전을 0.10.0으로 동기화.
- 기존 `packages/mde-core/tests/test_mde_core_metadata.py`: 설정·lock·런타임 버전,
  저장소 밖의 실제 설치 메타데이터, save 필수 도구 선언·lock 검증 추가.

lock 파일 형식 revision은 사용한 uv에 의해 3에서 5로 갱신됐다. 기존 제3자 패키지의
버전을 일괄 업그레이드하지 않았다.

## 기존 코드 재사용과 신규 코드 필요성

기존 `mde.__version__`, 패키지 설정, lock 파일과 메타데이터 테스트를 재사용했다.
새 제품 함수·클래스·소스 파일은 만들지 않았다. 새 테스트 3개는 실제로 재현한
버전 불일치와 도구 누락의 회귀 방지를 위해 기존 테스트 파일에 추가했다.
별도 Python 프로세스의 `-I`와 저장소 밖 임시 cwd를 사용해 저장소의 egg-info가
설치된 distribution 버전을 가리는 현상을 방지한다.
신규 Markdown 파일은 사용자 요구에 따른 구현·검증 기록이다.

## 실행 및 검증 방법

저장소 루트에서 Python 3.12를 명시한다. 실제 검증에는 Python 3.12.14와 저장소 밖
격리 환경을 사용했다. 외부 AI API와 개인 Vault를 사용하지 않았다.

```powershell
uv sync --frozen --python 3.12
uv run --frozen --python 3.12 pytest -q
uv run --frozen --python 3.12 ruff check .
uv run --frozen --python 3.12 black --check packages/mde-core/tests/test_mde_core_metadata.py
uv run --frozen --python 3.12 black --check .
uv lock --check --python 3.12
uv lock --check --project apps/autoknowledge-lite --python 3.12
uv run --frozen --project apps/autoknowledge-lite --extra test --python 3.12 pytest apps/autoknowledge-lite/tests packages/mde-core/tests/test_mde_core_metadata.py -q
```

실제 pytest 실행에는 캐시 생성 방지를 위해 `-p no:cacheprovider`를 추가했다.
결과는 `../12_test/TEST-013-validation-environment-recovery.md`에 기록한다.

## 기존 기능 영향

업무 로직·CLI 명령 처리·API·Workflow·Agent·Vault·Capture Schema·원본 archive·
projection·Viewer·Android 코드는 수정하지 않았다. mde-core의 API 버전을 올린 것이
아니라 기존 0.10.0 런타임과 설치 메타데이터를 맞춘 것이다.
`save()`도 변경하지 않았다. 기존 save는 `black .`으로 전체 파일을 수정할 수 있으므로
현재 작업에서는 실행하지 않았다.

## 미해결 문제와 다음 STEP

- 전체 Black 검사: 기존 67개 파일 서식 불일치로 실패. 수정 전에는 68개였으며,
  이번에 수정한 메타데이터 테스트 파일만 정리해 67개가 남았다.
- 대규모 기존 파일 수정을 피하기 위해 나머지 파일을 자동 포맷하지 않았다.
- Git에 이미 등록된 `mde_core.egg-info/`는 설치 시 변경된다. 이번 빌드의 부수 변경은
  원복했으며, 생성 파일 추적 정리는 별도 검토 대상으로 남긴다.
- 기존 Starlette deprecation 경고 유지.
- Viewer·Android·실기기 검증은 이번 STEP에서 재실행하지 않았다.

다음 최소 STEP은 기존 Black 불일치를 변경 영향이 작은 범위부터 나누어 정리하고
전체 검증을 다시 수행하는 것이다. 검사를 생략하거나 예외 설정으로 숨기지 않는다.
필수 검증 전에는 커밋·push·새 기능 개발로 넘어가지 않는다.

## Git 명령

현재 게이트가 실패했으므로 실행 가능한 save·commit·push 명령을 제시하지 않는다.
차후 전체 필수 검증이 통과한 뒤 검토된 파일만 커밋한다.
