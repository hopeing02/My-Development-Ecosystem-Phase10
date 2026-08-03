# SDS-008 Capture Viewer와 통합 그래프

- 버전: 1.0
- 상태: Implemented
- 작성일: 2026-08-03

## 구성

```text
Capture 저장·민감정보 검사
  -> Capture matching/query projection
  -> CaptureQueryService
  -> 목록·상세·하위 자료·파일 이력·그래프 API
  -> Knowledge Viewer 동일 Origin gateway
  -> 문서 / Capture 통합 UI
```

기존 Knowledge 문서 Viewer와 그래프는 교체하지 않는다. Capture 화면은 같은 앱의
탐색 모드로 추가하며 `clipboard_item`과 `development_session`을 유형별 상세 화면으로
표시한다. 대화, 명령, 변경 파일, Diff와 테스트는 탭을 열 때 별도 API로 조회한다.

## 조회와 보존

신규 Capture는 저장 Handler의 민감정보 검사가 끝난 payload만 조회 projection에
보존한다. 원본 대화·명령·Diff·테스트는 읽기 전용이며 제목·태그·프로젝트·상위
주제·사용자 메모는 별도 `capture-viewer-metadata-v1.json`에 저장한다. 목록 기본
크기는 30, 최대 100이며 opaque cursor를 사용한다. 명령 출력은 20,000자,
Diff 미리보기는 500KB로 제한하고 앞뒤 문맥만 반환한다.

## 그래프

Capture 그래프는 DOCUMENT, PROJECT, CLIPBOARD_CAPTURE, DEVELOPMENT_SESSION, FILE,
COMMAND, TEST_RESULT 노드와 parent_of, references, belongs_to_project, excerpt_of,
changed_file, executed_command, tested_by Edge를 제공한다. 기본 깊이는 2, 최대 깊이는
4, 최대 노드는 300이다. 기본 화면은 확정 관계와 문서·프로젝트·Capture·파일만
표시하며 후보와 명령·테스트는 사용자가 선택할 때 확장한다.

## 보안 경계

Viewer 서버는 loopback `127.0.0.1:8000` Capture API만 프록시한다. 외부 Capture API
주소는 거부하고 변경 요청에는 기존 Knowledge Command와 같은 Host·Origin·JSON
정책을 적용한다. React는 Capture 원문을 텍스트 노드와 `pre`로만 렌더링하여 raw
HTML, script, event handler와 위험 URL 실행 경로를 제공하지 않는다.

