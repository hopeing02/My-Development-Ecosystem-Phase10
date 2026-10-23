# DOC-PARSER-0 — 입력 파일 검증 계약

- 문서 번호 / STEP: DOC-PARSER-0
- TASK: DOC-PARSER-000
- 버전: 0.1.0
- 상태: Review
- 작성일: 2026-10-21
- 작성자: Codex
- 목적: 인터넷·범용판 Python Document Parser의 첫 입력 계약 구현
- 변경 이력: 최초 작성. 허용된 다섯 파일에만 패키지, 계약, 테스트와 기록 추가.

## 확인한 기준과 재사용 검토

저장소 현행 AGENTS.md 및 CON → GOV → STD → DEV → CMD → PRM → ARCH →
SDS → ADR → QA 순서의 기준을 확인했다. 주요 참조는 다음과 같다.

- CON-000/001/005/010/011/012: 재사용, 작은 단위 개발, 문서 동기화와 변경 관리.
- GOV-001/005/008/010/012: 프로젝트 운영, Python 품질과 최소 변경.
- STD-001/004 및 DEV-001: 개발 기록, 테스트, Python 3.12+, uv, 타입 힌트.
- CMD-001/007 및 PRM-001: 명령·요청 범위와 출력 계약.
- ARCH-001 및 ARCH-codex-session-source-analysis: 기존 기능의 경계 확인.
- SDS 공통 색인 및 SDS-002/003: 기존 Knowledge 설계와의 경계 확인.
- ADR-001/002/008/010/021: 모노레포, 구현 기록 위치, 로컬 산출물과 실행 경계.
- QA-001/002/003/004: 테스트, Ruff, Black 및 원본 보존.

`apps`, `packages`, `tests`, `docs`에서 document-parser, DOC-PARSER,
HWP/HWPX 확장자 및 지원 형식 검증을 검색했다. 동일 계약의 검증 완료 코드는
발견되지 않았다. 기존 Knowledge Scanner는 Markdown 본문을 읽고 색인하는
다른 계약이므로 재사용하지 않았다. 기관 내부 자산이나 업무규칙은 사용하지 않았다.

이번 요청의 명시적 경로 제한과 단일 STEP 지시를 적용하여 별도 SDS/ADR/QA,
CHANGELOG, 요청서, 테스트 기록 파일을 추가하지 않고 이 문서에 최소 계약과
검증 기록을 모은다. 기존 MDE 연동이나 공통 구조는 변경하지 않는다.

## 입력·출력 계약

공개 함수는 `document_parser.validate_source(path)`다.

| 항목 | 계약 |
| --- | --- |
| 입력 | 비어 있지 않은 `str` 또는 `os.PathLike[str]` 로컬 경로 |
| 성공 | 불변 `DocumentSource(path: Path, format: DocumentFormat)` |
| `path` | `Path` 변환 결과. 상대경로 유지, resolve/expanduser 수행 안 함 |
| `format` | `hwp`, `hwpx`, `pdf` 중 하나. 점 없는 소문자 문자열 |
| 검사 순서 | 빈 입력 → Path 변환 → stat 및 일반 파일 여부 → 마지막 확장자 |
| 지원 확장자 | `.hwp`, `.hwpx`, `.pdf`. 대소문자 구분 없음 |
| 누락 경로 | `FileNotFoundError` 그대로 전달 |
| 빈 문자열·일반 파일 아님·미지원 확장자 | `ValueError` |
| 경로 타입 오류 | `TypeError` |
| 권한·기타 파일시스템 오류 | `PermissionError` 등 원래 예외 그대로 전달 |

확장자가 지원되어도 디렉터리·특수 파일은 거부한다. 심볼릭 링크는 `stat`의
표준 동작대로 대상을 따라가며 끊어진 링크는 누락 경로로 처리한다. 검증 결과는
호출 시점의 메타데이터이며 이후 파일의 존재를 보장하지 않는다.

확장자만으로 형식을 판별한다. 내용·매직 바이트·인코딩·암호화·문서 유효성은
검사하지 않으며 빈 파일도 허용한다. 입력 파일을 열거나 읽거나 쓰지 않는다.
런타임 의존성은 표준 라이브러리뿐이며 AI API, OCR, 문서 파싱 라이브러리,
Agent/RAG/Vector DB 또는 API 서버를 추가하지 않는다.

## 검증

사전 조건: Python 3.12+, uv 및 개발 의존성 pytest/Ruff/Black.
저장소 루트에서 외부 검증은 다음 명령을 사용한다.

```powershell
uv run --project apps/document-parser pytest apps/document-parser/tests/test_source.py
uv run --project apps/document-parser ruff check apps/document-parser/src/document_parser apps/document-parser/tests/test_source.py
uv run --project apps/document-parser black --check apps/document-parser/src/document_parser apps/document-parser/tests/test_source.py
```

테스트는 메타데이터 대역을 사용하여 문서 파일을 생성·읽기·수정하지 않는다.
지원 형식, 혼합 대소문자, 문자열/Path, 한글·공백·상대경로, 미지원·누락 확장자,
누락 파일의 오류 우선순위, 디렉터리·특수 파일, 권한·OS 오류, 빈 입력과 타입,
결과 불변성 및 파일 열기 금지를 검증한다. 예상 결과는 모든 테스트 통과,
Ruff 오류 0개, Black 변경 불필요다.

실제 결과: pytest **24 passed**, Ruff **All checks passed**, Black **3 files
would be left unchanged**. 세 검사 모두 종료 코드 0이다.
Python 3.12.14와 기존 설치 도구를 사용해 아래 명령으로 실행했다.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
pytest -p no:cacheprovider apps/document-parser/tests/test_source.py
ruff check --no-cache apps/document-parser/src/document_parser apps/document-parser/tests/test_source.py
black --check --no-cache --workers 1 apps/document-parser/src/document_parser apps/document-parser/tests/test_source.py
```

허용 경로 밖의 가상환경·잠금 파일과 ignored 캐시를 생성·수정하지 않도록
Codex 내부 점검에서는 `uv run`의 환경 동기화를 실행하지 않았다.

### W1 외부 실행 결과

W1 실행기가 요청 JSON에 지정된 `uv run --project apps/document-parser` 세 명령을
실제로 실행했다. pytest **24 passed (0.06초)**, Ruff **All checks passed**,
Black **3 files would be left unchanged**, 세 명령 모두 exit 0이다.
`DOC-PARSER-0.result.json`은 `success=true`, `codexExitCode=0`,
`disallowedFiles=[]`, `error=null`이며 변경 파일은 허용된 다섯 파일뿐이다.

GitHub 원본 JSON의 `projectPath`는 이 PC에 없는 예제 경로이므로, ignored 경로의
`DOC-PARSER-0.local.json`에 실제 저장소 경로만 바꿔 실행했다. 원본 JSON은 변경하지 않았다.
uv 실행 파일을 PATH에 추가하고 `UV_PROJECT_ENVIRONMENT`에 기존 Python 3.12.14 검증
환경을 지정했다. `UV_NO_SYNC=1`로 잠금 파일·새 가상환경 생성을 막았으며,
`PYTHONPATH`에 이 프로젝트의 `src`, `BLACK_NUM_WORKERS=1`을 지정했다.
이 결과는 기존 환경에서의 실행 검증이며 새 환경의 패키지 설치 검증은 남아 있다.

## 자체 검토와 범위

입력·출력·예외 계약을 문서화하고 구현과 테스트를 함께 제공했다.
W1 실행 중 커밋·push·mde save·릴리스·배포·위임·자동 수정 루프는 수행하지 않았다.
검증된 다섯 파일의 GitHub 반영과 새 로컬 복제본 갱신은 이후 사용자의 별도 요청에 따라 수행한다.
다음 STEP은 시작하지 않는다.
