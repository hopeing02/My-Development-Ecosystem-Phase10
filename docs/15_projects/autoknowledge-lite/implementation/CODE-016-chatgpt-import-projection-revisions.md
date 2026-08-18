# CODE-016 ChatGPT Import Projection Revisions

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

보관된 ChatGPT 원본 Archive를 기존 `ChatGPTKnowledgeAdapter`에 연결하고, Session별
읽기 전용 projection revision과 warning 격리를 로컬에 저장한다. API와 Viewer에는
아직 연결하지 않는다.

## 구현

- Source discovery → Raw Archive → archived Source 재검증 → Adapter projection 흐름 추가
- Archive discovery, manifest와 보관본 SHA-256 일치 검증
- Session ID hash 기반 projection 디렉터리와 연속 revision JSON 저장
- 원본 Session content hash와 Adapter version이 같으면 중복 revision으로 처리
- 동일 Session 원본이 변경되면 기존 revision을 보존하고 다음 revision 추가
- 각 revision에 import ID, 원본 member/index, source content hash와 Adapter version 기록
- 개별 Adapter 실패를 다른 Session과 분리하고 Import issue로 반환
- source/Adapter warning을 `warnings/chatgpt/{import_id}.json`에 별도 보존

## 무결성

- 원본 Archive와 원본 Session dict를 수정하지 않음
- 손상된 Session 때문에 유효 Session projection을 중단하지 않음
- 기존 revision이 손상되거나 revision sequence가 끊기면 덮어쓰지 않음
- warning report가 기존 내용과 충돌하면 덮어쓰지 않음
- projection과 warning은 raw Archive와 별도 계층에 저장

## 호환성

기존 ChatGPT Clip, Markdown, Capture API, Codex 수집, Knowledge Graph와 Viewer는
수정하지 않았다.
