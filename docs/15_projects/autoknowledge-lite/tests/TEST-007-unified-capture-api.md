# TEST-007 공통 Capture API와 Android 전환

- 테스트일: 2026-08-02

## 검증 범위

- Schema 필수값과 enum 오류의 표준 응답
- clipboard 저장, source/front matter, 상위 문서 연결
- 서버 재계산 해시와 불일치 warning
- captureId 멱등성과 본문 중복 분리
- 민감정보 원문 비노출 차단
- 상대·절대·드라이브·상위 경로 및 심볼릭 링크 탈출 차단
- development_session 계약 검증 후 명시적 501
- `/v1/share` Android Legacy Adapter와 응답 호환
- Android DTO 매핑, saved/duplicate/4xx/5xx 상태 변환
- Python과 Android의 공통 정규화 벡터

## 실행 명령

```powershell
cd apps/autoknowledge-lite
uv run pytest
uv run ruff check .
uv run black --check --fast .

cd android
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
.\gradlew.bat testDebugUnitTest assembleDebug --no-daemon
```

실제 기기 연결이 없는 환경에서는 ChatGPT/Codex 클립보드 복사, 서버 중단 후 큐
재전송과 설정 플래그 롤백은 APK 설치 후 수동 검증 대상으로 남는다.

## 결과

- AutoKnowledge Lite Python 전체: 96 passed, 1 skipped, 실패 0
- Ruff 전체: 통과
- 이번 단계 Python 파일 Black: 통과
- 전체 Black: 기존 미커밋 `mde_client.py`, `test_mde_client.py`, `test_api.py`의
  포맷 차이로 실패했으며 보존 지침에 따라 수정하지 않음
- Android JUnit: 19 passed, 실패 0
- Debug APK: 빌드 성공
- 심볼릭 링크 탈출 테스트: Windows의 심볼릭 링크 생성 권한 부재로 1건 스킵
