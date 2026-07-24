# ADR-011 AutoKnowledge Lite 모노레포 통합

- 상태: Accepted
- 결정일: 2026-07-23

## 배경

AutoKnowledge Lite의 실행 가능한 Python·Android 구현은 별도 로컬 저장소인 `.runtime/autoknowledge-lite/`에 있고, MDE 모노레포의 `apps/autoknowledge-lite/`에는 프로젝트 골격만 존재했다. 이 구조에서는 공식 코드 위치와 프로젝트 문서 위치가 분리되고, 별도 저장소의 중복 문서가 `docs/15_projects/autoknowledge-lite/` 단일 원본 원칙과 충돌한다.

## 결정

- AutoKnowledge Lite의 공식 소스와 테스트는 `apps/autoknowledge-lite/`에서 관리한다.
- 프로젝트 설계·구현·테스트·사용법·릴리스 문서는 `docs/15_projects/autoknowledge-lite/`를 단일 원본으로 사용한다.
- 개인 지식 원본과 생성된 개인 Markdown은 프로젝트 문서 영역에 넣지 않는다.
- 개인 Vault, 작업 JSON, 실행 로그, 가상환경, 빌드 결과는 Git에서 제외한다.
- 기존 Vault Git 동기화 정책과 사용자 환경 설정은 이번 통합에서 변경하지 않는다.
- `.runtime/autoknowledge-lite/`는 통합 검증 전까지 복구용 원본으로 보존하며 자동 삭제하지 않는다.

## 결과

AutoKnowledge Lite는 MDE가 관리하는 하나의 프로젝트가 되지만 개인 지식과 프로젝트 개발 기록의 보안 경계는 유지된다. MDE Knowledge Plugin은 개인 Vault를 `personal` Source로 색인하고, 프로젝트 문서는 기존 `mde-docs` Source를 통해 색인한다.

## 제외 범위

- 개인 Vault 파일 이동·수정·삭제
- Vault Git 동기화 비활성화 또는 원격 저장소 변경
- AI 공급자 변경
- 별도 저장소와 원격 저장소 삭제
