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

## 일일 개발계획 (MDE-D1)

```powershell
python tools/mde_daily_plan.py projects
python tools/mde_daily_plan.py plan --project document-parser --step DOC-PARSER-2 --goal "다음 파서 검증 범위 확인" --date 2026-10-30
python tools/mde_daily_plan.py show --date 2026-10-30
```

날짜 생략 시 실행 PC의 오늘 날짜, 예정 시간 생략 시 120분을 사용합니다.
`--minutes`는 15~720분입니다. STEP과 목표는 실제 작업에 맞게 입력합니다.
앱 목록은 `apps/`의 실제 디렉터리에서 읽으며 `sample-project`와 링크 디렉터리는 제외합니다.
프로젝트 메타데이터가 없는 앱과 draft 앱도 목록에 포함합니다.
다른 저장소는 하위 명령 앞에 `--root <저장소>`를 지정합니다.

계획은 `docs/14_operations/DevelopmentLog/YYYY-MM-DD.md`에 저장하며 날짜별 한 건만 허용합니다.
기존 일지에는 `## 오늘 작업` 바로 아래 한 줄만 추가합니다. 기존 내용·줄바꿈·BOM을 보존하며,
해당 제목이 없거나 계획이 이미 있으면 변경을 거부합니다. 조회는 파일을 만들지 않습니다.
이 명령은 계획 기록만 수행합니다. Task 실행 큐에 등록하지 않습니다.

등록 중에는 일지 옆의 `YYYY-MM-DD.md.d1-lock`으로 같은 날짜의 동시 등록을 막습니다.
프로세스 강제 종료 후 잠금이 남으면 실행 중인 등록 프로세스가 없는지 확인하고 잠금 파일만 지운 뒤 재시도합니다.
일지 디렉터리는 Git 추적 경로이므로 비공개 업무정보·기관 내부자료·비밀키를 작성하지 않습니다.

구현과 검증: [CODE-016](../docs/11_code/CODE-016-mde-daily-plan.md),
[TEST-022](../docs/12_test/TEST-022-mde-daily-plan.md).
