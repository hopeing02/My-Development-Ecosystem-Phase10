# ADR-013 AutoKnowledge APK 다운로드 경로

- 작성일: 2026-07-23
- 상태: Accepted

## 결정

휴대폰 설치용 APK는 별도 파일 서버를 만들지 않고 기존 AutoKnowledge 로컬 서버의 고정 `GET /downloads/autoknowledge-lite.apk` 경로로 제공한다.

## 이유

- 사용 중인 Tailscale 연결을 그대로 사용할 수 있다.
- 별도 포트·프로세스·자동 시작 설정이 필요하지 않다.
- 고정 파일 하나만 노출해 임의 파일 다운로드 위험을 제한할 수 있다.

## 보안 경계

- 요청에서 파일 경로나 이름을 입력받지 않는다.
- Vault, 작업 JSON, 로그를 제공하지 않는다.
- 외부 클라우드나 공개 배포 서버에 APK를 업로드하지 않는다.
- 노트북 서버와 Tailscale 연결이 켜져 있을 때만 접근할 수 있다.
