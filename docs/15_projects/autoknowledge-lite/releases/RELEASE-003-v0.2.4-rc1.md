# RELEASE-003 AutoKnowledge Lite v0.2.4 RC1

- 후보 확정일: 2026-08-20
- 상태: Internal Release Candidate — 물리 Android 기기 승인 대기
- 대상: AutoKnowledge-Lite `0.2.4`와 MDE Knowledge Viewer Android `0.1.0`

## 주요 기능

- 기존 일반 Markdown, ChatGPT/Codex Clip, Session Markdown 호환 유지
- ChatGPT Data Export ZIP과 사용자가 제출한 공개 Shared Link 가져오기
- 원본 Session/Message 보존과 공통 Knowledge Model 읽기 전용 투영
- Session의 Task/Activity 분석 및 원본 Message 이동
- ChatGPT Session/Task/Activity Knowledge Graph 연결
- 관계 검색과 ChatGPT/Codex Project Timeline
- 모바일 AutoKnowledge-Lite와 Knowledge Viewer APK 직접 다운로드

## 호환성과 보안

- 기존 Markdown 포맷과 저장 경로를 변경하지 않는다.
- 원본 archive, Markdown, projection revision을 AI 분석으로 수정하지 않는다.
- ChatGPT 계정의 비공개 최근 세션 목록에 직접 접근하지 않는다.
- Control API Key는 브라우저 메모리에서만 사용한다.
- APK 업데이트 설치 실패 시 앱을 삭제하지 않는다. 삭제하면 Android 앱 로컬 설정과 대기 데이터가 제거될 수 있다.

## RC APK

### AutoKnowledge-Lite

- package: `dev.mde.autoknowledge`
- versionCode: `5`
- versionName: `0.2.4`
- minSdk: `26`, targetSdk: `34`
- SHA-256: `B5235A81639C692344F7CCD4705F7BD5E7ECC1FAA26E514AA46796A557F875B7`
- 다운로드: `http://100.75.235.67:8000/downloads/autoknowledge-lite.apk`

### MDE Knowledge Viewer

- package: `dev.mde.knowledgeviewer`
- versionCode: `1`
- versionName: `0.1.0`
- minSdk: `26`, targetSdk: `34`
- SHA-256: `E3045F8BC0B9FE6D3C71AF06B561290C6B70FBC9BCBDC5E7830748459C37946D`
- 다운로드: `http://100.75.235.67:8765/downloads/mde-knowledge-viewer.apk`

두 APK는 APK Signature Scheme v2 검증을 통과했고 localhost 및 Tailscale 다운로드 파일이 로컬 빌드 산출물과 일치했다.

## 자동화 승인

- AutoKnowledge-Lite Python: 216 passed, 1 skipped
- MDE Knowledge: 68 passed
- Knowledge Viewer: 42 passed
- AutoKnowledge Android: 24 passed
- Knowledge Viewer Android: 3 passed
- 두 debug APK: BUILD SUCCESSFUL

## 남은 승인 조건

연결된 Android 기기가 없어 실제 설치·실행은 자동 검증하지 못했다. `GUIDE-009-mobile-rc-acceptance.md`의 물리 기기 항목을 모두 통과하면 상태를 `Ready`로 변경한다.

## 알려진 제한

- ChatGPT 실제 세션은 Data Export ZIP 또는 사용자가 생성한 공개 Shared Link로만 확보한다.
- 현재 로컬 데이터에는 독립 ChatGPT/Codex/general Clip 레코드가 없지만 기존 포맷과 API 회귀는 통과했다.
- RC APK는 내부 사용을 위한 debug 서명 빌드다.
