# CODE-022 ChatGPT Shared Link Import Service

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

명시적 Shared Link fetch 결과를 raw Archive에 먼저 저장한 뒤 기존 ChatGPT Adapter와
공통 projection revision 저장소에 연결한다.

## 처리 순서

1. 제한된 Shared Link fetch
2. immutable raw snapshot Archive
3. Archive hash 재검증
4. 구조화 Session 후보 판독
5. 기존 `ChatGPTKnowledgeAdapter`로 original Session/Message 투영
6. 기존 content hash와 projection revision 전략으로 중복 방지
7. warning을 기존 ChatGPT issue 저장소에 별도 기록

구조화 payload 손상 또는 필수 원본 metadata 누락 시 raw snapshot은 유지하고 해당
Session만 failed issue로 격리한다. 누락된 title, timestamp와 message는 생성하지 않는다.

동일 snapshot은 raw와 projection 모두 중복 생성하지 않는다. 동일 conversation의
공유 snapshot이 실제로 변경되면 같은 Session의 다음 immutable revision으로 저장한다.
