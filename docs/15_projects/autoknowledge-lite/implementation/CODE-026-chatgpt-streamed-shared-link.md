# CODE-026 ChatGPT streamed Shared Link 호환

- 작성일: 2026-08-19
- 버전: 0.2.4
- 상태: Complete

## 장애 원인

공개 Shared Link의 HTTPS 요청과 raw snapshot 보존은 성공했지만 최신 ChatGPT 공유
페이지가 대화를 중첩 JSON이 아닌 streamed loader reference table로 전달했다. 기존
reader는 table 자체만 순회해 `conversation_id`와 `mapping`의 참조를 복원하지 못했고
`CHATGPT_SHARED_CONVERSATION_MISSING` warning으로 격리했다.

## 구현

- JSON string으로 전달된 streamed loader table을 읽기 전용으로 식별
- `_N` key/value reference를 실제 object/list 관계로 복원
- 음수 sentinel은 확보되지 않은 값으로 유지하고 임의 데이터를 생성하지 않음
- table 크기와 기존 전체 traversal 제한 유지
- 순환 참조는 container identity로 한 번만 순회
- 기존 중첩 JSON, raw snapshot, archive manifest 포맷은 변경하지 않음
- 원본 snapshot을 재작성하거나 삭제하지 않음

## 실제 원본 확인

실패 당시 보존된 snapshot을 수정 없이 다시 읽어 Session 1개, mapping node 19개,
Message 9개를 `source=original`로 투영했다. 운영 서버 재시작 후 같은 공개 링크를
재처리해 발견 1, 신규 1, 실패 0을 확인했다.
