# TEST-034 모바일 릴리스 후보 준비

## 일자

2026-08-20

## 확인 결과

- Git 작업 트리: clean에서 시작
- AutoKnowledge-Lite: versionName `0.2.4`, versionCode `5`
- MDE Knowledge Viewer: versionName `0.1.0`, versionCode `1`
- 두 APK package, minSdk 26, targetSdk 34 확인
- 두 APK v2 서명 검증 통과
- localhost와 Tailscale 다운로드 SHA-256 일치
- AutoKnowledge API, Viewer, Graph, Timeline HTTP 200
- 자동화 회귀 결과는 `TEST-033-step10-full-regression.md` 참조

## 물리 기기 상태

2026-08-20 준비 시점의 `adb devices -l` 결과 연결된 기기가 0대였다. 이후
2026-08-24 외부 LTE 실기기에서 Tailscale을 통해 AutoKnowledge Lite 다운로드·연결과
ChatGPT Shared Link 신규/중복 가져오기, Viewer 최신 Session 표시를 확인했다.

상세 결과는 `TEST-035-mobile-chatgpt-live-validation.md`를 참조한다.

## 판정

- 자동화 및 배포 준비: PASS
- 물리 Android ChatGPT 경로: PASS
- 전체 물리 Android 설치 승인: PENDING
- 최종 상태: Internal RC

물리 기기 승인 절차는 `GUIDE-009-mobile-rc-acceptance.md`를 따른다.
