# Codex AI 요청서

- 작성일: 2026-07-23
- 프로젝트: autoknowledge-lite
- 대상 버전: 0.2.0

## 요청

Android 앱에서 개인 Vault의 고정 분류 폴더를 선택하고 서버가 allowlist를 검증한 뒤 해당 폴더에 Markdown을 저장하도록 구현한다.

## 제약

- 기본값은 `00_Inbox`다.
- 임의 경로 입력은 허용하지 않는다.
- 기존 Git 동기화는 선택된 Markdown 한 파일만 처리한다.
- 개인 Vault와 프로젝트 공식 문서를 혼합하지 않는다.
- 구현·테스트·사용법·릴리스·CHANGELOG·DevelopmentLog를 기록한다.
