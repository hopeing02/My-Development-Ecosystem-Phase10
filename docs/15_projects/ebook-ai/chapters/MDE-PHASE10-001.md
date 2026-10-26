# 1장. 기존 함수를 고치지 않고 새 API를 제공하기

> 편집 및 사용자 승인 전: 검증 대기

STEP: EBOOK-AI-03 · TASK: EBOOKPHASE10CHAPTER001

기준 저장소: `hopeing02/My-Development-Ecosystem-Phase10`

기준 커밋: `4f23c9828c531ce4b4c335ed843cd03b1cb88769`

## 목표

이미 동작하는 함수를 유지하면서, 다른 이름과 키워드로도 같은 검사를 사용할 수 있게 만든 실제 변경을 읽어 본다. 여기서 API는 다른 Python 코드가 가져와 호출하는 공개 함수를 뜻한다.

이번 장은 새 기능을 개발하는 지침이 아니라, 저장소에 반영된 공개 API 호환 변경을 설명하는 초안이다. 코드를 읽은 뒤 개인 PC에서 직접 만든 가상 파일로 두 함수의 결과를 비교한다.

## 실제 문제

기존 패키지에는 `validate_source(path=...)`가 있었다. 반면 결과 기록에 따르면 원문 STEP이 요구한 호출은 `inspect_document_source(file_path=...)`였고, 홈 디렉터리를 뜻하는 `~`의 확장도 필요했다.

Python에서는 함수 이름뿐 아니라 키워드 매개변수 이름도 호출 규칙의 일부다. `path=`를 받는 함수에 `file_path=`를 넘기면 같은 뜻으로 알아서 바뀌지 않는다. 기존 함수를 새 이름으로 바꾸거나 매개변수를 바꾸면 이미 `validate_source(path=...)`를 사용하던 코드에 영향을 줄 수 있다.

그래서 이 변경은 기존 함수를 보존하고, 필요한 호출 규칙을 받아 기존 검사에 연결하는 작은 호환 함수를 추가했다. 같은 파일 검사 알고리즘을 두 벌로 관리할 필요도 없다.

## 변경 전

커밋의 부모 버전에서 패키지가 공개하던 이름은 `DocumentFormat`, `DocumentSource`, `validate_source`였다. 기존 함수의 시그니처는 다음과 같다.

```python
def validate_source(path: str | PathLike[str]) -> DocumentSource:
```

`validate_source(path=...)`는 경로를 `Path`로 바꾼 뒤 `stat()`으로 일반 파일인지 확인하고, 마지막 확장자를 소문자로 바꾸어 `.hwp`, `.hwpx`, `.pdf` 중 하나인지 검사한다. 성공하면 경로와 형식을 담은 `DocumentSource`를 반환한다. 예를 들어 `.HWPX`의 `format`은 점 없는 소문자 문자열 `hwpx`다.

이 함수는 `expanduser()`를 수행하지 않는다. 따라서 `~/sample.pdf`를 주어도 홈 디렉터리 경로로 직접 바꾸어 주지 않는다. 또한 `validate_source(file_path=...)`는 기존 시그니처에 없는 키워드 호출이다.

## 변경 후

`inspect_document_source(file_path: str | Path) -> DocumentSource`가 추가되었다. `__init__.py`는 새 함수를 import하고 `__all__`에 넣어 기존 이름들과 함께 공개한다.

| 호출 | 사용하는 키워드 | 홈 경로 확장 |
| --- | --- | --- |
| `validate_source(path=...)` | `path=` | 함수 자체에서는 수행하지 않음 |
| `inspect_document_source(file_path=...)` | `file_path=` | 기존 검사에 넘기기 전에 `expanduser()` 수행 |

두 함수 모두 위치 인자로도 경로를 받을 수 있다. 다만 `validate_source(file_path=...)`나 `inspect_document_source(path=...)`처럼 키워드를 서로 바꾸어 쓰면 `TypeError`가 발생한다.

새 함수는 먼저 `Path(file_path).expanduser()`로 입력 경로를 준비한다. 이렇게 해야 `~`가 실제 홈 디렉터리 경로로 바뀐 상태에서 기존 함수가 파일을 찾을 수 있다. 이어서 검증 완료된 `validate_source`를 호출하여 일반 파일과 확장자 검사를 재사용한다. 단순히 같은 함수에 이름만 하나 더 붙이는 별칭으로는 `file_path=`와 홈 경로 확장이라는 두 요구를 충족할 수 없다.

지정 커밋의 diff에서 `validate_source` 본문은 바뀌지 않았다. 결과 문서에도 변경 전후 AST, 즉 코드의 구문 구조가 같았다고 기록되어 있다.

## 운영 코드

다음은 실제 저장소 `apps/document-parser/src/document_parser/source.py`에 있는 새 호환 함수의 원문 전체다. 기준 커밋은 `4f23c9828c531ce4b4c335ed843cd03b1cb88769`이며, 시그니처와 본문을 수정하지 않고 발췌했다. 아래 코드는 당시 검증 기록이 있는 운영 코드다.

```python
def inspect_document_source(file_path: str | Path) -> DocumentSource:
    """Expose the original STEP API while reusing verified source validation."""
    return validate_source(Path(file_path).expanduser())
```

`Path`, `DocumentSource`, `validate_source`는 같은 파일에 이미 정의되거나 import되어 있다. 이 발췌만 별도 파일에 붙여 실행하는 대신, 다음 실습처럼 기존 패키지에서 함수를 가져온다.

새 함수도 파일 내용을 읽거나 ZIP을 파싱하지 않는다. 검사의 범위는 경로가 가리키는 대상이 일반 파일인지, 지원하는 확장자인지까지다. 반환값은 문서 본문의 유효성을 보증하지 않는다.

## 따라 하기

Python 3.12 이상이 준비된 개인 PC에서 저장소 루트를 현재 디렉터리로 삼는다. 아래는 PowerShell에서 한 번에 실행할 수 있는 예제다. 기존 실행 기록처럼 `PYTHONPATH`가 `apps/document-parser/src`를 가리키게 하여 저장소의 패키지를 직접 가져온다. `python -B`는 import 과정의 바이트코드 파일 생성을 막는다.

실습 자료는 임시 디렉터리에 직접 만드는 공개 가능한 가상 파일 `sample.HWPX` 하나다. **빈 HWPX 파일은 유효한 압축 컨테이너가 아니다. 이 예제는 경로와 확장자 검증만 확인할 수 있으며, HWPX 본문 추출 실습이 아니다.** 기관 문서나 실제 업무자료는 필요하지 않다.

```powershell
$env:PYTHONPATH = (Resolve-Path 'apps/document-parser/src').Path
@'
from pathlib import Path
from tempfile import TemporaryDirectory

from document_parser import inspect_document_source, validate_source

with TemporaryDirectory() as temporary_directory:
    file_path = Path(temporary_directory) / "sample.HWPX"
    file_path.touch()

    existing_result = validate_source(path=file_path)
    new_result = inspect_document_source(file_path=file_path)

    assert existing_result.format == "hwpx"
    assert new_result.format == "hwpx"
    assert existing_result.format == new_result.format
    print(existing_result.format, new_result.format)
'@ | python -B -
```

정상 종료하면 다음 두 단어가 출력된다.

```text
hwpx hwpx
```

`touch()`가 빈 일반 파일을 만들고 두 함수가 같은 경로를 검사한다. 확장자의 대문자는 소문자로 처리되므로 두 결과가 모두 `hwpx`가 된다. `with` 블록을 벗어나면 `TemporaryDirectory`가 실습 파일과 임시 디렉터리를 정리한다. 이 코드는 설명을 위해 작성한 실습 예제이며 저장소의 운영 코드 원문이나 과거 검증 완료 코드로 분류하지 않는다.

## 검증

`docs/15_projects/document-parser/results/DOC-PARSER-0-api-result.md`의 2026-10-25 기록은 다음과 같다.

| 검사 | 원문 기록의 결과 |
| --- | --- |
| pytest | `pytest 27 passed` — 기존 입력 검사 24개와 공개 API 검사 3개 |
| Ruff | Ruff PASS |
| Black | Black PASS |
| 기존 함수 보존 | `validate_source` 변경 전후 AST 동일 PASS |

**위 결과는 과거 저장소 검증 기록이며 이번 집필 실행에서 재검증한 결과가 아님.** 당시 기록을 현재의 검사 결과나 출판 승인으로 해석해서는 안 된다.

`test_public_api.py`의 세 검사는 두 키워드 호출의 결과 일치, 새 함수가 기존 검사를 실제 호출하는지, `~` 경로 확장을 다룬다. `test_source.py`는 지원 확장자, 누락 파일, 일반 파일이 아닌 대상, 파일시스템 오류 등을 검사하며 파일 내용을 열지 않는지도 확인한다.

이번 집필에서는 지정 커밋의 `git show`와 출처 파일을 대조한다. 원고 구조, 발췌 일치, 실습 Python 문법과 Git 공백 오류를 검사하며 pytest·Ruff·Black 및 임시 파일 실습은 재실행하지 않는다.

## 오류와 주의

- `ModuleNotFoundError`가 나면 저장소 루트에서 실행했는지와 `PYTHONPATH`가 프로젝트의 `src`를 가리키는지 확인한다. pytest의 `pythonpath` 설정이 일반 `python` 실행에도 자동 적용되는 것은 아니다.
- 키워드 오류가 나면 기존 함수는 `path=`, 새 함수는 `file_path=`인지 확인한다. 함수 이름과 키워드는 한 쌍으로 읽는다.
- 없는 파일은 기존 검사에서 `FileNotFoundError`, 일반 파일이 아니거나 지원하지 않는 확장자이면 `ValueError`가 발생한다. `PermissionError` 같은 파일시스템 오류도 성공으로 숨기지 않고 전달된다.
- 새 함수는 `Path` 변환과 홈 경로 확장을 먼저 수행한다. 따라서 모든 잘못된 입력의 예외 메시지까지 기존 함수와 동일하다고 확대 해석하지 않는다. 예를 들어 기존 함수는 빈 문자열을 직접 거부하지만, 새 함수에서는 먼저 `Path("")`가 현재 디렉터리를 나타내게 된다.
- `format == "hwpx"`는 확장자 판별 결과다. 파일이 올바른 ZIP인지, XML이 있는지, 본문을 읽을 수 있는지는 확인하지 않는다. `.pdf`나 `.hwp`도 내용의 유효성을 검사하지 않는다.
- 상대경로는 실행 위치의 영향을 받으며, 기존 검사는 경로를 `resolve()`로 절대경로화하지 않는다. 심볼릭 링크는 `stat()`의 동작에 따라 대상을 검사한다. 반환 결과는 검사 시점의 상태이므로 이후 파일이 계속 존재한다는 보장도 아니다.
- `DOC-PARSER-1.md`는 HWPX 텍스트 추출을 위한 후속 명세다. 명세가 있다는 이유로 구현이 완료되었거나 PASS했다고 소개하지 않는다. 이 장에서는 후속 예정 범위를 식별하는 용도로만 참조한다.

## 출처

아래 링크는 모두 공개 기준 저장소의 지정 커밋에 고정되어 있다. 집필 시 로컬 clean checkout에서 해당 파일을 실제로 읽었고, 필수 출처 파일과 기준 커밋 사이에 차이가 없음을 확인했다.

- [지정 커밋의 실제 변경 전후](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/commit/4f23c9828c531ce4b4c335ed843cd03b1cb88769): 저장소 루트에서 `git show 4f23c9828c531ce4b4c335ed843cd03b1cb88769`으로 확인했다.
- [`apps/document-parser/src/document_parser/source.py`](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/blob/4f23c9828c531ce4b4c335ed843cd03b1cb88769/apps/document-parser/src/document_parser/source.py): 기존 검사와 새 호환 함수 원문.
- [`apps/document-parser/src/document_parser/__init__.py`](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/blob/4f23c9828c531ce4b4c335ed843cd03b1cb88769/apps/document-parser/src/document_parser/__init__.py): 두 함수의 공개 export.
- [`apps/document-parser/tests/test_public_api.py`](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/blob/4f23c9828c531ce4b4c335ed843cd03b1cb88769/apps/document-parser/tests/test_public_api.py): 키워드 호환, 검사 재사용, 홈 경로 확장 검사.
- [`apps/document-parser/tests/test_source.py`](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/blob/4f23c9828c531ce4b4c335ed843cd03b1cb88769/apps/document-parser/tests/test_source.py): 기존 입력 검사와 내용 미접근 검사.
- [`docs/15_projects/document-parser/results/DOC-PARSER-0-api-result.md`](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/blob/4f23c9828c531ce4b4c335ed843cd03b1cb88769/docs/15_projects/document-parser/results/DOC-PARSER-0-api-result.md): 변경 이유와 과거 27 passed·Ruff·Black 결과.
- [`AGENTS.md`](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/blob/4f23c9828c531ce4b4c335ed843cd03b1cb88769/AGENTS.md): 검증 코드 재사용과 STEP 범위 원칙.
- [`docs/04_development/DEV-001-development-standard.md`](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/blob/4f23c9828c531ce4b4c335ed843cd03b1cb88769/docs/04_development/DEV-001-development-standard.md): 개발 순서와 Python·UTF-8·검사 기준.
- [`apps/document-parser/pyproject.toml`](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/blob/4f23c9828c531ce4b4c335ed843cd03b1cb88769/apps/document-parser/pyproject.toml): Python 3.12 이상, `src` 패키지 배치, pytest의 경로 설정.
- [`docs/15_projects/document-parser/implementation/DOC-PARSER-0.md`](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/blob/4f23c9828c531ce4b4c335ed843cd03b1cb88769/docs/15_projects/document-parser/implementation/DOC-PARSER-0.md): 기존 입력 계약과 저장소 루트·`PYTHONPATH` 실행 방식.
- [`docs/15_projects/document-parser/steps/DOC-PARSER-1.md`](https://github.com/hopeing02/My-Development-Ecosystem-Phase10/blob/4f23c9828c531ce4b4c335ed843cd03b1cb88769/docs/15_projects/document-parser/steps/DOC-PARSER-1.md): 후속 HWPX 추출 명세의 존재와 범위만 확인.

## 검증 상태

편집 및 사용자 승인 전: **검증 대기**.

원고는 실제 변경과 과거 검사 기록을 바탕으로 작성한 초안이다. 이번 문서 검사가 통과하더라도 실습 재현, 편집 검토 및 사용자 출판 승인을 대신하지 않는다. 출판 승인 상태는 자동으로 PASS 처리하지 않는다.
