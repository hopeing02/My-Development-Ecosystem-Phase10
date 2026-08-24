# API-002 Android APK 다운로드

## 요청

```http
GET /downloads/autoknowledge-lite.apk
```

## 성공

- 상태: `200`
- Content-Type: `application/vnd.android.package-archive`
- 파일명: `autoknowledge-lite-v0.2.0.apk`

## 실패

서버에 빌드 APK가 없으면 `404`와 다음 응답을 반환한다.

```json
{"detail": "Android APK is not available."}
```

경로 파라미터와 임의 파일 다운로드는 지원하지 않는다.
