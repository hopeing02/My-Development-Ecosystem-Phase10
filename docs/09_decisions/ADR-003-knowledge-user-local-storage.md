# ADR-003 Knowledge 사용자 전역 저장과 Source 격리

- 버전: 1.0.0
- 상태: Accepted
- 작성일: 2026-07-22

## 결정

Knowledge Source 설정과 SQLite 색인을 프로젝트가 아닌 `~/.mde/knowledge/`에 저장한다. 하나의 DB를 사용하되 모든 관련 테이블과 쿼리를 `source_id`로 격리한다.

## 이유

개인·업무 경로와 원문 색인이 Git에 포함되는 것을 방지하고 여러 MDE 프로젝트에서 같은 Source를 재사용하기 위해서다. 단일 DB는 v1 운영 복잡도를 줄이며 Source 격리는 동일 파일명 충돌과 잘못된 교차 삭제를 막는다.

## 대안

- 프로젝트 내부 `.mde/knowledge`: Git 노출 위험 때문에 거절
- Category별 DB: v1 범위를 넘어 다음 버전 후보로 보류
- Core Plugin 프레임워크 확장: 현재 CLI 기능에 비해 과도하여 거절

## 영향

사용자는 로컬 DB가 원문을 포함할 수 있음을 인지해야 한다. 백업·삭제·암호화는 v1 범위 밖이며 Source 간 링크는 자동 연결하지 않는다.
