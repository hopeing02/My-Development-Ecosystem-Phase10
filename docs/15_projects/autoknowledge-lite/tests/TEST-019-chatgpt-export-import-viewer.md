# TEST-019 ChatGPT Export Import Viewer 검증

## 검증 범위

- 파일과 Control API Key가 모두 있어야 Import 활성화
- 선택한 ZIP을 Bearer 인증 binary request로 전달
- imported, partial, duplicate 형식 검증
- 부분 손상 경고를 원문 없이 표시
- API 오류 code와 안전한 message 표시
- key를 browser storage에 저장하지 않음
- 기존 Documents 화면으로 복귀 가능
- Knowledge Viewer TypeScript와 production build 검증

## 실행 명령

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\knowledge-viewer

npm test
# 10 files passed, 33 tests passed

npm run build
# TypeScript checks and Vite production build passed
```

Vite의 기존 500 kB chunk size 권고는 유지되며 build 실패는 아니다.
