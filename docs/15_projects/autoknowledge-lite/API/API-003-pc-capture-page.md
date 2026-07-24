# API-003 PC 저장 화면

## 요청

```http
GET /pc
```

## 응답

- 상태: `200`
- Content-Type: `text/html`
- 정적 PC 저장 화면

화면은 동일 서버의 `POST /v1/share`를 호출한다. 저장 폴더는 클라이언트 선택값과 관계없이 서버의 기존 allowlist로 다시 검증한다.
