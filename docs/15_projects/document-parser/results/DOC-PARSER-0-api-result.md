# DOC-PARSER-0 공개 API 호환 보완 결과

## 결과

PASS — 2026-10-25, 실제 C 드라이브 작업 폴더에서 검증했다.

## 변경 파일

- source.py: inspect_document_source(file_path)를 추가했다.
- __init__.py: 원문 공개 이름과 기존 validate_source를 함께 export한다.
- tests/test_public_api.py: 키워드 호환·기존 함수 재사용·홈 경로 확장을 검사한다.

## 기존 코드 재사용

validate_source 본문은 변경 전후 AST가 동일하다. 기존 입력 검사 24개를 그대로 유지했다.
새 공개 함수는 Path 변환·expanduser 후 검증 완료 함수에 위임한다.
이름만 별칭으로 제공하면 원문의 file_path=와 ~ 계약을 충족하지 못하므로 공개 호환 함수가 필요하다.
단순 편의용 helper나 검증 알고리즘의 복제는 추가하지 않았다.

## 실제 검사

- pytest: **27 passed**, 0.05초 (기존 24 + 공개 API 3).
- Ruff: PASS.
- Black: PASS (새 테스트 파일의 import 형식을 정리한 뒤 최종 통과).
- validate_source AST 동일: PASS.
- 기존 pyproject.toml, test_source.py와 Codex CLI 연결부 변경 없음.

## 기존 기능 영향

validate_source(path=...)를 사용하는 기존 코드는 그대로 동작한다.
inspect_document_source(file_path=...)는 원문의 명세 이름·키워드·~ 확장을 제공한다.
기관 내부 데이터나 새 의존성은 사용하지 않았다.

## 다음 검증

DOC-PARSER-1의 HWPX 추출이 공개 inspect_document_source를 사용하도록 명세·요청을 개정하고
새 W1 실행으로 검사한다. 기존 명세에서 통과한 44개 결과는 아카이브로 분리한다.
W2 자동화나 문단 분리는 시작하지 않는다.
