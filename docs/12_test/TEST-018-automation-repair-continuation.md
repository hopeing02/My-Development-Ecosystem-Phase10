# TEST-018 자동 수정 후 Workflow 재개

- 일자: 2026-10-19 (Asia/Seoul)
- 대상: CODE-012
- 이번 STEP 판정: PASS
- 실 AI 개발부터 운영 배포까지의 전체 판정: 미검증

## 수정 전 재현

추가한 후속 단계 성공·save/push/배포 테스트 대역 실패·checkpoint 보존 검사에서
5 failed, 기존 2 passed를 확인했다. 후속 단계가 실행되지 않아 실패를 전파하지
못했고 checkpoint도 auto-apply-fix 등의 합성 ID로 대체됐다.

## 검증 내용

- 재테스트 성공 후 남은 save → push → 후속 단계 → complete 실행.
- 후속 save/push/테스트 대역 배포가 실패하면 failed로 중단하며 추가 AI 수정 없음.
- 테스트가 계속 실패하면 제한 횟수에서 중단, Git 저장 없음, 원래 checkpoint 유지.
- 비활성 save 및 false 조건 push는 재개 후에도 skipped 유지.
- test.run이 여러 개인 경우 실제 실패한 step의 args로 재검증.
- 재검증 결과를 원래 test output으로 제공하고 완료 checkpoint에 연결.
- 실제 Plugin 통합: 초기 코드 생성 → pytest 1 failed → 수정 → pytest 1 passed →
  실제 로컬 커밋 → 임시 bare 원격 push → complete. 최종 로컬/원격 HEAD 동일.

AI 응답만 MockAIProvider로 제어했다. release.deploy라는 단위 테스트 handler는
실패 전파를 검증하는 대역이며 실제 deploy 구현을 추가한 것이 아니다.

## 결과

Python 3.12.14와 기존 frozen 환경을 사용했다. 실행 방법은 CODE-012를 따른다.

| 항목 | 실제 결과 |
|---|---|
| 자동화 + Git 통합 대상 | 11 passed |
| root 전체 | 234 passed, 경고 0개, 15.96초 |
| 앱·메타데이터 전체 | 226 passed, 경고 0개, 4.90초 |
| Black 전체 | 234개 파일 유지, PASS |
| Ruff | PASS |
| 두 docs check | PASS |
| diff 검사 | PASS |

기존 226개 root 사례에서 실제 버그·정책·통합 회귀 8개가 추가됐다.
앱 실행에는 root에도 포함되는 메타데이터 7개가 있으므로 단순 합산하지 않는다.

## 미검증 및 제약

실 AI 호출, AI 리뷰 거절, 운영 서비스 배포·상태 확인·복구는 검증하지 않았다.
운영 원격 push나 서비스 중단을 통합 테스트에서 수행하지 않았다. 사용한 원격은
임시 디렉터리의 bare 저장소다. Android·Viewer·실기기 회귀는 재실행하지 않았다.
전체 자동화 완료로 표시하지 않는다.
