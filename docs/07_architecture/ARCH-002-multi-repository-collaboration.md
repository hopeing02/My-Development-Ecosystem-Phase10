# ARCH-002 다중 저장소 협업 아키텍처

## 1. 구성

```text
mde-core repository
  MDE CLI / Agent / Workflow / Template
             |
             | reads configuration and executes policy
             v
project repository A        project repository B
  .mde/project.yaml           .mde/project.yaml
  tasks/pending/*.yaml        tasks/pending/*.yaml
  source / tests              source / tests
```

## 2. 책임 경계

- MDE Core는 설정 해석, 정책 검증, 작업 실행을 담당한다.
- 프로젝트 저장소는 제품 코드, 작업 파일, 프로젝트별 명령을 소유한다.
- GitHub는 사용자 인증, Pull Request, 승인, 기본 브랜치 보호를 담당한다.
- MDE Core는 프로젝트 저장소의 원격 권한이나 GitHub 계정을 대신 관리하지 않는다.

## 3. 실행 흐름

```text
작업 YAML 로드
→ project.yaml 로드
→ assignee와 작업 브랜치 검증
→ Workflow 실행
→ test/build 명령 실행
→ 작업 브랜치 push
→ Pull Request 및 GitHub 필수 검사
→ 승인 후 main 병합
```

## 4. 의존 방향

`CLI → project config / task → workflow → plugins → git` 방향을 유지한다. 프로젝트 설정 모듈은 CLI 또는 Git 모듈을 import하지 않는다.
