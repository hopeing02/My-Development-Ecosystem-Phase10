# TEST-024 ChatGPT Shared Link Import Viewer 검증

## 검증 범위

- 명시적으로 입력한 Shared Link와 Control API Key 전달
- authenticated JSON body와 전용 API 경로
- 입력 전 Shared Link Import 비활성화
- Control API Key browser storage 미저장
- 기존 Export Import와 Documents navigation 회귀
- Viewer 전체 테스트와 production build

## 실행 명령

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\knowledge-viewer

npm test
# 10 files passed, 35 tests passed

npm run build
# TypeScript checks and Vite production build passed
```

Vite의 기존 500 kB chunk size 권고는 유지되며 build 실패는 아니다.
