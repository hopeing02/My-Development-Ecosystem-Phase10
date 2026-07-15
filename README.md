# MDE Tools v1

압축을 **MDE GitHub 저장소의 루트**에 풀면 `tools/` 폴더가 생성됩니다.

```text
My-Development-Ecosystem/
└── tools/
    ├── init_repository.py
    ├── create_project.py
    ├── create_document.py
    └── mde_toolkit/
```

초기화:

```powershell
python tools\init_repository.py
```

새 프로젝트 생성:

```powershell
python tools\create_project.py --name senior-matching --type python
```

도구 테스트:

```powershell
python -m unittest discover -s tools\tests -v
```
