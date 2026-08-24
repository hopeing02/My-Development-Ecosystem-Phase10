# ARCH Codex 공개 대화 세션 소스 분석

- 조사일: 2026-08-03
- 대상: AutoKnowledge-Lite 통합 개발 4단계
- 상태: Implemented

## 1. 조사 목적

Windows Codex 작업 수집기의 Git, 명령, 테스트, patch 자료를 유지하면서 사용자에게 공개된 Codex 대화를 같은 `development_session`에 추가할 안전한 인터페이스를 결정한다. Codex 내부 저장 경로나 비공개 파일 형식은 도메인 계약으로 사용하지 않는다.

## 2. 확인한 환경

- 저장소 브랜치: `codex/obsidian-knowledge-automation`
- 기준 커밋: `16459fd`
- Windows 앱 패키지: `OpenAI.Codex` 26.727.6591.0 ARM64, 상태 `Ok`
- PATH의 `codex.exe`: Windows 앱 패키지에 포함된 실행 파일
- 현재 PowerShell에서 `codex --version`, `codex --help`, `codex app-server` 직접 실행: `Access is denied`

설치 위치는 환경 조사 결과에만 사용했다. 수집기 코드에 WindowsApps 경로나 사용자 프로필 경로를 하드코딩하지 않았다.

## 3. 공식 인터페이스 조사

OpenAI Codex 공식 매뉴얼은 App Server를 Codex 클라이언트용 통합 인터페이스로 설명한다.

- `codex app-server`: stdio JSONL 기반 JSON-RPC 제공
- `thread/list`: 저장된 thread 메타데이터와 공식 thread ID 탐색
- `thread/read` + `includeTurns: true`: thread를 재개하지 않고 turn과 공개 item 읽기
- `thread.id`: thread 식별자
- `thread.sessionId`: live session tree의 root 식별자
- 공개 item: `userMessage`, `agentMessage`, `plan`, `commandExecution`, `fileChange`, 공개 tool item, review item, `contextCompaction`
- `reasoning`: 별도 item 형식이며 이번 수집 대상에서 제외

공식 문서: [Codex App Server](https://learn.chatgpt.com/docs/app-server)

현재 공식 매뉴얼에서 일반 Codex 앱 대화를 파일로 내보내는 안정적인 CLI `export` 명령은 확인하지 못했다. 따라서 내부 rollout JSONL이나 SQLite를 직접 읽지 않는다.

## 4. 결정

### 4.1 기본 경로

`CodexAppSessionAdapter`가 공식 App Server의 `thread/list`와 `thread/read`만 호출한다. CLI와 IDE thread도 App Server의 같은 thread 계약으로 노출되는 범위에서 `CodexCliSessionAdapter`와 `CodexIdeSessionAdapter`가 공통 구현을 사용한다.

### 4.2 명시적 가져오기 경로

App Server 실행이 불가능한 환경에서는 사용자가 명시적으로 제공한 `thread/read` JSON 응답만 `ManualImportSessionAdapter`로 가져온다. 원본 파일은 수정하거나 세션 폴더에 복사하지 않는다. 저장되는 reference에는 `%EXPLICIT_IMPORT%/<filename>` 별칭만 남긴다.

### 4.3 미지원 경로

- Windows 앱 내부 데이터 폴더 추측
- rollout JSONL 직접 파싱
- SQLite 직접 조회
- 화면 OCR, 접근성 읽기, 키보드 감시
- 브라우저 쿠키나 인증 토큰 접근
- 시스템 프롬프트와 reasoning item 수집

## 5. 어댑터 계약

```text
CodexSessionSource
├─ CodexAppSessionAdapter     공식 App Server
├─ CodexCliSessionAdapter     공식 App Server 공통 계약
├─ CodexIdeSessionAdapter     공식 App Server 공통 계약
└─ ManualImportSessionAdapter 명시적 thread/read JSON
```

각 어댑터는 `discover_sessions`, `read_session`, `supports`를 제공한다. 도메인 계층은 App Server 원본 item 대신 `NormalizedCodexMessage` 형태의 사전만 사용한다.

## 6. 공개 메시지 변환

| App Server item | role | messageType | 처리 |
|---|---|---|---|
| `userMessage` | `user` | `text` | text 입력만 보존 |
| `agentMessage` | `assistant` | `text`/`progress` | 공개 phase 보존 |
| `plan` | `assistant` | `progress` | 공개 plan 보존 |
| `commandExecution` | `tool` | `command` | 명령과 공개 결과 보존 |
| `fileChange` | `tool` | `patch` | `codex_displayed_patch`, 적용 상태 `unknown` |
| 공개 tool/review item | `tool`/`assistant` | `progress` | 최소 공개 필드 보존 |
| `contextCompaction` | `system_summary` | `progress` | compaction 발생 사실만 보존 |
| `reasoning` | 없음 | 없음 | 항상 제외 |
| 알 수 없는 공개 item | `unknown` | `unknown` | 내용 보존, partial 경고 |

## 7. 보안과 동의

- attach/import 전에 `--consent`가 필수다.
- `MDE_CODEX_CONVERSATION_CAPTURE=0|false|no|off`로 기능을 비활성화한다.
- 메시지마다 기존 secret 필터를 다시 적용한다.
- Windows 사용자 홈 경로는 `%USERPROFILE%`로 치환한다.
- 메시지는 기본 256 KiB로 제한하고 앞뒤를 보존해 잘림을 표시한다.
- 원문 메시지와 명령 출력은 일반 로그나 inspect 출력에 표시하지 않는다.
- 서버가 민감정보를 다시 감지하면 기존 quarantine 정책을 따른다.

## 8. 증분과 재작성 처리

체크포인트는 `sourceSessionId`, 전체 공개 메시지 fingerprint, 마지막 sequence, 마지막 source message ID를 저장한다. App Server의 `thread/read` 결과를 다시 표준화한 뒤 `sourceMessageId`와 content hash로 중복을 제거한다. 메시지 수가 감소하거나 같은 길이에서 fingerprint가 달라지면 체크포인트 무효 경고를 남기고 전체 결과를 다시 병합한다.

## 9. 현재 Windows 제한

설치된 Windows 앱은 확인했지만 현재 PowerShell 보안 경계에서 번들 `codex.exe` 실행이 거부되었다. 따라서 이 환경에서는 실행 중인 앱의 실제 thread를 App Server로 발견하거나 읽는 검증을 완료할 수 없다. 이 상태는 doctor의 WARN으로 보고하며, 명시적 JSON import는 정상 동작한다. 내부 파일 직접 파싱으로 우회하지 않는다.

## 10. 변경 대응

App Server schema는 설치된 Codex 버전에 맞춰 생성할 수 있다. 지원 item이 변경되면 adapter version과 fixture를 갱신한다. 알 수 없는 item은 잘못 분류하지 않고 `unknown`과 partial 경고로 보존한다.
