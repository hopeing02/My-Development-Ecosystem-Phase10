# ADR-007 보안 Category별 Git Vault 저장소 분리

- 상태: Accepted
- 작성일: 2026-07-22

## 배경

개인, 업무, 개발, 프로젝트, 공유 문서는 접근 권한과 외부 공유 정책이 다르다. 하나의 Git Vault에 서로 다른 보안 Category를 함께 저장하면 개인 자료가 업무 저장소에 포함되거나 업무 자료가 개인 Git 원격으로 전송될 위험이 있다. MDE Source Category만으로는 Git 원격의 접근 권한을 강제할 수 없다.

## 결정

- `personal`과 `work`는 반드시 별도의 Git 저장소 또는 로컬 저장소로 분리한다.
- 업무 Vault는 회사 정책이 허용한 저장소만 사용하고 개인 Git 원격과 결합하지 않는다.
- `project`와 `shared`는 공유 대상과 권한이 다르면 별도 저장소로 분리한다.
- 같은 접근 권한을 가진 개인 주제는 한 개인 Vault 안에서 폴더와 태그로 분류할 수 있다.
- AutoKnowledge 개인 Vault의 활성 원본은 MDE 코드 저장소 밖의 사용자 전용 경로에 둔다.
- MDE Knowledge Plugin은 외부 원본을 복사하거나 Git 동기화하지 않고 등록·색인·검색만 수행한다.
- 이전 검증이 끝날 때까지 기존 원본은 복구용으로 보존한다.

## 결과

AutoKnowledge 애플리케이션 코드와 개인 지식 Git 저장소의 경계가 분리된다. 개인 Source는 `sensitive=true`, `allow_agent_access=false`를 유지하며, 기본 검색과 Agent 자동 접근에서 제외된다.

## 대안

하나의 Git 저장소에서 Category별 폴더만 나누는 방식은 Git 원격과 접근 권한이 저장소 단위로 적용되므로 채택하지 않았다. 모든 주제를 각각 별도 저장소로 만드는 방식은 같은 보안 경계 안에서 관리 비용이 커져 필수로 정하지 않았다.
