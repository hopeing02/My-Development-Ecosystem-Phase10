name: MDE CI

on:
  pull_request:
    branches:
      - main

permissions:
  contents: read

jobs:
  verify:
    runs-on: windows-latest
    steps:
      - name: Check out project
        uses: actions/checkout@v4

      - name: Check out MDE Core
        uses: actions/checkout@v4
        with:
          repository: ${{ vars.MDE_CORE_REPOSITORY }}
          ref: ${{ vars.MDE_CORE_REF }}
          path: _mde-core

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "17"

      - name: Install uv
        run: python -m pip install uv

      - name: Install MDE Core
        run: python -m pip install ./_mde-core

      - name: Run project tests
        run: mde test

      - name: Run project build
        run: mde build
