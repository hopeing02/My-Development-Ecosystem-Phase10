# STD-004 Capture 텍스트 정규화

- 상태: Active
- 적용 계약: Capture Schema `1.0`

## 규칙

Android와 서버는 다음 순서로 클립보드 본문을 정규화한다.

1. CRLF와 CR을 LF로 바꾼다.
2. 전체 문자열의 앞뒤 공백을 제거한다.
3. 코드 블록 밖의 줄 끝 공백을 제거한다.
4. 빈 줄은 연속 두 줄까지만 유지한다.
5. 펜스 코드 블록 안의 들여쓰기와 줄 끝 공백은 보존한다.
6. Unicode 문자는 별도 호환 정규화 없이 원문 코드 포인트를 보존한다.

정규화 결과의 UTF-8 바이트에 SHA-256을 적용한 값이 서버의 최종
`serverContentHash`다. 플랫폼 공통 예제는
`packages/capture-core/test-vectors/normalization.json`과 `hashes.json`을 단일
기준으로 사용한다.

## 제한

펜스는 줄의 공백을 제외한 첫 토큰이 `````인 경우 토글한다. 중첩 펜스와 물결표
펜스는 Schema 1.0에서 별도 해석하지 않는다.
