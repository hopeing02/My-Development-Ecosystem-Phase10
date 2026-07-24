# SDS-004 Obsidian 지식 그래프 자동화

- 버전: 0.3.0
- 상태: Approved

## 목적

AutoKnowledge Lite가 저장한 Markdown을 Obsidian에서 즉시 검색·분류·연결할 수
있도록 속성, 별칭, 정규화 태그와 MOC 링크를 자동 생성한다.

## 기능 요구사항

1. 태그에서 공백과 지원하지 않는 문자를 제거하고 대소문자 중복을 합친다.
2. 최대 세 개의 핵심 태그로 짧은 별칭을 만든다.
3. 저장 폴더에 따라 `type`과 기본 `status`를 결정한다.
4. 제목·요약·태그 키워드로 관련 MOC를 결정한다.
5. 각 노트 끝에 관리 가능한 `## 연결` 구역을 생성한다.
6. 동일 제목 노트는 가장 내용이 긴 노트를 대표 후보로 삼되 삭제하지 않는다.
7. 기존 노트 정리 도구는 기본적으로 변경 미리보기만 제공한다.
8. 정리 도구를 다시 실행했을 때 추가 변경이 없어야 한다.

## MOC

- `_Home`
- `MOC - AutoKnowledge`
- `MOC - 로컬 AI와 스마트홈`
- `MOC - Android 개발`
- `MOC - 생활과 요리`

규칙에 맞는 MOC가 없으면 저장 폴더에 대응하는 일반 MOC를 사용한다.

## 데이터 계약

```yaml
aliases:
  - 짧은 별칭
tags:
  - normalized-tag
type: reference
status: to-review
reviewed: false
topics:
  - "[[MOC - AutoKnowledge]]"
```

## 안전 요구사항

- Vault 밖 경로를 수정하지 않는다.
- `.git`, `.obsidian`, `.trash`, README와 기존 MOC는 콘텐츠 정리 대상에서
  제외한다.
- 기존 frontmatter의 알 수 없는 속성은 보존한다.
- 기존 본문은 `## 연결` 구역 외에는 바꾸지 않는다.
- 적용 전 Git 작업 트리가 깨끗한지 운영 절차에서 확인한다.
