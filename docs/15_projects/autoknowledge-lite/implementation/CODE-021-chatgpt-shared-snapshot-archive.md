# CODE-021 ChatGPT Shared Snapshot Fetch와 Archive

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

사용자가 명시적으로 제출한 ChatGPT Shared Link 1건만 제한적으로 조회하고, 분석보다
먼저 응답 원본을 immutable local raw snapshot으로 보존한다.

## Fetch 경계

- canonical `https://chatgpt.com/share/<conversation-ID>`만 요청
- cookie, ChatGPT 로그인 credential과 Authorization을 사용하지 않음
- redirect도 동일 conversation ID의 canonical URL만 허용
- 최대 3회 redirect, 20초 timeout
- `text/html`, `application/json`만 허용
- Content-Length 사전 제한과 streaming byte 제한을 함께 적용

## Archive

- `raw/chatgpt/shared/{content-hash import id}/snapshot.html`에 원문 저장
- staging directory, fsync와 atomic rename 사용
- snapshot과 manifest 권한을 local user 전용으로 제한
- content hash 기반 중복 방지와 기존 Archive 무결성 재검증
- manifest에는 공개 link token 대신 SHA-256 hash만 기록
- 판독 또는 AI 분석 전에 raw snapshot 저장 가능

자동 polling, sidebar 조회와 비공개 ChatGPT 계정 접근은 수행하지 않는다.
