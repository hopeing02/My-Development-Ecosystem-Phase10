# GUIDE-005 Obsidian 지식 그래프 사용법

- 버전: 0.3.0
- 상태: Active

## Vault 열기

Obsidian에서 `Open folder as vault`를 선택하고 사용자 전용 외부 Vault를 연다.

```text
C:\Users\<user>\Knowledge\Personal-Vault
```

MDE 저장소 내부 `apps/autoknowledge-lite/vault`는 복구용 보존본이므로 활성
Obsidian Vault로 사용하지 않는다.

## 자동 구성

다음 핵심 플러그인이 Vault 설정에 포함된다.

- Backlinks
- Outgoing links
- Graph view
- Properties view
- Bases
- Templates

새 AutoKnowledge 노트에는 다음 항목이 자동 생성된다.

- 짧은 `aliases`
- 공백 없는 정규화 `tags`
- `type`, `status`, `reviewed`
- MOC 링크가 포함된 `topics`
- 마지막 `## 연결` 구역

## 시작 화면

- `_Home.md`: 전체 주제 지도
- `Knowledge Dashboard.md`: 받은함, 최근 자료, 미검토 자료, 주제별 자료,
  중복 후보 Bases

처음에는 `Knowledge Dashboard`에서 `status: to-review` 노트를 검토한다.
검토가 끝나면 `reviewed: true`로 바꾸고 필요하면 `status`를 정정한다.

## 그래프

기본 그래프는 `90_Archive`와 `integration-test` 태그를 제외하고 폴더별
색상을 사용한다. Local Graph 깊이 1~2에서 현재 노트의 MOC와 관련 개념을
먼저 탐색한다.

## 기존 Vault 재정리

기본 실행은 미리보기다.

```powershell
$env:PYTHONPATH="apps/autoknowledge-lite/src"
apps/autoknowledge-lite/.venv/Scripts/python.exe `
  apps/autoknowledge-lite/scripts/organize-vault.py `
  --vault $env:AUTOKNOWLEDGE_VAULT_DIR
```

실제 적용은 Git 작업 트리가 깨끗한지 확인한 뒤 `--apply`를 추가한다.

Obsidian 설정만 다시 확인하려면 `setup-obsidian.py`를 같은 방식으로 실행한다.
기존 `graph.json`이 있으면 자동으로 덮어쓰지 않는다.
