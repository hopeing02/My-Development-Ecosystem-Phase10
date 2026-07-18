# autoknowledge-lite — DB

MVP는 데이터베이스 대신 작업별 UTF-8 JSON 파일을 사용합니다.

- 기본 경로: `apps/autoknowledge-lite/data/`
- 환경변수: `AUTOKNOWLEDGE_DATA_DIR`
- 파일명: `{job_id}.json`
- 저장 방식: 임시 파일 작성 후 원자적 교체

접수 시 작업 ID, 상태, 접수 시각과 원문을 저장합니다. 분석 후에는 상태를 `processed`로 바꾸고 `processed_at`과 `analysis`를 같은 레코드에 추가합니다.
