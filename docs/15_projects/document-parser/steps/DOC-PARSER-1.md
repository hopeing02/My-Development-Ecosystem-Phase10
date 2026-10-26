# DOC-PARSER-1 — HWPX 최소 텍스트 추출

- 문서 역할: 개발 명세 원본. 개발 실행 중 수정 금지.
- 정리일: 2026-10-25
- 전제: DOC-PARSER-0 검증 완료. 기존 코드와 공개 API는 수정하지 않는다.
- 실행 요청: `tasks/pending/DOC-PARSER-1.json`

## 목표

ZIP/XML 기반 HWPX에서 구역별 본문 텍스트만 최소 추출하여 `str`로 반환한다.
문단이나 서식 구조를 보존하는 단계는 아니다.

## 기존 코드 재사용

원문 STEP의 공개 API `inspect_document_source(file_path: str | Path)`를 재사용한다.
이 함수는 원문의 `file_path=` 키워드와 `~` 확장을 지원하며, 기존 검증 함수
`validate_source()`와 `DocumentSource`에 검사를 위임하는 최소 호환 함수다.
검증 완료된 `validate_source()`의 본문은 그대로 보존한다.
기존 `validate_source(path=...)` 호출도 계속 지원한다. 두 공개 이름을 패키지에서 제공한다.

이 명세는 이전 validate_source 직접 호출 명세의 실행 완료 후 사용자 요청에 따라 개정했다.
이전 명세·요청·코드·44 passed 결과는 ignored 실행 아카이브와 Git 이력에 보존한다.
개정된 명세를 다시 고정한 뒤 새 W1 실행으로 검증하며 이전 PASS를 새 명세의 결과로 쓰지 않는다.
source.py, __init__.py, test_source.py, test_public_api.py는 새 실행 중 수정하지 않는다.

## 허용 변경 파일

- `apps/document-parser/src/document_parser/hwpx.py`
- `apps/document-parser/tests/test_hwpx.py`

이 명세, 요청 JSON, 기존 DOC-PARSER-0 코드, pyproject.toml, 잠금 파일,
implementation/ 문서 또는 결과 MD/JSON은 Codex의 변경 대상이 아니다.
실행 결과는 외부 W1 실행기가 JSON으로 기록하고, 검증 후 별도 결과 MD에 정리한다.

## 공개 함수와 처리 순서

`document_parser.hwpx.extract_hwpx_text(file_path: str | Path) -> str`

1. 공개 `inspect_document_source(file_path)`를 호출하여 파일 존재·형식 검사를 재사용한다.
   hwpx.py가 validate_source를 직접 호출하거나 입력 검사를 다시 구현하지 않는다.
2. 반환된 `DocumentSource.format`이 `hwpx`가 아니면 `ValueError`로 거부한다.
3. 표준 라이브러리 `zipfile.ZipFile`로 원본을 읽기 전용으로 연다.
4. ZIP 멤버 중 `^Contents/section(\d+)\.xml$`에 정확히 일치하는 이름만 선택한다.
5. 구역 번호를 정수로 정렬한다. 예: section0 → section2 → section10.
6. 각 구역 XML을 `xml.etree.ElementTree`로 읽는다.
7. namespace prefix에 의존하지 않고 local-name이 `t`인 요소의 텍스트를 문서 순서대로 추출한다.
   각 `t`는 `"".join(element.itertext())`에 해당하는 내용을 사용한다.
8. 같은 구역의 텍스트는 구분자 없이 연결하고, 구역 사이에만 `\n` 하나를 넣는다.
   공백을 임의로 strip하거나 정규화하지 않는다. 텍스트가 없는 구역은 빈 문자열이다.
9. 최종 문자열을 반환한다. 압축을 디스크에 풀거나 원본을 수정하지 않는다.

함수·상수는 현재 최소 기능에 필요한 것만 추가한다. 새 런타임 의존성은 추가하지 않는다.

## 오류 계약

- 파일 누락·경로 타입·접근 오류: 공개 입력 API가 위임한 기존 검사의 예외를 그대로 전달.
- 기존 검사에 통과한 비-HWPX 입력: `ValueError`, 메시지에 `Expected HWPX` 포함.
- 잘못된 ZIP 컨테이너: `ValueError`, 메시지에 `Invalid HWPX ZIP` 포함, 원인 예외 연결.
- section XML 부재: `ValueError`, 메시지에 `no section XML` 포함.
- 잘못된 section XML: `ValueError`, 메시지에 `Invalid HWPX section XML`과 멤버 이름 포함, 원인 예외 연결.

## 필수 검증

- DOC-PARSER-0 회귀 검사와 두 공개 API의 키워드·경로 호환 검사 통과.
- HWPX 추출이 inspect_document_source를 실제 호출함을 검사.
- 한 구역의 여러 `t` 연결과 한글·공백 보존.
- ZIP 저장 순서에 관계없는 숫자 순 정렬. section2/section10 경계 포함.
- namespace prefix에 의존하지 않는 텍스트 추출.
- PDF 등 지원되는 비-HWPX 입력 거부, 누락 파일 예외 전달.
- 잘못된 ZIP, section 부재, 잘못된 XML 거부.
- 원본 HWPX가 변경되지 않음.
- Ruff와 Black 통과. 허용 외 변경 없음.

테스트에는 직접 만든 범용 ZIP/XML fixture만 사용한다. 기관 내부 문서는 사용하지 않는다.
테스트 개수나 성공 여부는 미리 확정하지 않고 실제 결과에 기록한다.

```powershell
uv run --project apps/document-parser pytest apps/document-parser/tests/test_source.py apps/document-parser/tests/test_public_api.py apps/document-parser/tests/test_hwpx.py
uv run --project apps/document-parser ruff check apps/document-parser/src/document_parser apps/document-parser/tests
uv run --project apps/document-parser black --check apps/document-parser/src/document_parser apps/document-parser/tests
```

## 실행 환경

저장소 루트에서 `projectPath: "."`인 요청을 실행한다.
uv·Python·Codex CLI와 로그인 및 pytest/Ruff/Black이 준비되어 있어야 한다.
이번 W1 검증은 기존 개발 환경을 `UV_PROJECT_ENVIRONMENT`로 선택하고 `UV_NO_SYNC=1`로
잠금 파일 생성을 피한다. `PYTHONPATH`는 이 프로젝트의 src를 가리킨다.
이 방식의 통과가 새 환경에서의 의존성 설치 검증을 뜻하지는 않는다.

```powershell
uv run python tools/automation/run_codex_single_task.py `
  --request tasks/pending/DOC-PARSER-1.json `
  --result .mde/codex-development/DOC-PARSER-1-result.json
```

## 기록 분리

- STEP MD: 이 파일. 무엇을 만들지 정의하고 실행 중 고정한다.
- JSON: 실행 요청. allowedFiles는 위 Python 파일 두 개뿐이다.
- RESULT JSON: `.mde/codex-development/DOC-PARSER-1-result.json`. W1이 기록하는 기계용 증거.
- RESULT MD: `docs/15_projects/document-parser/results/DOC-PARSER-1-result.md`.
  외부 검증 PASS 후 실제 JSON·Git 차이·코드를 확인하여 기록하며, 개발 전에 생성하지 않는다.

자동 JSON→MD 생성과 Workflow/task_runner 연결은 후속 W2 범위다.

## 이번 STEP에서 제외

문단 경계 보존, 제목·주석 판정, 서식·header.xml 매핑, 표·이미지 파싱,
HWP 바이너리·PDF·OCR, 공통 Core, 검색·색인, AI/RAG/Vector DB/API,
새 프레임워크, 위임·멀티에이전트, 자동수정 반복, mde save, commit/push, 배포.
공공기관 내부 코드·문서·경로·업무규칙과 실제 비밀키는 사용하지 않는다.

## 다음 STEP

DOC-PARSER-2 — HWPX 문단 분리.
검증된 최소 추출 함수를 재작성하지 않고 `hp:p` 단위를 다루는 별도 최소 기능을 검토한다.
이번 실행에서는 시작하지 않는다.
