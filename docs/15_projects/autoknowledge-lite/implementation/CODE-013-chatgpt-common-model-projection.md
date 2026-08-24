# CODE-013 ChatGPT 공통 모델 Projection

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

기존 ChatGPT Clip 저장과 Markdown 포맷을 변경하지 않고, 확보된 ChatGPT 원본을
공통 `Session`과 `Message` 모델로 읽기 전용 투영한다.

## 구현

- ChatGPT export의 `id`, `title`, 생성·수정 시각과 현재 대화 분기의 Message를 사용
- 기존 `chatgpt/clipboard_item` Capture Envelope을 단일 Message Session으로 호환 투영
- 기존 `captureId`, 원본 Message ID와 `contentHash`를 우선 재사용
- 제목 없는 기존 Clip은 새 제목을 만들지 않고 `captureId`를 표시값으로 재사용하며 warning 기록
- content hash가 없는 export Message는 hash 필드를 생성하지 않고 비워 둠
- 중복 판별에 기존 Capture 정규화와 SHA-256 전략을 재사용
- 원문 content의 공백과 내용을 변경하지 않음
- ChatGPT export의 `Session`과 `Message`에는 `source=original` 및 원본 reference 기록
- Clip의 단일 Message Session 호환 투영에는 `source=derived`, `derived_by=rule`과 원본 Capture reference 기록
- 요약, Task, AI metadata 같은 파생 정보는 생성하지 않음

## 실패 경계

안전한 Session 구성에 필요한 ID, 제목, 생성·수정 시각이 없으면 명시적 Adapter
오류를 반환한다. 개별 Message의 ID, role, content, timestamp 또는 hash가 손상된
경우에는 해당 Message 또는 선택 필드만 제외하고 warning을 반환한다. Adapter는
입력 dict와 Capture payload를 수정하지 않으며 기존 저장 파이프라인에서 호출되지
않으므로 투영 실패가 원본 Clip 저장 실패로 이어지지 않는다.

## 호환성

기존 Capture API, Markdown renderer, Obsidian 저장 구조, Codex Adapter, Knowledge
Graph와 Viewer는 수정하지 않았다.
