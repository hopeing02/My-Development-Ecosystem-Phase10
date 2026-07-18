# autoknowledge-lite — API

## GET `/v1/status`

서비스 이름, 상태, 버전을 반환합니다.

## POST `/v1/share`

공유 콘텐츠를 검증하고 `202 Accepted`로 작업을 접수합니다. 응답에는 `job_id`, `status=queued`, `received_at`이 포함됩니다.

## POST `/v1/ai/process`

`job_id`로 접수된 작업을 읽고 분석합니다. 성공 시 `status=processed`, `processed_at`, 요약·핵심 항목·태그·제공자 정보를 반환하고 같은 JSON 파일에 저장합니다.

- 잘못된 UUID: `422`
- 존재하지 않는 작업: `404`
- 분석기 실패: `502`
- 저장소 실패: `503`

## AI 제공자 설정

기본 분석기는 외부 호출이 없는 `local-deterministic` 구현입니다. `AUTOKNOWLEDGE_AI_PROVIDER`로 제공자를 선택합니다.

- `local`: 로컬 결정론적 분석기
- `openai`: OpenAI Responses API (`OPENAI_API_KEY` 필요)
- `claude` 또는 `anthropic`: Anthropic Messages API (`ANTHROPIC_API_KEY` 필요)

모델은 `OPENAI_MODEL`과 `ANTHROPIC_MODEL`로 변경할 수 있습니다. 기본값은 각각 `gpt-5.6-sol`, `claude-sonnet-4-6`입니다. 키를 파일이나 저장소에 기록하지 않습니다.
