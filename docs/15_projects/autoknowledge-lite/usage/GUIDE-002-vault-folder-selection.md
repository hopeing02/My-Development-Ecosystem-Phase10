# GUIDE-002 Vault 폴더 선택

- 버전: 0.2.0
- 상태: Active

## 사용할 수 있는 폴더

| 폴더 | 용도 |
|---|---|
| `00_Inbox` | 기본 받은함, 분류 전 자료 |
| `10_Life` | 생활·가족·일상 |
| `20_Learning` | 학습·강의·연구 |
| `30_Interests` | 관심 분야·취미 |
| `40_Reference` | 장기 참고자료 |
| `90_Archive` | 보관 자료 |

## 클립보드 저장

1. 휴대폰에 v0.2.0 APK를 설치한다.
2. AutoKnowledge Lite를 연다.
3. `개인 Vault 저장 폴더` 목록에서 목적 폴더를 선택한다.
4. 다른 앱에서 전체 텍스트를 복사한다.
5. `클립보드 내용 저장`을 누른다.
6. 성공 메시지에서 저장 폴더를 확인한다.

## 다른 앱에서 공유

AutoKnowledge Lite 화면에서 마지막으로 선택한 폴더가 공유 메뉴 저장에도 적용된다. 폴더를 바꾸려면 AutoKnowledge Lite를 먼저 열어 새 폴더를 선택한 뒤 공유한다.

## 기본값과 기존 앱

폴더를 선택하지 않거나 기존 Android 앱이 `target_folder`를 보내지 않으면 `00_Inbox`에 저장된다. 기존 `AutoKnowledge/` 문서는 자동 이동·수정·삭제하지 않는다.

## 경로 보호

사용자는 임의 폴더명이나 `../` 경로를 입력할 수 없다. 서버도 6개 allowlist 밖의 값을 `422`로 거부한다.

## Git 동기화

기존 Git 동기화가 활성화되어 있으면 선택 폴더에 새로 생성된 Markdown 한 파일만 커밋·푸시한다. 프로젝트 설계·구현·테스트·사용법 문서는 개인 Vault가 아니라 MDE 프로젝트 문서 영역에 유지한다.

## APK

```text
apps/autoknowledge-lite/android/app/build/outputs/apk/debug/app-debug.apk
```

기존 휴대폰 앱에는 새 화면이 없으므로 v0.2.0 APK를 다시 설치해야 한다.
