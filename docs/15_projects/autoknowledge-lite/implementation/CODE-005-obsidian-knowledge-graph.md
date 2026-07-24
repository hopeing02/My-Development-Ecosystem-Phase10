# CODE-005 Obsidian 지식 그래프 자동화

- 작성일: 2026-07-24
- 버전: 0.3.0
- 상태: Complete

## 구현

- `knowledge_graph.py`에 태그 정규화, 별칭, 노트 종류·상태, MOC와 개념
  링크 생성 규칙을 추가했다.
- 기존 Markdown 원문과 알 수 없는 속성을 보존하는 frontmatter 파서와
  반복 실행 가능한 노트 정리기를 구현했다.
- `organize-vault.py`는 기본 미리보기와 명시적 `--apply`를 구분하고 동일
  제목 노트를 삭제하지 않은 채 중복 후보로 표시한다.
- 새 Markdown 생성기는 기존 노트 정리기와 같은 메타데이터·연결 규칙을
  사용한다.
- `obsidian_setup.py`와 `setup-obsidian.py`는 핵심 플러그인, 그래프 필터,
  Templates, Bases와 Dashboard를 기존 사용자 설정을 보존하며 구성한다.

## 운영 적용

- 활성 Vault를 `C:\Users\<user>\Knowledge\Personal-Vault`로 전환했다.
- 내부 보존본과 외부 Vault의 Git HEAD·tree·파일 수를 검증했다.
- 기존 콘텐츠 노트 21개를 보강하고 MOC 10개를 생성했다.
- 개인 Vault 변경을 비공개 `origin/main`에 별도 커밋으로 동기화했다.

실제 절대경로와 개인 원문은 MDE Git 문서에 저장하지 않는다.
