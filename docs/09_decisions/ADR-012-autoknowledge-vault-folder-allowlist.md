# ADR-012 AutoKnowledge Vault 폴더 allowlist

- 상태: Accepted
- 결정일: 2026-07-23

## 결정

Android 앱은 다음 고정 폴더 중 하나만 선택해 `target_folder`로 전송한다.

- `00_Inbox`
- `10_Life`
- `20_Learning`
- `30_Interests`
- `40_Reference`
- `90_Archive`

서버는 같은 allowlist를 API 모델에서 검증하고, 값이 없으면 `00_Inbox`를 사용한다. 임의 경로, 절대경로와 `..` 경로는 허용하지 않는다.

선택된 폴더에 생성된 Markdown 한 파일만 기존 Git 동기화에 전달한다. 프로젝트 개발 문서는 개인 Vault가 아니라 `docs/15_projects/autoknowledge-lite/`에서 계속 관리한다.
