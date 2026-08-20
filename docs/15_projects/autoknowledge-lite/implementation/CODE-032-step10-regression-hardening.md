# CODE-032 Step 10 회귀 안정화

## 변경 목적

Step 10 전체 회귀 실행에서 Capture 대화·파일·명령·테스트 탭을 연속 검증하는 기존 복합 UI 테스트가 병렬 부하 시 기본 5초 제한을 간헐적으로 초과했다.

## 변경

- `CaptureWorkspace.test.tsx`의 해당 복합 테스트에만 10초 제한을 명시했다.
- 제품 코드, API, Markdown 포맷, 저장 구조, Graph 데이터는 변경하지 않았다.
- 단독 실행 시간은 약 1.4초, 전체 병렬 실행에서는 약 4.3~5.4초였다.

## Android 환경 검증

- AutoKnowledge-Lite Android는 기존 `local.properties` SDK 경로를 사용했다.
- Knowledge Viewer Android는 빌드 프로세스에만 `ANDROID_HOME`을 지정했다.
- 저장소 또는 사용자 원본 데이터에는 환경 설정을 기록하지 않았다.

## 결과

전체 Viewer 회귀가 반복 실행에서 안정적으로 완료되고, 두 Android 앱의 단위 테스트·debug APK 빌드·서명·다운로드 일치성까지 확인할 수 있게 됐다.
