# TEST-011 Codex Activity Record Projection

- 작성일: 2026-08-18
- 대상: `CodexKnowledgeAdapter`

## 실행 명령

```powershell
uv run --project apps/autoknowledge-lite pytest apps/autoknowledge-lite/tests/test_codex_knowledge_adapter.py -q
uv run --project apps/autoknowledge-lite pytest apps/autoknowledge-lite/tests -q
uv run --project apps/autoknowledge-lite ruff check apps/autoknowledge-lite/src/autoknowledge_lite/codex_knowledge_adapter.py apps/autoknowledge-lite/tests/test_codex_knowledge_adapter.py
uv run --project apps/autoknowledge-lite black --check apps/autoknowledge-lite/src/autoknowledge_lite/codex_knowledge_adapter.py apps/autoknowledge-lite/tests/test_codex_knowledge_adapter.py
```

## 기대 결과

- 기존 Session·Message 투영이 유지된다.
- Command·File·Test와 Activity가 공통 모델 검증을 통과한다.
- 입력 payload는 변경되지 않는다.
- 손상된 개별 레코드는 warning으로 격리된다.
- 기존 AutoKnowledge-Lite 테스트에 회귀가 없다.
