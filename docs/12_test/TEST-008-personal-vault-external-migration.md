# TEST-008 개인 Vault 외부 경로 이전 검증

- 상태: Passed
- 작성일: 2026-07-22

## 대상

- AutoKnowledge 개인 Git Vault의 MDE 저장소 외부 복사
- Git branch, HEAD, remote, 객체 무결성
- 원본과 복사본 파일 SHA-256 비교
- MDE Source 경로 전환
- 민감 Source 보안 정책과 검색
- 기존 원본 보존

## 사전 조건

- 기존 Vault Git working tree가 clean 상태
- 기존 branch가 `main`
- 추적 파일 19개, Markdown 18개
- 사용자 전용 Knowledge 경로 사용 가능

## 절차

1. 기존 Vault의 Git 상태, HEAD, remote를 읽기 전용으로 확인한다.
2. 사용자 전용 `C:\Users\<user>\Knowledge\Personal-Vault`로 `.git`을 포함해 전체 복사한다.
3. 원본과 복사본의 Git 정보와 파일 SHA-256을 비교한다.
4. 기존 MDE Source 등록을 해제하고 같은 이름과 보안 Category로 새 경로를 등록한다.
5. 새 Source를 스캔하고 Source 제한 검색을 실행한다.
6. 기본 검색, `--all`, 감사 로그, 기존 원본 보존을 확인한다.

## 예상 결과

- 원본과 복사본의 branch, HEAD, remote가 동일하다.
- 파일 누락과 해시 불일치가 없다.
- 새 Source가 `personal`, `obsidian`, `sensitive=true`, `agent access=false`다.
- Markdown 18개가 오류 없이 색인된다.
- 기본 검색과 `--all`만 사용한 검색에서 민감 Source가 제외된다.
- 감사 로그에 이전·신규 절대경로가 기록되지 않는다.
- 기존 원본은 삭제되지 않는다.

## 실제 결과

```text
Branch: main
HEAD match: true
Remote match: true
Git fsck: passed
Source files excluding .git: 19
Destination files excluding .git: 19
SHA-256 mismatches: 0
Markdown: 18
First scan on new path: Added 18, Errors 0
Default search exposed sensitive source: false
--all exposed sensitive source: false
Audit contains old absolute path: false
Audit contains new absolute path: false
Original preserved: true
```

결과: Passed
