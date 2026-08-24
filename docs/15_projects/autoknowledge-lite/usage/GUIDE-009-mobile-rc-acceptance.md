# GUIDE-009 모바일 RC 설치 승인

## 사전 조건

- 휴대폰과 PC에서 Tailscale 연결
- Android 8.0(API 26) 이상
- 기존 앱이 설치되어 있으면 삭제하지 않음

## 1. APK 다운로드

휴대폰 브라우저에서 다음 주소를 연다.

- AutoKnowledge-Lite: `http://100.75.235.67:8000/downloads/autoknowledge-lite.apk`
- MDE Knowledge Viewer: `http://100.75.235.67:8765/downloads/mde-knowledge-viewer.apk`

예상 파일명:

- `autoknowledge-lite-v0.2.4.apk`
- `mde-knowledge-viewer-v0.1.0.apk`

## 2. 비파괴 업데이트 설치

기존 앱이 있으면 Android 설치 화면에서 `업데이트`를 선택한다. 서명 충돌 또는 호환되지 않는 패키지 오류가 나오면 앱을 삭제하지 말고 오류를 기록한다.

USB 디버깅과 ADB를 사용하는 경우:

```powershell
adb install -r apps/autoknowledge-lite/android/app/build/outputs/apk/debug/app-debug.apk
adb install -r apps/knowledge-viewer/android/app/build/outputs/apk/debug/app-debug.apk
```

`-r`은 기존 앱 데이터와 설정을 유지하는 업데이트 설치다.

## 3. AutoKnowledge-Lite 승인

1. 앱을 열어 기존 서버 주소와 설정이 유지되는지 확인한다.
2. 서버 주소를 `http://100.75.235.67:8000`으로 확인한다.
3. PC 연결 상태 확인이 성공하는지 확인한다.
4. 최근 실제 Codex 세션 목록을 조회한다.
5. 세션 한 건을 선택해 연결·추가 동기화·FINALIZE를 실행한다.
6. ChatGPT 공개 Shared Link 한 건 또는 Data Export ZIP을 가져온다.
7. 실패 시 원본 입력이 삭제되지 않고 warning으로 표시되는지 확인한다.

## 4. Knowledge Viewer 승인

1. MDE Knowledge Viewer 앱을 열고 `http://100.75.235.67:8765`에 연결한다.
2. 기존 Markdown 문서가 표시되는지 확인한다.
3. Capture에서 Codex Session과 변경 파일을 확인한다.
4. ChatGPT에서 Session, Task, Activity와 원본 Message 이동을 확인한다.
5. Timeline에서 ChatGPT와 Codex 작업이 시간순으로 함께 표시되는지 확인한다.
6. Graph에서 Session, Task, Activity, File 관계를 확인한다.

## 5. 승인 기록

다음 항목이 모두 통과해야 RC를 `Ready`로 변경한다.

- [ ] AutoKnowledge-Lite 업데이트 설치 성공
- [ ] Knowledge Viewer 업데이트 설치 성공
- [ ] 기존 모바일 설정과 대기 데이터 유지
- [ ] `:8000` PC 연결 성공
- [ ] Codex 실제 Session 조회·저장 성공
- [ ] ChatGPT 실제 Session 가져오기 성공
- [ ] ChatGPT Task/Activity와 원본 Message 이동 성공
- [ ] Project Timeline 표시 성공
- [ ] Knowledge Graph 표시 성공
- [ ] 두 앱 재실행 후 설정 유지

기기 모델, Android 버전, 설치 시각과 실패 메시지를 함께 기록한다.
