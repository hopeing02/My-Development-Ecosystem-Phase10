# CMD-003 MDE Knowledge Plugin 사용자 가이드

- 버전: 1.0.0
- 상태: Active
- 작성일: 2026-07-22
- 대상 버전: MDE Knowledge Plugin v1.2.0

## 1. 실행 위치와 기본 확인

PowerShell에서 MDE 저장소로 이동한다.

```powershell
cd C:\My-Development-Ecosystem-Phase10
```

등록된 Source 목록과 `mde-docs` 상세 정보를 확인한다.

```powershell
uv run mde knowledge list
uv run mde knowledge show mde-docs
```

Source 이름 대신 ID도 사용할 수 있다.

```powershell
uv run mde knowledge show ks-001
```

## 2. MDE 문서 검색

Source를 지정하지 않은 기본 검색은 `development`, `project`, `shared`만 포함하고 `personal`, `work`는 제외한다.

```powershell
uv run mde knowledge search "workflow"
uv run mde knowledge search "workflow" --source mde-docs
uv run mde knowledge search "workflow" --source mde-docs --limit 10
uv run mde knowledge search "개발 표준" --source mde-docs
uv run mde knowledge search "배포" --category development
```

검색 결과에는 Source와 Category, 제목, 상대경로, 제한된 길이의 문맥이 표시된다. 문서 전체는 출력하지 않는다.

```text
[mde-docs | development] MDE Workflow Engine
07_architecture/ARCH-003-workflow-engine.md

...workflow task를 순서대로 실행하고...
```

## 3. 태그 검색

YAML frontmatter 태그와 본문 태그를 검색할 수 있다.

```yaml
---
tags:
  - architecture
  - mde
---
```

```markdown
#architecture
#mde/workflow
```

```powershell
uv run mde knowledge search --tag architecture --source mde-docs
uv run mde knowledge search "workflow" --tag architecture --source mde-docs
```

코드 블록 내부의 `#`는 가능한 범위에서 태그로 인식하지 않는다.

## 4. 문서 변경 후 증분 스캔

`docs` 아래 Markdown 문서를 작성하거나 수정한 후 다시 스캔한다.

```powershell
uv run mde knowledge scan mde-docs
```

```text
Knowledge source: mde-docs
Category: development
Added: 2
Updated: 1
Deleted: 0
Unchanged: 93
Errors: 0
```

- `Added`: 새로 발견된 문서
- `Updated`: 내용이 변경된 문서
- `Deleted`: 원본에서 사라져 색인에서 제거된 문서
- `Unchanged`: 변경되지 않아 다시 저장하지 않은 문서
- `Errors`: 인코딩 또는 읽기 오류가 발생한 문서

`Deleted`는 원본 파일을 삭제한다는 의미가 아니다. 이미 사라진 원본 파일에 해당하는 SQLite 색인만 제거한다.

## 5. 새 Source 등록

개발 문서:

```powershell
uv run mde knowledge add "D:\Projects\Another-Project\docs" `
  --name another-project `
  --category development
```

프로젝트 문서:

```powershell
uv run mde knowledge add "D:\Projects\Project-Alpha\docs" `
  --name project-alpha `
  --category project
```

개인 Obsidian Vault:

```powershell
uv run mde knowledge add "D:\Knowledge\Personal-Vault" `
  --name personal `
  --category personal `
  --type obsidian
```

업무 Markdown:

```powershell
uv run mde knowledge add "D:\Knowledge\Work-Vault" `
  --name work `
  --category work
```

공백, 한글, 다른 드라이브가 포함된 경로도 등록할 수 있다.

```powershell
uv run mde knowledge add "D:\개인 자료\나의 지식 저장소" `
  --name my-vault `
  --category personal `
  --type obsidian
```

등록 시 원본 파일을 MDE 저장소로 복사하지 않는다. 정규화된 원본 폴더 경로만 사용자 전역 Registry에 저장한다.

## 6. Source Category 기준

| Category | 용도 | Sensitive 기본값 | Agent 접근 기본값 |
|---|---|---:|---:|
| `development` | MDE 또는 공통 개발 문서 | false | true |
| `project` | 특정 프로젝트 문서 | false | true |
| `shared` | 공유 프로젝트 문서 | false | true |
| `personal` | 개인 Markdown·Obsidian | true | false |
| `work` | 업무 자료 | true | false |

개인 자료는 `personal`, 회사 자료는 `work`로 등록한다.

## 7. 여러 Source 스캔

민감하지 않은 모든 Source를 스캔한다.

```powershell
uv run mde knowledge scan --all
```

기본 포함 Category는 `development`, `project`, `shared`이고 기본 제외 Category는 `personal`, `work`이다.

민감 Source까지 포함하려면 명시적인 옵션이 필요하다.

```powershell
uv run mde knowledge scan --all --include-sensitive
uv run mde knowledge scan --category project
uv run mde knowledge scan --category personal --include-sensitive
```

특정 민감 Source를 이름으로 지정한 경우에는 별도 옵션 없이 스캔할 수 있다.

```powershell
uv run mde knowledge scan personal
```

## 8. 개인·업무 자료 검색

민감 Source는 이름을 명시하여 검색한다.

```powershell
uv run mde knowledge search "학원 일정" --source personal
uv run mde knowledge search "지출 결의" --source work
```

민감 결과에는 `SENSITIVE` 표시가 붙는다.

```text
[personal | personal | SENSITIVE] 아이들 학원 일정
가족/아이들-학원-일정.md
```

모든 Source에서 검색하려면 `--all`과 `--include-sensitive`를 함께 사용한다.

```powershell
uv run mde knowledge search "자동화" --all --include-sensitive
```

`--all`만 사용하면 민감 Source는 포함되지 않는다.

## 9. Obsidian 링크와 백링크

다음 Obsidian 문법을 인식한다.

```markdown
[[가족 일정]]
[[가족 일정|일정 보기]]
[[가족 일정#학원]]
![[시간표.png]]
```

Markdown 내부 링크와 외부 링크도 인식한다.

```markdown
[개발 표준](../04_development/DEV-001-development-standard.md)
[외부 사이트](https://example.com)
```

백링크는 동일 Source 안에서 조회한다.

```powershell
uv run mde knowledge backlinks "가족 일정" --source personal
uv run mde knowledge backlinks "DEV-001-development-standard" --source mde-docs
uv run mde knowledge backlinks "가족 일정" --source personal --limit 20
```

Source 경계를 넘는 링크는 자동 연결하지 않는다. 이미지, PDF, HWP, Office 첨부파일은 링크로만 인식하고 본문은 색인하지 않는다.

## 10. Source 비활성화와 재활성화

```powershell
uv run mde knowledge update personal --enabled false
uv run mde knowledge update personal --enabled true
uv run mde knowledge show personal
```

비활성화된 Source는 기본 검색에서 제외되며 직접 스캔할 수 없다.

## 11. Agent 접근 설정

일반 Source의 Agent 접근을 변경할 수 있다.

```powershell
uv run mde knowledge update project-alpha --agent-access false
uv run mde knowledge update project-alpha --agent-access true
```

민감 Source에서 접근 설정을 활성화하려면 확인 옵션이 필요하다.

```powershell
uv run mde knowledge update personal `
  --agent-access true `
  --confirm-sensitive-access
```

v1.2의 Agent 검색 인터페이스는 안전을 위해 민감 Source를 계속 제외한다. 검색 결과를 Agent 프롬프트에 자동 삽입하는 기능도 없다. 이 설정은 향후 안전한 Agent 연동을 위한 Source 정책 정보다.

## 12. Source 등록 해제

```powershell
uv run mde knowledge remove personal
```

제거되는 항목:

- Source 등록 정보
- 해당 Source의 SQLite 문서·태그·링크 색인
- 해당 Source의 스캔 기록

보존되는 항목:

- 원본 폴더와 Markdown 문서
- `.obsidian` 설정
- 첨부파일
- Git 저장소

완료 메시지:

```text
Knowledge source removed: personal
Original files preserved.
```

## 13. 사용자 데이터 저장 위치

기본 위치:

```text
C:\Users\<사용자>\.mde\knowledge\
├── sources.json
├── knowledge.db
└── logs\
    └── knowledge-YYYY-MM-DD.log
```

- `sources.json`: 등록된 Source와 원본 경로
- `knowledge.db`: 문서 본문과 검색 색인
- `logs`: Source 관리 및 스캔 감사 로그

SQLite에는 검색을 위해 원문 전체가 저장될 수 있으며 v1.2에서는 암호화하지 않는다.

현재 PowerShell 세션에서 저장 기준 경로를 변경하려면 `MDE_DATA_HOME`을 설정한다.

```powershell
$env:MDE_DATA_HOME = "D:\MDE-User-Data"
uv run mde knowledge list
```

이 경우 Knowledge 데이터는 `D:\MDE-User-Data\knowledge\`에 저장된다. 기존 사용자 데이터는 자동으로 이동하지 않는다.

## 14. 감사 로그 확인

```powershell
Get-Content "$HOME\.mde\knowledge\logs\knowledge-$(Get-Date -Format yyyy-MM-dd).log"
Get-ChildItem "$HOME\.mde\knowledge\logs"
```

기록하는 대표 이벤트:

- `source.added`
- `source.updated`
- `source.removed`
- `scan.started`
- `scan.completed`
- `scan.failed`

검색어, 검색 결과, 문서 본문, Source 절대경로는 기록하지 않는다. 검색 명령 자체도 감사 로그에 검색어나 결과를 남기지 않는다.

감사 로그는 오늘을 포함한 최근 30일을 보관한다. 만료 로그는 다음 Source 관리 또는 스캔 감사 이벤트가 발생할 때 안전한 파일명 규칙에 따라 자동 정리한다.

## 15. 기본 제외 폴더와 인코딩

`*.md`를 재귀 탐색하지만 다음 폴더는 제외한다.

```text
.git
.obsidian
.mde
node_modules
.venv
venv
__pycache__
.pytest_cache
.ruff_cache
dist
build
temp
tmp
trash
휴지통
```

Markdown 이외 첨부파일은 본문 색인 대상이 아니다. 인코딩은 UTF-8과 UTF-8 BOM을 지원하며, 한 파일의 인코딩 오류가 전체 Source 스캔을 중단시키지 않는다.

## 16. 추천 일상 사용 흐름

개발 문서 작업 후:

```powershell
uv run mde knowledge scan mde-docs
uv run mde knowledge search "변경한 주제" --source mde-docs
```

여러 개발·프로젝트 Source 갱신:

```powershell
uv run mde knowledge scan --all
```

개인 Vault 작업 후:

```powershell
uv run mde knowledge scan personal
uv run mde knowledge search "찾을 내용" --source personal
```

가장 자주 사용하는 핵심 명령:

```powershell
uv run mde knowledge list
uv run mde knowledge scan mde-docs
uv run mde knowledge search "검색어" --source mde-docs
uv run mde knowledge show mde-docs
```

간단한 명령 목록은 `CMD-002-knowledge-plugin.md`를 참고한다.
