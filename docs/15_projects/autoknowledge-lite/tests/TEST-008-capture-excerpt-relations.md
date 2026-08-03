# TEST-008 Capture 발췌 관계와 모바일 Codex 저장

- 테스트일: 2026-08-03

## 자동 검증

- 정확 해시 단일 후보 확정과 동점 후보 제안
- 부분/연속 메시지, 짧은 단편과 프로젝트 불일치 차단
- revision 근거 제거 후 STALE
- 거절 후보 재제안 방지와 dry-run 무변경
- 관계 조회와 evidence 원문 비포함
- 모바일 API 비활성·401 인증, 명시 동의와 경로 비노출
- capture/attach/sync/finalize/status 응답
- Android 세션/상태/프로젝트 모델
- 기존 Capture API 회귀

## 결과

- AutoKnowledge Lite Python 전체: 110 passed, 1 skipped
- 신규 관계·모바일 제어 Python: 12 passed
- Android Debug JUnit: 22 passed
- Android `assembleDebug`: 성공
- Knowledge Viewer 딥링크 포함: 19 passed, production build 성공
- Windows Codex 수집기 회귀: 24 passed
- 실제 공식 App Server 세션 discover/inspect: 성공
- 실제 인증 모바일 API 세션 목록: 1건 조회, 제목·client·메시지 수 반환 확인
- 실제 Backfill dry-run/실행: Android Codex 단편 6건, Windows 세션 1건, 후보 0건, skip 0건
- 실제 기존 capture session 증분 sync: 새 공개 메시지 12건 수집, 기존 revision 2와 문서 ID 유지
- 현재 작업 세션과 증분 자료는 인증 테스트 문자열 때문에 서버 민감정보 검사에서 `QUARANTINED`; 보안 검사를 약화하지 않음
- 연결된 ADB 기기: 없음. 실제 기기 탭 UI 검증은 수동 절차로 남음
