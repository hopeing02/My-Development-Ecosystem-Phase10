# GUIDE-003 Android APK 직접 다운로드

- 버전: 0.2.0
- 상태: Active

## 다운로드

휴대폰을 노트북과 같은 Tailscale 네트워크에 연결하고 다음 주소를 연다.

```text
http://100.75.235.67:8000/downloads/autoknowledge-lite.apk
```

파일명은 `autoknowledge-lite-v0.2.0.apk`이다.

## 설치

1. 다운로드 완료 알림을 누른다.
2. Android가 요구하면 해당 브라우저의 알 수 없는 앱 설치를 이번 설치에만 허용한다.
3. 기존 AutoKnowledge Lite 위에 업데이트 설치한다.
4. 설치 후 앱을 열고 서버 주소와 Vault 폴더 선택을 확인한다.

노트북이 꺼져 있거나 AutoKnowledge 서버가 중지됐거나 휴대폰 Tailscale 연결이 끊겨 있으면 다운로드할 수 없다.

## 보안

다운로드 API는 경로 입력을 받지 않고 빌드된 AutoKnowledge APK 한 파일만 제공한다. Vault, 작업 JSON, 로그와 임의 서버 파일은 제공하지 않는다.
