# CMD-006 Windows Codex 작업 수집

## 명령

```powershell
uv run mde codex register --project-id PROJECT --path C:\repo --target-folder 40_Reference/Codex
uv run mde codex list
uv run mde codex start --project PROJECT --title "작업 제목" --request "작업 요청"
uv run mde codex status
uv run mde codex run -- uv run pytest
uv run mde codex add-note --type progress --message "구현 완료"
uv run mde codex finalize --summary "최종 요약"
uv run mde codex retry
uv run mde codex doctor
```

`start --launch`는 doctor가 PATH에서 Codex 실행 파일을 실제 탐지한 경우에만 사용한다. 기본 모드는 수동 시작·종료이다.

`mde save --finalize-codex`는 save 성공 후 활성 세션을 종료한다. 수집기 실패는 save 성공을 실패로 바꾸지 않는다.
