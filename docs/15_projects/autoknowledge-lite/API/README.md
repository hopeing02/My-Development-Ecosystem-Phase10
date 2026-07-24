# AutoKnowledge Lite API

## GET `/v1/status`

서비스 이름, 상태와 버전을 반환한다.

## POST `/v1/share`

공유 콘텐츠를 검증하고 `202 Accepted`로 작업을 접수한다. 응답에는 `job_id`, `status=queued`, `received_at`이 포함된다. 기본 설정에서는 응답 후 분석·Markdown 생성·Vault 저장을 자동 실행하며 `AUTOKNOWLEDGE_AUTO_PROCESS=false`로 자동 처리를 끌 수 있다.

선택 필드 `target_folder`는 6개 고정 Vault 폴더만 허용하고 생략 시 `00_Inbox`를 사용한다. 허용값 밖의 경로는 `422`로 거부한다.

URL만 공유되면 공개 웹페이지 본문을 보강한다. 내부망 주소, 비텍스트 응답, 2MB 초과 응답은 차단한다.

## GET `/downloads/autoknowledge-lite.apk`

빌드된 AutoKnowledge Lite v0.2.0 Android APK 한 파일을 내려준다. 경로 입력은 받지 않으며 파일이 없으면 `404`를 반환한다.

## POST `/v1/ai/process`

접수된 `job_id`를 분석하고 요약·핵심 항목·태그·제공자 정보를 작업 JSON에 저장한다.

- 잘못된 UUID: `422`
- 존재하지 않는 작업: `404`
- 분석기 실패: `502`
- 저장소 실패: `503`

## POST `/v1/markdown`

분석된 작업을 YAML 메타데이터가 포함된 Markdown으로 변환하고 개인 Vault에 저장한다. 아직 분석되지 않은 작업은 `409`를 반환한다.

## AI 제공자

`AUTOKNOWLEDGE_AI_PROVIDER`는 `local`, `openai`, `claude` 또는 `anthropic`을 지원한다. 외부 공급자를 사용할 때 필요한 키는 사용자 환경에서만 관리하고 저장소 문서에 기록하지 않는다.
