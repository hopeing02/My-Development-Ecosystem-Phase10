# SDS-002 Vault 폴더 선택

- 버전: 0.2.0
- 상태: Approved

## 요구사항

클립보드 또는 Android 공유 콘텐츠를 저장할 때 사용자가 개인 Vault의 고정 분류 폴더를 선택할 수 있어야 한다.

## 허용 폴더

`00_Inbox`, `10_Life`, `20_Learning`, `30_Interests`, `40_Reference`, `90_Archive`

## 동작

1. Android 앱에서 폴더를 선택하고 사용자 설정에 저장한다.
2. 클립보드와 공유 payload에 `target_folder`를 포함한다.
3. 서버는 allowlist를 검증하고 작업 JSON에 선택값을 저장한다.
4. Markdown을 `<Vault>/<target_folder>/`에 저장한다.
5. 생성된 Markdown 한 파일만 기존 Git 동기화에 전달한다.

값이 누락된 기존 클라이언트와 기존 작업 JSON은 `00_Inbox`를 사용한다.

## 보안

임의 문자열을 파일 경로로 사용하지 않는다. allowlist 밖의 값은 API `422`로 거부하며 Vault 밖에 파일을 만들지 않는다.
