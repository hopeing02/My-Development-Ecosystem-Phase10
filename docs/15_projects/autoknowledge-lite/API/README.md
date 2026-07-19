# autoknowledge-lite — API

## GET `/v1/status`

서비스 이름, 상태, 버전을 반환합니다.

## POST `/v1/share`

공유 콘텐츠를 검증하고 `202 Accepted`로 작업을 접수합니다. 응답에는 `job_id`, `status=queued`, `received_at`이 포함됩니다.

기본 설정에서는 응답 후 백그라운드에서 AI 분석과 Markdown 생성을 자동 실행합니다. 자동 처리를 끄려면 `AUTOKNOWLEDGE_AUTO_PROCESS=false`를 설정합니다.

모바일 앱이 URL만 공유한 경우 서버가 공개 웹페이지를 조회해 읽을 수 있는 본문으로 보강합니다. ChatGPT 공개 공유 링크의 이스케이프된 대화 데이터와 일반 HTML의 가시 텍스트를 지원하며, 내부망 주소·비텍스트 응답·2MB 초과 응답은 차단합니다.

## POST `/v1/ai/process`

`job_id`로 접수된 작업을 읽고 분석합니다. 성공 시 `status=processed`, `processed_at`, 요약·핵심 항목·태그·제공자 정보를 반환하고 같은 JSON 파일에 저장합니다.

- 잘못된 UUID: `422`
- 존재하지 않는 작업: `404`
- 분석기 실패: `502`
- 저장소 실패: `503`

## POST `/v1/markdown`

분석된 작업을 YAML 메타데이터가 포함된 Markdown으로 변환해 작업 JSON과 Obsidian Vault의 실제 `.md` 파일에 저장합니다. 응답의 `note_path`에서 생성된 파일 경로를 확인할 수 있습니다. 아직 분석되지 않은 작업은 `409`를 반환합니다.

기본 Vault는 `apps/autoknowledge-lite/vault/`이며 노트는 `AutoKnowledge/` 하위에 생성됩니다. 기존 Vault를 사용하려면 `AUTOKNOWLEDGE_VAULT_DIR`에 Vault 최상위 경로를 설정합니다.

## AI 제공자 설정

기본 분석기는 외부 호출이 없는 `local-deterministic` 구현입니다. `AUTOKNOWLEDGE_AI_PROVIDER`로 제공자를 선택합니다.

- `local`: 로컬 결정론적 분석기
- `openai`: OpenAI Responses API (`OPENAI_API_KEY` 필요)
- `claude` 또는 `anthropic`: Anthropic Messages API (`ANTHROPIC_API_KEY` 필요)

모델은 `OPENAI_MODEL`과 `ANTHROPIC_MODEL`로 변경할 수 있습니다. 기본값은 각각 `gpt-5.6-sol`, `claude-sonnet-4-6`입니다. 키를 파일이나 저장소에 기록하지 않습니다.
