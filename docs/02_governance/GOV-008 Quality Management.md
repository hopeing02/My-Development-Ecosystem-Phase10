이 문서는

앞으로 생성되는 모든 Python 코드의 품질 기준

입니다.

예를 들어

CODE-010

execution_context.py

를 작성하면

자동으로

QA-001을 검사합니다.

QA-001에서 정의될 내용
1.

Python Version

Python 3.12+
2.

Formatting

Black

필수

3.

Lint

Ruff

오류 0개

4.

Type Hint

100%
5.

Docstring

모든

Module
Class
Method

필수

6.

Testing

pytest

필수

7.

Coverage

90%

목표

95%
8.

Logging

print 사용 금지

Logger 사용

9.

Exception

Exception 직접 사용 금지

AppException

상속

10.

Architecture

순환 Import

금지

11.

Complexity

Cyclomatic Complexity

10 이하

12.

Function

함수

30줄 이하

13.

Class

300줄 이하

14.

File

500줄 이하

15.

Review

AI Review

필수

그러면

앞으로

CODE-010

↓

QA 검사

↓

통과

↓

Git Commit

이 자동으로 됩니다.

그리고 제가 정말 만들고 싶은 것은 이것입니다.
/build

↓

Workflow

↓

Code Generate

↓

QA Check

↓

Fix

↓

QA Check

↓

Git

↓

Release

즉

AI가

코드 생성

↓

스스로 검사

↓

스스로 수정

↓

다시 검사

↓

GitHub Commit

까지 하는 구조입니다.