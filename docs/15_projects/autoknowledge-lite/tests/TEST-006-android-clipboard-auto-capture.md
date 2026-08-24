# TEST-006 Android 클립보드 자동 수집

- 테스트일: 2026-08-02

## 자동 검증

- Java 단위 테스트: 정규화, 자동·수동 유효성, URL 단독, 민감정보, 해시,
  출처 독립 중복, 서버 실패 대기열을 검증한다.
- Python 통합 테스트: `/v1/share` 메타데이터 보존, Markdown 메타데이터와
  `{timestamp}-{source}-clip-{hash8}.md` 파일명을 검증한다.
- Android 빌드: `testDebugUnitTest assembleDebug`로 검증한다.

## 결과

- Android JUnit: 13개 통과, 실패 0개
- AutoKnowledge Lite Python 회귀: 82개 통과, 실패 0개
- Ruff: 통과
- Black: 통과(`--fast`; 실행 Python 3.11과 프로젝트 target 3.15 차이로 안전 AST 검사는 사용 불가)
- Debug APK: 빌드 성공

## 실제 기기

실제 Android 9 기기는 자동 테스트 환경에 연결되어 있지 않으므로 APK 설치 후
ChatGPT, Codex, 일반 문서, 중복, 서버 장애, 일시 중지 절차를 수동 수행해야 한다.
