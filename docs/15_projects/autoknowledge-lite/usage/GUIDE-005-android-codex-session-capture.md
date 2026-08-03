# GUIDE-005 Android에서 Codex 전체 공개 대화 저장

## PC 준비

```powershell
$env:AUTOKNOWLEDGE_CONTROL_API_KEY='<충분히 긴 임의 키>'
$env:AUTOKNOWLEDGE_VIEWER_URL='http://<TAILSCALE-IP>:8765'
$env:MDE_CODEX_CONVERSATION_CAPTURE='1'
uv run autoknowledge-lite
```

제어 키는 서버와 Android에만 입력하고 로그·문서·대화에 붙여 넣지 않는다. Codex App Server 포트를 LAN/Tailscale에 직접 노출하지 않는다.

## Android 흐름

1. AutoKnowledge Lite 0.2.3에서 기존 서버 주소와 제어 API 키를 입력한다.
2. `PC 연결 상태 확인`을 누른다.
3. `최근 실제 Codex 세션 조회`에서 제목, 시각, 메시지 수와 client 유형을 확인한다.
4. 등록 프로젝트와 저장할 세션을 선택한다.
5. `전체 공개 대화 수집에 동의합니다`를 켠다.
6. `선택 세션 연결 및 지금 수집`을 누른다.
7. 필요하면 `추가 대화 동기화`를 누른다.
8. `Finalize 및 저장` 후 `SAVED`, 메시지 수와 revision을 확인한다.
9. `Knowledge Viewer에서 열기`를 누르면 저장된 문서가 딥링크로 바로 열린다. 민감 Source는 기존 확인 대화상자를 먼저 승인한다.

Codex 저장 오류는 기존 Clipboard Capture 대기열과 별도다. 민감정보가 발견되면 저장을 강행하지 않고 `QUARANTINED` 자료를 PC에서 검토한다.
