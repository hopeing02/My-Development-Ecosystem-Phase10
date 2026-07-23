# CODE-004 MDE 문서 동기화 구현 기록

- 상태: Implemented
- 작성일: 2026-07-22

## 구현 내용

`mde.documentation` 모듈이 현재 CLI parser를 순회해 구현·예약 명령 표와 leaf command usage를 생성한다. `mde-user-guide`와 `knowledge-guide` target의 관리 표식 한 쌍 사이만 교체하고, 나머지 본문은 그대로 유지한다.

## CLI

```powershell
uv run mde docs check
uv run mde docs update
uv run mde docs update --apply
uv run mde docs check --target knowledge-guide
uv run mde docs update --target knowledge-guide --apply
```

`check`는 최신 상태일 때 0, 불일치할 때 1을 반환한다. `update`는 변경 diff만 출력하며 0을 반환한다. `update --apply`는 차이가 있을 때 관리 구간만 UTF-8과 LF로 갱신한다.

## 안전장치

- 허용된 target만 사용
- MDE 문서 루트 탐색
- 정확히 한 쌍의 관리 표식 요구
- 기본 미리보기
- 명시적 `--apply` 요구
- 다른 문서와 Git 상태 무변경
- 자동 commit과 push 없음
