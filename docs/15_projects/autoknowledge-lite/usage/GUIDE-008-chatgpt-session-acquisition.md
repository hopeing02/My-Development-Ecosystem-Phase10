# GUIDE-008 ChatGPT 실제 세션 확보

## 권장: Data Export

ChatGPT Settings의 Data Controls에서 Export Data를 요청하고 받은 ZIP을 PC에
다운로드한다. Knowledge Viewer의 `ChatGPT` 메뉴에서 Control API Key와 ZIP을 선택한
뒤 `로컬로 가져오기`를 누른다.

이 방식은 export에 실제로 포함된 여러 conversation을 Session과 Message로 투영하는
기본 경로다. 자동 최근 목록 조회나 ChatGPT login session 재사용은 하지 않는다.

## 보조: Shared Link 1건

ChatGPT 대화에서 공유 링크를 만든 뒤 Knowledge Viewer의 `공개 Shared Link 1건`에
canonical `https://chatgpt.com/share/<conversation-ID>` URL을 입력하고 명시적으로
가져온다.

Shared Link는 공개 snapshot 한 건이며 최근 대화 전체를 가져오지 않는다. 민감한
대화에는 사용하지 않는다. 링크가 삭제되기 전 확보된 raw snapshot은 local Archive에
원본으로 유지된다.

## 결과

- `imported`: 신규 Session projection 완료
- `partial`: raw 원본은 저장됐지만 구조화 데이터 일부 또는 전체를 투영하지 못함
- `duplicate`: 같은 원본과 projection이 이미 존재

어느 경로에서도 누락 title, timestamp, message를 임의 생성하지 않는다.
