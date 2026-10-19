# TEST-017 예약 CLI 계약 및 관리 가이드 검증

- 일자: 2026-10-19 (Asia/Seoul)
- 기준: `8b02705` 이후 CODE-011
- 판정: PASS, 예약 명령 기능 자체는 미구현 유지

## 실패 재현

도움말 검사 4개를 수정 전에 실행해 모두 failed를 확인했다. generate/inbox의
부모·하위 --help에 reserved와 not implemented 안내가 없었다.
기존 docs check도 mde-user-guide 및 knowledge-guide에서 각각 exit 1이었다.
수정 후 같은 검사가 모두 통과했다.

## 입력·출력 계약

- generate / generate command example / inbox / inbox list는 모두 exit 2.
- 공통 reserved but not implemented yet 메시지를 유지하며 생성 성공으로 표시하지 않음.
- 기존 legacy 입력 파일을 포함한 임시 디렉터리의 경로 목록·파일 바이트가 실행 전후 동일.
- generate, generate command, inbox, inbox list의 --help는 exit 0이며 미구현을 명시.
- 관리 참조에는 두 명령이 reserved로 표시되고 구현 명령 상세 목록에는 포함되지 않음.
- 실제 두 가이드가 parser와 일치해야 한다는 지속 회귀검사를 추가.

## 검증 결과

Python 3.12.14와 이전 검증 STEP의 frozen 환경을 재사용했다. 의존성 변경은 없다.

| 검증 | 실제 결과 |
|---|---|
| CLI·docs 대상 | 21 passed |
| root 전체 | 226 passed, 경고 0개, 14.58초 |
| 앱·메타데이터 전체 | 226 passed, 경고 0개, 5.25초 |
| Black 전체 | 234개 파일 유지, PASS |
| Ruff | PASS |
| 두 docs check | PASS |
| diff 검사 | PASS |

이번 추가 사례는 CLI 8개와 실제 문서 동기화 2개다. 앱 실행 226개에는 root에도
포함되는 메타데이터 7개가 있으므로 독립 합계로 합산하지 않는다.

## 범위와 제한

외부 AI API·개인 Vault·운영 Agent·원격 콘텐츠를 사용하지 않았다.
예약 명령의 동작 구현은 추가하지 않았다. Viewer·Android·APK·실기기 회귀는
재실행하지 않았으며 새 제품 기능이나 모바일 승인을 완료했다고 주장하지 않는다.
