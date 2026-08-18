# CODE-019 ChatGPT Export Import Viewer

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

기존 Knowledge Viewer의 문서와 Capture 탐색을 유지하면서 사용자가 ChatGPT Data
Export ZIP을 명시적으로 선택해 로컬 Import API로 전달할 수 있게 한다.

## 구현

- 기존 상단 탐색에 `ChatGPT` 메뉴 추가
- ZIP 파일과 Control API Key를 모두 입력한 경우에만 가져오기 활성화
- ZIP을 binary body로 기존 `POST /api/v1/chatgpt/imports`에 전달
- imported, partial, duplicate 결과와 세션 수, 격리 경고 표시
- 기존 Documents, Capture 화면과 상태 변경 없이 독립 패널로 구성

## 보안과 원본 보존

- Control API Key를 component memory에서만 사용
- localStorage와 sessionStorage에 key 또는 원문을 기록하지 않음
- Viewer가 ZIP을 해석하거나 원본을 수정하지 않고 로컬 Import API에만 전달
- 응답에 포함된 식별자와 경고 코드만 표시하고 원문 또는 raw 저장 경로는 표시하지 않음
