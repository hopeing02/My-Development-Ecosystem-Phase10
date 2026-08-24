# ADR-010 로컬 생성물과 복구본 Git 제외 정책

- 상태: Accepted
- 작성일: 2026-07-23

## 배경

로컬 에이전트 작업 영역, 의존성 복사본, Android 빌드 캐시, AutoKnowledge 실행 데이터, 개인 Vault 복구본이 Git 미추적 항목으로 함께 나타나 실제 소스 변경을 구분하기 어려웠다. 일부 항목은 개인 콘텐츠나 로컬 SDK 경로를 포함할 수 있어 실수로 커밋하면 안 된다.

## 분류와 결정

| 경로 | 분류 | 결정 |
|---|---|---|
| `.codex-remote-attachments/` | 사용자 첨부 작업 파일 | 보존, Git 제외 |
| `.incoming/` | 외부 반입·비교용 소스 | 보존, Git 제외 |
| `.runtime/` | 실행용 저장소·가상환경·로그 | 보존, Git 제외 |
| `.test-deps/` | 로컬 테스트 의존성 | 보존, Git 제외 |
| `*.egg-info/` | Python 생성 메타데이터 | 재생성 가능, Git 제외 |
| `.gradle/`, `local.properties`, `build/` | Android 캐시·로컬 SDK·빌드 결과 | Git 제외 |
| `apps/autoknowledge-lite/data/` | 작업 결과와 로컬 콘텐츠 | 보존, Git 제외 |
| `apps/autoknowledge-lite/vault/` | 이전 개인 Vault 중첩 Git 복구본 | 보존, 경로 한정 Git 제외 |
| `status/agent-heartbeat.json` | 실행 상태 파일 | 보존, Git 제외 |
| `agent-test-target.txt` 삭제 | 기존 추적 파일의 사용자 변경 | 이번 결정에서 변경·복구·커밋하지 않음 |

Android의 `app/src/`, Gradle 설정, manifest 등 실제 소스가 향후 생성되면 추적할 수 있도록 `android/` 전체는 제외하지 않는다. 개인 Vault 복구본 역시 삭제하거나 이동하지 않고 별도의 보존 결정 전까지 현재 위치에 둔다.

## 결과

`git status`에는 실제 검토가 필요한 추적 파일 변경만 남고, 개인·로컬·재생성 가능 파일의 우발적 커밋 위험이 줄어든다.

## 대안

모든 미추적 파일을 삭제하는 방식은 사용자 첨부와 복구본을 잃을 수 있어 채택하지 않았다. `apps/autoknowledge-lite/android/` 전체를 제외하는 방식은 미래 Android 소스까지 숨기므로 채택하지 않았다.
