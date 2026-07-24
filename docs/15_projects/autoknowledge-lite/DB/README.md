# AutoKnowledge Lite 데이터 저장

MVP는 데이터베이스 대신 작업별 UTF-8 JSON 파일을 사용한다.

- 기본 경로: `apps/autoknowledge-lite/data/`
- 경로 재정의: `AUTOKNOWLEDGE_DATA_DIR`
- 파일명: `{job_id}.json`
- 저장 방식: 임시 파일 작성 후 원자적 교체

접수 시 작업 ID, 상태, 접수 시각과 원문을 저장한다. 분석 후에는 `processed_at`과 분석 결과를 추가하고, Markdown 생성 후에는 완성 문서와 실제 Vault 파일 경로를 기록한다. 작업 JSON은 개인 원문을 포함할 수 있으므로 Git에서 제외한다.
