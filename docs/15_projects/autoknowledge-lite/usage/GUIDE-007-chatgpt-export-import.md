# GUIDE-007 ChatGPT Export Import

## 준비

ChatGPT에서 Data Export를 요청하고 전달된 ZIP을 로컬 PC에 다운로드한다. ZIP을
직접 해제하거나 내부 JSON을 수정할 필요가 없다.

## 실행

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10
uv run --project apps/autoknowledge-lite autoknowledge-lite chatgpt-import `
  C:\Downloads\chatgpt-export.zip
```

별도 로컬 데이터 경로를 사용하려면 다음과 같이 지정한다.

```powershell
uv run --project apps/autoknowledge-lite autoknowledge-lite chatgpt-import `
  C:\Downloads\chatgpt-export.zip `
  --data-dir C:\AutoKnowledgeLocalData
```

## 결과

- `imported`: 원본 보관과 하나 이상의 신규 Session projection 완료
- `partial`: 원본은 보관됐지만 일부 Session projection 실패
- `duplicate`: 같은 Archive와 Session revision이 이미 존재
- `error`: ZIP 자체를 안전하게 읽거나 보관할 수 없음

부분 성공과 warning이 있어도 원본 ZIP은 로컬 raw Archive에 보존된다. 명령 출력은
원문과 raw Archive 절대 경로를 포함하지 않는다.
