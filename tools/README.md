# MDE Tools

저장소 구조, 프로젝트, 표준 문서를 안전하게 생성하는 내장 도구입니다. 모든 도구는 Python 표준 라이브러리만 사용합니다.

## 1. 저장소 초기화

저장소 루트에서 실행합니다.

```bash
python tools/init_repository.py
```

기존 파일은 기본적으로 덮어쓰지 않습니다. 생성기 기본 템플릿을 갱신해야 할 때만 다음을 사용합니다.

```bash
python tools/init_repository.py --force
```

## 2. 새 프로젝트 생성

```bash
python tools/create_project.py --name autoknowledge-lite --type python
python tools/create_project.py --name family-memo --type gas
python tools/create_project.py --name tax-system --type nextjs
python tools/create_project.py --name senior-matching --type generic
```

프로젝트명은 영문 소문자 kebab-case로 씁니다. 예: `senior-matching`.

생성 위치:

```text
apps/<project-name>/
docs/15_projects/<project-name>/
```

프로젝트 상세 문서의 단일 원본은 `docs/15_projects/<project-name>/`입니다.

## 3. 표준 문서 생성

```bash
python tools/create_document.py --category adr --id ADR-002 --title "모노레포-운영-원칙"
python tools/create_document.py --category sds --id SDS-002 --title "검색-모듈" --project autoknowledge-lite
```

지원 문서 유형:

```text
con, gov, std, dev, cmd, prm, arch, sds, adr, qa, code, test, release, ops
```

## 안전 원칙

- 기존 파일은 기본값으로 유지합니다.
- `--force`를 명시했을 때만 같은 경로의 템플릿 파일을 덮어씁니다.
- Windows 예약어인 `CON`을 폴더명으로 만들지 않습니다. 대신 `docs/01_constitution/`을 사용합니다.
