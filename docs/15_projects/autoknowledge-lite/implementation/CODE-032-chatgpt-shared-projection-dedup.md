# CODE-032 ChatGPT Shared Projection 중복 판정 보완

## 목표

ChatGPT 공개 Shared Link가 요청마다 가변 snapshot 필드를 반환하더라도 실제 공통
Session/Message/Task 투영이 동일하면 신규 revision으로 잘못 집계하지 않는다.

## 구현

- 원본 snapshot archive와 source content hash 보존 방식을 변경하지 않는다.
- 동일 source content hash는 기존 방식대로 중복 처리한다.
- source content hash가 달라도 최신 adapter version의 공통 projection이 완전히 같으면
  동일 Session revision으로 처리한다.
- 실제 메시지나 공통 모델 metadata가 달라지면 기존처럼 다음 revision을 생성한다.
- 기존에 생성된 revision은 삭제하거나 migration하지 않는다.

## 검증

- 동일 snapshot 재가져오기
- 서로 다른 snapshot hash와 동일 projection 재가져오기
- 동일 Session의 실제 메시지 변경에 따른 신규 revision 생성
- 손상 원본 격리 및 원본 불변 회귀 테스트

