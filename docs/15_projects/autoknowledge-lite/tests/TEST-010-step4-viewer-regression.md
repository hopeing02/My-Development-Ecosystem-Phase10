# TEST-010 Step 4 Knowledge Viewer 회귀검증

- 실행일: 2026-08-18
- 상태: Passed

## 검증 범위

- 자료가 있는 Codex 세션의 개요·대화·변경 파일·명령·테스트 표시
- 자료가 없는 세션의 탭별 empty state
- 관계가 없는 세션 그래프의 empty state
- Session 각 탭에서 관련 Task 상세 이동
- Task 상세에서 원본 세션 자료 복귀
- Task 중심 그래프 이동
- 기존 Session·Project·Document·File·Command·Test 노드 보존
- 신규 Session→Task와 Task→File/Command/Test 관계
- 빈 세션에는 Task를 생성하지 않는 무결성

## 자동 검증

```powershell
uv run --project apps/autoknowledge-lite pytest apps/autoknowledge-lite/tests
npm test --prefix apps/knowledge-viewer
npm run build --prefix apps/knowledge-viewer
uv run pytest packages/mde-core/tests/knowledge
```

개별 탭과 그래프는 실제 Capture API와 같은 형태의 populated/empty fixture를 사용한다.
원본 본문·파일 경로·명령·테스트 결과가 응답과 Viewer에서 유지되는지 확인한다.
