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

`adb devices -l` 결과 연결된 기기가 0대였다. 따라서 사용자의 휴대폰에 설치하거나 앱 데이터를 변경하지 않았다.

## 판정

- 자동화 및 배포 준비: PASS
- 물리 Android 설치 승인: PENDING
- 최종 상태: Internal RC

물리 기기 승인 절차는 `GUIDE-009-mobile-rc-acceptance.md`를 따른다.
