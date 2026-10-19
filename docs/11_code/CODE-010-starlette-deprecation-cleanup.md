# CODE-010 Starlette 경고 원인 제거

- 일자: 2026-10-19 (Asia/Seoul)
- 시작 커밋: `efc23e138ae09ebdf2b02f2bb37598c2623267bc`
- 상태: 구현 및 해당 STEP 검증 PASS

## 원인과 최소 수정

경고를 직접 Capture 코드와 테스트 의존성으로 나누어 확인했다.

1. CaptureError 기본 상태와 validation 응답의 HTTP_422_UNPROCESSABLE_ENTITY를
   HTTP_422_UNPROCESSABLE_CONTENT로 교체했다.
2. 1MB 초과 본문의 HTTP_413_REQUEST_ENTITY_TOO_LARGE를
   HTTP_413_CONTENT_TOO_LARGE로 교체했다.
3. 고정된 Starlette 1.3.1 TestClient는 httpx2가 없으면 httpx로 대체하며 경고한다.
   httpx2==2.14.0을 루트 dev, mde-core test extra, 앱 test extra에만 추가했다.
4. 두 pytest 설정에서 StarletteDeprecationWarning을 오류로 처리한다. 경고를
   숨기거나 예외 목록을 추가하지 않았다.

런타임 Python 변경은 정확히 상태 상수 이름 3곳뿐임을 원문 비교로 확인했다.
상수 값은 기존 422·413과 같고 응답 JSON·검증 순서·경로·크기 제한은 유지한다.

## 기존 자산 재사용과 신규 코드 필요성

기존 capture_api.py, 테스트의 _client/_request/RecordingIndexer, 상태 검증 테스트와
pytest 설정을 재사용했다. 기존 Capture 테스트 파일에 1MB 초과 응답·원문 비노출·
Vault 미저장·색인 미호출 검사 1개를 추가해 미검증 413 경로를 확인했다.
새 업무 함수·클래스·모듈은 없다. 신규 저장소 파일은 CODE·TEST 기록 2개다.

httpx2는 기존 TestClient가 요구하는 테스트용 HTTP 클라이언트다. Agent/RAG/Vector DB/
오케스트레이션 프레임워크가 아니다. 제품 콘텐츠 수집과 AI SDK가 사용하는 기존
httpx를 바꾸지 않았다. 앱 기본 runtime dependency export에 httpx2·httpcore2가
포함되지 않는 것도 확인했다. 두 lock 모두 기존 패키지 버전을 그대로 유지했다.

lock에 추가된 패키지는 httpx2, httpcore2, truststore와 플랫폼 조건부
httpx2-jsfetch다. 검증한 Windows 테스트 환경에는 앞의 3개가 설치됐다.

## 실행 및 검증

```powershell
uv sync --frozen --python 3.12
uv run --frozen --python 3.12 pytest -q -p no:cacheprovider
uv run --frozen --project apps/autoknowledge-lite --extra test --python 3.12 pytest apps/autoknowledge-lite/tests packages/mde-core/tests/test_mde_core_metadata.py -q -p no:cacheprovider
uv run --frozen --python 3.12 black --check .
uv run --frozen --python 3.12 ruff check .
uv lock --check --python 3.12
uv lock --check --project apps/autoknowledge-lite --python 3.12
git diff --check
```

실제 검증에는 Python 3.12.14와 각 frozen lock으로 동기화한 격리 환경을 사용했다.
상세 결과는 `../12_test/TEST-016-starlette-deprecation-cleanup.md`에 기록했다.

## 기존 기능 영향과 미해결 문제

기존 HTTP 413·422 및 error code·field 계약이 유지된다. 전체 루트·앱 회귀는 경고 없이
통과했다. Vault·기존 Markdown·archive·projection·Capture Schema·Workflow·Agent·
Android·Viewer에는 변경이 없다. 외부 AI API를 호출하지 않았다.
Viewer·Android·APK·실기기 검증은 이번 Python 경고 수정 STEP에서 재실행하지 않았다.
이 결과를 모바일 RC 재승인이나 새 제품 릴리스로 해석하지 않는다.

이번 STEP에서 확인한 미해결 실패는 없다. 다음 최소 후보는 기존 미구현 CLI
generate/inbox의 실제 동작과 문서 계약을 대조하는 분석이다. 기능 구현은 그 분석을
거쳐 최소 범위를 정한 뒤 진행한다.

## Git 반영

기존 커밋·푸시 요청에 따라 검증 통과 변경만 별도 커밋 대상으로 한다.
메시지: `fix: resolve Starlette deprecations without changing Capture responses`.
기존 Git HTTPS 인증 대신 연결된 GitHub 인증을 사용하며 트리 동일성·원격 SHA를
확인한다. force push는 사용하지 않는다. 최종 SHA는 작업 결과 보고서에 기록한다.

## 근거

- [고정된 Starlette 1.3.1의 TestClient](https://github.com/Kludex/starlette/blob/1.3.1/starlette/testclient.py)
- [고정된 Starlette 1.3.1의 상태 상수](https://github.com/Kludex/starlette/blob/1.3.1/starlette/status.py)
- [httpx2 2.14.0 배포 정보](https://pypi.org/project/httpx2/2.14.0/)

위 공식 소스와 설치된 패키지를 대조했다. 최신 패키지를 일괄 업그레이드하지 않았다.
