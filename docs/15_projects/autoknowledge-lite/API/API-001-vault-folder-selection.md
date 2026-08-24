# API-001 Vault 폴더 선택

`POST /v1/share` 요청에 선택 필드 `target_folder`를 추가한다.

```json
{
  "content": "저장할 내용",
  "target_folder": "20_Learning"
}
```

허용값은 `00_Inbox`, `10_Life`, `20_Learning`, `30_Interests`, `40_Reference`, `90_Archive`이며 생략 시 `00_Inbox`를 사용한다. 허용값 밖의 문자열, 절대경로와 상위 경로 표현은 `422`로 거부한다.
