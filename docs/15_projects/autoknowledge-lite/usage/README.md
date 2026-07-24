# autoknowledge-lite 사용법

이 폴더는 `autoknowledge-lite`의 설치, 실행, 설정, 기능별 사용 절차를 관리합니다.

## 관리 규칙

- 프로젝트 공통 설계는 `../SDS/`와 `../design/`에 기록합니다.
- 기능 구현 기록은 `../implementation/`에 기록합니다.
- 테스트 절차와 결과는 `../tests/`에 기록합니다.
- 사용자에게 영향을 주는 기능 변경은 이 폴더의 관련 가이드를 함께 정정합니다.
- 버전별 요약은 `../releases/`와 저장소 루트 `CHANGELOG.md`에 기록합니다.
- 실행 중 생성되는 원시 로그와 민감정보는 이 폴더에 저장하지 않습니다.

## 문서 이름

첫 통합 사용 가이드는 `GUIDE-001-usage.md`를 사용하고, 기능별 가이드가 필요하면 `GUIDE-002-<topic>.md` 순서로 추가합니다.

## 현재 가이드

- `GUIDE-001-usage.md`: 설치, 실행, Android 앱, Git 동기화와 문제 해결
- `GUIDE-002-vault-folder-selection.md`: 개인 Vault 고정 폴더 선택과 안전 제한
- `GUIDE-003-android-apk-download.md`: 휴대폰에서 v0.2.0 APK 직접 다운로드와 설치
