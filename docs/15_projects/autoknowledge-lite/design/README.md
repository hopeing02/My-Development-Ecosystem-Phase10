# AutoKnowledge Lite 설계

## 구성

```text
Android 공유·클립보드
        ↓ HTTP
FastAPI 로컬 서버
        ├─ 작업 JSON
        ├─ 분석기(local/OpenAI/Claude)
        ├─ Markdown 생성
        └─ 개인 Vault 저장 및 선택적 Git 동기화
```

## 저장 경계

- 실행 코드: `apps/autoknowledge-lite/`
- 프로젝트 공식 문서: `docs/15_projects/autoknowledge-lite/`
- 개인 지식: `AUTOKNOWLEDGE_VAULT_DIR`가 가리키는 개인 Vault
- 실행 로그·작업 JSON·빌드 결과: Git 제외 로컬 경로

개인 Vault에는 개인 지식만 저장하고 프로젝트 설계·구현·테스트·사용법은 프로젝트 문서 영역에서만 관리한다.
