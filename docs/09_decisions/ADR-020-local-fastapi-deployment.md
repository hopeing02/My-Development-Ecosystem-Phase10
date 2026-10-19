# ADR-020 로컬 FastAPI 배포 계약

- 일자: 2026-10-19 (Asia/Seoul)
- 범위: 사용자가 지정한 현재 PC의 로컬 FastAPI 서비스
- 결정: 기존 Plugin·Workflow·Git·TaskExecutionLock에 연결하는 최소 배포 어댑터

## 입력과 출력

입력은 서비스 이름, module:app, 저장소 내 app-dir, Python 실행 파일, health-path,
시작 제한 시간이다. 커밋된 HEAD와 깨끗한 작업 트리만 배포한다. 설치·빌드는 기존
검증 환경 책임이며 배포 중 pip 설치나 의존성 갱신은 하지 않는다.
출력은 commit, PID·생성 시각, snapshot 위치, loopback URL과 health 상태다.

Git archive로 추적 코드만 `.mde/deployments/<name>/releases/`에 분리한다.
원본 Vault·작업 트리·기존 서비스를 수정하지 않는다. 후보는 새 127.0.0.1 포트에서
실행하며 프로세스 소유·listen·HTTP 200을 확인한 뒤 원자적으로 current를 바꾼다.
실패 시 후보만 종료하고 기존 current는 그대로 둔다. 이전 정상 프로세스는 rollback용으로
유지한다. 고정 URL의 트래픽 전환과 로그인 시 자동 실행은 이번 계약에 포함하지 않는다.

## 재사용 및 신규 필요성

기존 Git 경계, TaskExecutionLock, Uvicorn, CommandRegistry와 runtime Plugin을 사용한다.
기존 Viewer PowerShell은 고정 경로·포트·앱 전용 supervisor이므로 교체하지 않는다.
범용 snapshot 배포·건강 확인·소유 검증·rollback 경계는 없어 신규 source 모듈 1개가
필요하다. PID 재사용을 확인하고 소유 자식 프로세스까지 종료하기 위해 psutil을 고정
의존성으로 추가한다. 새 Agent·RAG·Vector DB·오케스트레이션 프레임워크는 도입하지 않는다.

## 실행 범위

명시적인 CLI 배포와 deploy.local Workflow handler를 제공한다. 기본 feature Workflow는
변경하지 않으며 handler는 실제 테스트 성공 결과와 현재 커밋 일치를 요구한다.
별도 feature-local Workflow 및 입력 JSON을 통해 기존 자동 수정 실행기에 연결한다.
기존 리뷰의 무조건 승인은 제거하고 실제 생성 파일과 명시적 boolean approved 판정을
요구한다. 거절·누락 시 적용 이전에 중단한다. 실 AI end-to-end 검증은 별도 미완료다.
일반 deploy 명령은 사용자 지정 커밋의 로컬 실행이며 전체 자동 개발 성공을 뜻하지 않는다.
