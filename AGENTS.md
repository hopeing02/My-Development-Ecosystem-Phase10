# MDE AI Development Instructions

모든 실제 코드 구현은 아래 공식 지침을 따른다.

- docs/04\_development/DEV-001-development-standard.md

핵심 원칙:

1. 설계 반복보다 실행 가능한 코드 구현을 우선한다.
2. 한 번에 작고 커밋 가능한 단위로 개발한다.
3. 소스 코드에는 테스트를 포함한다.
4. CON → GOV → STD → DEV → CMD → PRM → ARCH → SDS → ADR → QA → CODE → TEST → RELEASE 순서를 준수한다.
5. 구조 변경, CON/GOV 변경, 대규모 폴더 이동은 임의로 수행하지 않는다.
6. 기존 파일을 수정할 때는 전체 파일 내용과 테스트·커밋 명령을 제공한다.
