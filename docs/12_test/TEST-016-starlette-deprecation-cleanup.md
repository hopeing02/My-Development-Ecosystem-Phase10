# TEST-016 Starlette 경고 제거 및 Capture 호환성

- 일자: 2026-10-19 (Asia/Seoul)
- 기준: `efc23e1` 이후 CODE-010
- 판정: PASS

## 실패 재현

- root Knowledge API 테스트에 -W error::starlette.exceptions.StarletteDeprecationWarning을
  적용하면 httpx2 미설치에 따른 TestClient fallback 경고가 collection error로 발생했다.
- httpx2 추가 후 구형 상태 상수를 유지한 Capture 테스트에서도 import 시 422 별칭
  경고가 collection error로 발생했다.
- 두 원인을 수정한 뒤 동일한 경고 오류 정책에서 테스트가 통과했다.

## 검증 절차와 실제 결과

Python 3.12.14, 기존 lock의 FastAPI 0.140.0 및 Starlette 1.3.1과 테스트 의존성
httpx2 2.14.0을 사용했다. 실행 방법은 CODE-010을 따른다.

| 검증 | 실제 결과 |
|---|---|
| Capture API 대상 | 18 passed, 경고 0개 |
| root 전체 | 216 passed, 경고 0개, 14.41초 |
| 앱 전체 + 메타데이터 7개 | 226 passed, 경고 0개, 5.40초 |
| Black 전체 | 234개 파일 유지, PASS |
| Ruff 전체 | PASS |
| root/app lock --check | 모두 PASS |
| git diff --check | PASS |
| 기존 lock 패키지 버전 비교 | 변경 0개 |
| 앱 기본 runtime dependency export | httpx2·httpcore2 미포함 |

앱 자체 회귀는 새 413 테스트를 포함한 219개다. 메타데이터 7개는 root에도 포함되므로
두 실행의 테스트 개수를 독립 합계로 더하지 않는다. 두 pytest 설정은 Starlette
deprecation을 오류로 처리하며 무시·제외 규칙을 추가하지 않았다.

## 입력·출력 계약 검증

- invalid schema/source/device 등 기존 422 응답 테스트 유지.
- 기본 CaptureError의 기존 422 응답과 error code 유지.
- 1MB 초과 clipboard 입력은 413, CONTENT_TOO_LARGE, payload.content를 반환.
- 초과 본문이 응답에 노출되지 않으며 Markdown을 저장하거나 색인을 호출하지 않음.
- 제품 코드 전체 차이는 상태 상수 이름 3곳 치환과 일치.

## 범위와 제한

AI 없이 테스트 대역·임시 경로를 사용했다. 개인 Vault·운영 Agent·원격 콘텐츠 요청은
사용하지 않았다. Viewer·Android·APK·실기기 회귀는 재실행하지 않았다.
이 유지보수 STEP의 필수 검증 실패나 남은 Starlette 경고는 없다.
