"""Static PC capture page for the local AutoKnowledge server."""

PC_CAPTURE_HTML = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoKnowledge Lite</title>
  <style>
    :root {
      color-scheme: light;
      font-family: "Segoe UI", "Malgun Gothic", sans-serif;
      background: #eef2f7;
      color: #172033;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
    }
    main {
      width: min(720px, 100%);
      background: #ffffff;
      border: 1px solid #d9e1ec;
      border-radius: 20px;
      padding: 28px;
      box-shadow: 0 18px 50px rgba(36, 53, 80, 0.12);
    }
    h1 { margin: 0 0 8px; font-size: 28px; }
    .subtitle { margin: 0 0 24px; color: #5f6c80; }
    label {
      display: block;
      margin: 18px 0 8px;
      font-weight: 700;
    }
    input, select, textarea, button {
      width: 100%;
      font: inherit;
      border-radius: 12px;
    }
    input, select, textarea {
      border: 1px solid #c8d2e0;
      padding: 12px 14px;
      background: #ffffff;
      color: #172033;
    }
    textarea { min-height: 240px; resize: vertical; line-height: 1.55; }
    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 20px;
    }
    button {
      border: 0;
      padding: 13px 16px;
      cursor: pointer;
      font-weight: 700;
    }
    #paste-button { background: #e7edf6; color: #263651; }
    #save-button { background: #2f66d0; color: #ffffff; }
    button:disabled { cursor: wait; opacity: 0.65; }
    #message {
      min-height: 24px;
      margin: 18px 0 0;
      padding: 12px 14px;
      border-radius: 12px;
      background: #f4f7fb;
      color: #43516a;
    }
    #message.success { background: #e7f7ed; color: #176636; }
    #message.error { background: #fff0f0; color: #a22c2c; }
    .hint { margin-top: 8px; color: #6b778c; font-size: 13px; }
    .parent-box {
      border: 1px solid #d9e1ec;
      border-radius: 14px;
      padding: 14px;
      background: #f8fafe;
    }
    #parent-results { display: grid; gap: 8px; margin-top: 10px; }
    #parent-results button {
      text-align: left;
      border: 1px solid #d4ddeb;
      background: #ffffff;
      color: #172033;
    }
    #parent-results button strong, #parent-results button small { display: block; }
    #parent-results button small { margin-top: 4px; color: #6b778c; }
    #selected-parent { margin: 10px 0 0; color: #2458b3; font-weight: 700; }
    #clear-parent { width: auto; margin-top: 8px; padding: 8px 10px; background: #e7edf6; }
    @media (max-width: 560px) {
      main { padding: 20px; }
      .actions { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <h1>AutoKnowledge Lite</h1>
    <p class="subtitle">PC 클립보드나 직접 입력한 내용을 개인 Vault에 저장합니다.</p>

    <form id="capture-form">
      <label for="title">제목 <span class="hint">(선택)</span></label>
      <input id="title" name="title" maxlength="200" autocomplete="off">

      <label for="target-folder">저장 폴더</label>
      <select id="target-folder" name="target_folder">
        <option value="00_Inbox">00_Inbox — 기본 받은함</option>
        <option value="10_Life">10_Life — 생활·일상</option>
        <option value="20_Learning">20_Learning — 학습·연구</option>
        <option value="30_Interests">30_Interests — 관심사</option>
        <option value="40_Reference">40_Reference — 참고자료</option>
        <option value="90_Archive">90_Archive — 보관</option>
      </select>

      <label for="parent-search">이 문서를 참조할 상위 주제 문서 <span class="hint">(선택)</span></label>
      <div class="parent-box">
        <input id="parent-search" type="search" autocomplete="off"
          placeholder="제목·별칭·경로로 기존 문서 검색">
        <div id="parent-results" aria-live="polite"></div>
        <p id="selected-parent">선택 안 함 — 직전에 웹에서 저장한 문서를 자동으로 연결합니다.</p>
        <button id="clear-parent" type="button" hidden>선택 해제</button>
      </div>

      <label for="content">저장할 내용</label>
      <textarea id="content" name="content" required
        placeholder="내용을 직접 입력하거나 클립보드 붙여넣기를 누르세요."></textarea>
      <p class="hint">클립보드는 버튼을 누를 때만 읽습니다.</p>

      <div class="actions">
        <button id="paste-button" type="button">클립보드 붙여넣기</button>
        <button id="save-button" type="submit">Vault에 저장</button>
      </div>
    </form>
    <p id="message" role="status" aria-live="polite">저장할 내용을 준비하세요.</p>
  </main>

  <script>
    const form = document.querySelector("#capture-form");
    const title = document.querySelector("#title");
    const content = document.querySelector("#content");
    const targetFolder = document.querySelector("#target-folder");
    const pasteButton = document.querySelector("#paste-button");
    const saveButton = document.querySelector("#save-button");
    const message = document.querySelector("#message");
    const parentSearch = document.querySelector("#parent-search");
    const parentResults = document.querySelector("#parent-results");
    const selectedParentText = document.querySelector("#selected-parent");
    const clearParent = document.querySelector("#clear-parent");
    let selectedParent = null;
    let searchTimer = null;

    function showMessage(text, kind = "") {
      message.textContent = text;
      message.className = kind;
    }

    pasteButton.addEventListener("click", async () => {
      try {
        content.value = await navigator.clipboard.readText();
        content.focus();
        showMessage("클립보드 내용을 불러왔습니다.", "success");
      } catch {
        showMessage("브라우저가 클립보드 읽기를 허용하지 않았습니다. 직접 붙여넣어 주세요.", "error");
      }
    });

    function selectParent(document) {
      selectedParent = document;
      selectedParentText.textContent = `선택한 상위 주제: ${document.title} · ${document.relative_path}`;
      clearParent.hidden = false;
      parentResults.replaceChildren();
      parentSearch.value = "";
    }

    clearParent.addEventListener("click", () => {
      selectedParent = null;
      selectedParentText.textContent = "선택 안 함 — 직전에 웹에서 저장한 문서를 자동으로 연결합니다.";
      clearParent.hidden = true;
      parentSearch.focus();
    });

    parentSearch.addEventListener("input", () => {
      window.clearTimeout(searchTimer);
      const query = parentSearch.value.trim();
      if (!query) {
        parentResults.replaceChildren();
        return;
      }
      searchTimer = window.setTimeout(async () => {
        try {
          const response = await fetch(`/v1/knowledge/documents?q=${encodeURIComponent(query)}`);
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const result = await response.json();
          parentResults.replaceChildren();
          for (const candidate of result.documents) {
            const item = window.document.createElement("button");
            item.type = "button";
            const name = window.document.createElement("strong");
            name.textContent = candidate.title;
            const path = window.document.createElement("small");
            path.textContent = candidate.relative_path;
            item.append(name, path);
            item.addEventListener("click", () => selectParent(candidate));
            parentResults.append(item);
          }
          if (!result.documents.length) parentResults.textContent = "검색 결과가 없습니다.";
        } catch {
          parentResults.textContent = "상위 주제 문서를 검색하지 못했습니다.";
        }
      }, 300);
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = content.value.trim();
      if (!text) {
        showMessage("저장할 내용을 입력하세요.", "error");
        content.focus();
        return;
      }

      saveButton.disabled = true;
      showMessage("저장 중입니다...");
      try {
        const response = await fetch("/v1/share", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            content: text,
            title: title.value.trim() || null,
            target_folder: targetFolder.value,
            capture_origin: "pc_clipboard",
            parent_document_id: selectedParent ? selectedParent.id : null
          })
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const result = await response.json();
        showMessage(`저장 요청 완료: ${targetFolder.value} · ${result.job_id}`, "success");
        title.value = "";
        content.value = "";
        selectedParent = null;
        selectedParentText.textContent = "선택 안 함 — 직전에 웹에서 저장한 문서를 자동으로 연결합니다.";
        clearParent.hidden = true;
      } catch {
        showMessage("저장하지 못했습니다. 서버 상태를 확인하세요.", "error");
      } finally {
        saveButton.disabled = false;
      }
    });
  </script>
</body>
</html>
"""
