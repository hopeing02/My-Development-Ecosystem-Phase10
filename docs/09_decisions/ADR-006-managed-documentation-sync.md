# ADR-006 관리 구간 기반 MDE 문서 동기화

- 상태: Accepted
- 작성일: 2026-07-22

## 배경

MDE CLI가 변경되면 전체 사용자 가이드의 명령과 옵션이 실제 코드에서 벗어날 수 있다. 전체 문서를 무인으로 다시 쓰면 사람이 작성한 설명과 보안 주의사항이 손상될 위험이 있고, 자동 커밋이나 push까지 결합하면 변경 범위가 지나치게 커진다.

## 결정

문서 유지관리는 Knowledge Plugin이 아닌 독립적인 MDE `docs` 명령으로 제공한다.

- 실제 `argparse` 정의를 CLI 참조의 단일 기준으로 사용한다.
- `CMD-004-mde-user-guide.md`와 `CMD-003-mde-knowledge-plugin-user-guide.md`의 명시적인 시작·종료 표식 사이만 target별로 자동 관리한다.
- `mde docs check`는 불일치를 읽기 전용으로 확인한다.
- `mde docs update`는 unified diff만 출력한다.
- `mde docs update --apply`가 있을 때만 관리 구간을 수정한다.
- 표식이 없거나 중복되면 수정하지 않고 실패한다.
- 자동 커밋, push, Source 원본 수정, 다른 문서 수정은 수행하지 않는다.
- 예약 명령과 구현 명령을 구분해 표시한다.

## 결과

CLI 추가·정정·삭제는 관리 구간에 자동 반영할 수 있고, 설명 본문은 보존된다. 적용 후 테스트, DevelopmentLog 기록, Knowledge 재색인, Git 커밋은 기존 개발 절차에 따라 별도로 수행한다.

## 대안

전체 문서를 매번 생성하는 방식은 설명 손실 위험 때문에 채택하지 않았다. Knowledge Plugin이 원본을 직접 수정하는 방식은 원본 보호 원칙과 책임 분리에 어긋나므로 채택하지 않았다.
