# CODE-009 생성 패키지 메타데이터 Git 추적 정리

- 일자: 2026-10-19 (Asia/Seoul)
- 시작 커밋: `d4883fca329c9c7c1c6804e0c5b825666908a164`
- 상태: 구현 및 STEP 검증 PASS
- 적용 기준: 기존 Accepted `ADR-010-local-artifact-git-exclusion.md`

## 문제와 최소 수정

기존 `.gitignore`는 `*.egg-info/`를 제외하지만 이미 등록된 생성 파일 6개에는
적용되지 않았다. 루트 패키지를 설치하면 이 파일들이 갱신되어 불필요한 변경이 생겼다.
새 정책을 만들지 않고 ADR-010을 적용한다.

`mde_core.egg-info/`의 PKG-INFO, SOURCES.txt, dependency_links.txt,
entry_points.txt, requires.txt, top_level.txt만 `git rm --cached --`로 추적 해제했다.
로컬 파일은 삭제·이동하지 않았다. 추적 해제 직후 6개 파일의 SHA-256이 전과 같음을
확인했다. 이후 재설치로 생성 메타데이터가 갱신되더라도 Git 상태에는 나타나지 않는다.

## 기존 코드 재사용 및 신규 코드 필요성

기존 ignore 규칙, 빌드 설정과 `test_mde_core_metadata.py`를 재사용했다.
해당 테스트에 `git ls-files`와 `git check-ignore`를 사용한 회귀검사 1개만 추가했다.
이는 실제 추적 문제를 검출하고 재발을 방지하기 위해 필요하다. 테스트는 등록 상태를
확인할 뿐 파일이나 Git index를 변경하지 않는다. 업무 함수·클래스·모듈은 추가하지
않았다. 신규 문서는 사용자 요구에 따른 CODE·TEST 기록 2개다.

## 실행 및 검증

최소 재현과 수정 명령:

```powershell
git ls-files -- '*.egg-info/*'
git rm --cached -- mde_core.egg-info
git check-ignore -v mde_core.egg-info/PKG-INFO
uv sync --frozen --python 3.12 --reinstall-package mde-core
uv sync --frozen --project apps/autoknowledge-lite --extra test --python 3.12 --reinstall-package mde-core
git status --short
uv run --frozen --python 3.12 pytest -q -p no:cacheprovider
uv run --frozen --project apps/autoknowledge-lite --extra test --python 3.12 pytest apps/autoknowledge-lite/tests packages/mde-core/tests/test_mde_core_metadata.py -q -p no:cacheprovider
uv run --frozen --python 3.12 black --check .
uv run --frozen --python 3.12 ruff check .
git diff --check
git diff --cached --check
```

실제 검증에는 Python 3.12.14와 저장된 lock에 기반한 저장소 밖 격리 환경을 사용했다.
상세 결과는 `../12_test/TEST-015-generated-metadata-tracking.md`를 참조한다.

## 기존 기능 영향

제품 코드·API·CLI·Workflow·Agent·DB·Vault·원본 데이터·Android·Viewer에는 변경이
없다. 패키지 메타데이터는 기존 빌드 설정에서 재생성한다. 두 설치 경로 모두 실제
재설치 후 버전 0.10.0, import와 CLI가 정상이고 Git 변경이 추가되지 않았다.

## Git 반영과 다음 STEP

기존 환경·서식 복구 변경은 GitHub의 main `d4883fc`로 반영됐다. 로컬 Git HTTPS
인증은 미설정이어서 연결된 GitHub 인증으로 동일 트리의 커밋을 생성하고 main을
fast-forward 갱신했다. 콘텐츠 트리 SHA는 로컬 검증 결과와 정확히 같았다.
이번 수정 역시 별도 커밋과 fast-forward 원격 반영 대상으로 검증했다. force push나
기존 이력 삭제는 하지 않는다.

예상 커밋 메시지: `chore: stop tracking generated package metadata`.
원격 반영 결과와 최종 SHA는 작업 결과 보고서에 남긴다.

남은 문제는 기존 Starlette deprecation 경고다. 다음 최소 후보는 경고 원인 분석이며
제품 기능 STEP이나 새 프레임워크 도입은 아직 선정하지 않았다. Viewer·Android·실기기
회귀는 이번 Git 추적 정리의 범위에 포함하지 않았다.
