from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .triage import InboxStore

store = InboxStore(Path(os.getenv("DB_PATH", "data/inbox.db")))
store.seed_demo_if_empty()

app = FastAPI(title="Multi-Agent Inbox Dashboard", version="2.0.0")

DASHBOARD_HTML = """<!doctype html>
<html lang="pt-BR" data-theme="dark">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Multi-Agent Inbox &amp; Lead Triage</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet" />
  <style>
    :root, [data-theme="dark"] {
      --bg: #050a0f;
      --surface: #0b1219;
      --surface-2: #111b24;
      --surface-hover: #172430;
      --text: #f0f7fc;
      --muted: #9ab3c8;
      --accent: #d4f1ff;
      --accent-ink: #050a0f;
      --accent-soft: rgba(212, 241, 255, 0.11);
      --accent-border: rgba(212, 241, 255, 0.34);
      --border: rgba(212, 241, 255, 0.14);
      --ok-bg: rgba(52, 211, 153, 0.15);
      --ok-text: #6ee7b7;
      --warn-bg: rgba(251, 191, 36, 0.15);
      --warn-text: #fcd34d;
      --err-bg: rgba(248, 113, 113, 0.15);
      --err-text: #fca5a5;
      --shadow: 0 24px 54px rgba(0, 0, 0, 0.55);
    }
    [data-theme="light"] {
      --bg: #f0f7fc;
      --surface: #ffffff;
      --surface-2: #e3eef6;
      --surface-hover: #d5e5f1;
      --text: #050a0f;
      --muted: #395064;
      --accent: #050a0f;
      --accent-ink: #f0f7fc;
      --accent-soft: rgba(5, 10, 15, 0.08);
      --accent-border: rgba(5, 10, 15, 0.3);
      --border: rgba(5, 10, 15, 0.14);
      --ok-bg: #ecfdf5;
      --ok-text: #047857;
      --warn-bg: #fffbeb;
      --warn-text: #b45309;
      --err-bg: #fef2f2;
      --err-text: #b91c1c;
      --shadow: 0 18px 40px rgba(5, 10, 15, 0.1);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 26px 18px 42px;
      transition: background-color 0.25s ease, color 0.25s ease;
    }
    .shell {
      max-width: 1180px;
      margin: 0 auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 20px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .shell-header {
      padding: 20px 26px;
      border-bottom: 1px solid var(--border);
      background: var(--surface-2);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }
    .brand { display: flex; align-items: center; gap: 0.8rem; }
    .logo-mark {
      width: 36px; height: 36px; border-radius: 10px;
      background: var(--accent); color: var(--accent-ink);
      display: grid; place-items: center; font-weight: 900; font-size: 0.9rem;
    }
    .brand-title { font-weight: 800; font-size: 1.08rem; }
    .brand-sub { font-size: 0.78rem; color: var(--muted); }

    .theme-btn {
      display: inline-flex; align-items: center; gap: 0.45rem;
      padding: 0.48rem 0.9rem; border-radius: 999px;
      border: 1px solid var(--accent-border); background: var(--surface); color: var(--text);
      font: inherit; font-size: 0.82rem; font-weight: 700; cursor: pointer;
    }
    .theme-btn:hover { background: var(--surface-hover); }

    .shell-body { padding: 24px 26px; }

    .kpi-grid {
      display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 0.9rem; margin-bottom: 20px;
    }
    .kpi {
      background: var(--surface-2); border: 1px solid var(--border);
      border-left: 4px solid var(--accent); border-radius: 12px; padding: 0.95rem 1.1rem;
    }
    .kpi-label { font-size: 0.72rem; color: var(--muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
    .kpi-val { font-size: 1.65rem; font-weight: 800; color: var(--accent); margin-top: 0.2rem; }

    .inbox-split {
      display: grid; grid-template-columns: 360px minmax(0, 1fr); gap: 18px;
      min-height: 470px;
    }
    .list-pane, .detail-pane {
      background: var(--surface-2); border: 1px solid var(--border);
      border-radius: 14px; padding: 16px; display: flex; flex-direction: column;
    }
    .search-input {
      width: 100%; padding: 0.58rem 0.85rem; border-radius: 9px;
      border: 1px solid var(--border); background: var(--bg); color: var(--text);
      font: inherit; font-size: 0.86rem; margin-bottom: 12px;
    }
    .conv-item {
      padding: 12px; border-radius: 10px; border: 1px solid var(--border);
      background: var(--surface); margin-bottom: 9px; cursor: pointer;
      transition: all 0.15s ease;
    }
    .conv-item:hover { background: var(--surface-hover); border-color: var(--accent-border); }
    .conv-item.active { border-color: var(--accent); border-left: 4px solid var(--accent); }
    .conv-name { font-weight: 700; font-size: 0.94rem; margin: 4px 0 2px; }
    .conv-preview { font-size: 0.8rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .badge {
      display: inline-block; font-family: "JetBrains Mono", monospace;
      font-size: 0.68rem; font-weight: 600; padding: 2px 7px; border-radius: 999px;
      background: var(--accent-soft); color: var(--accent); border: 1px solid var(--accent-border);
      margin-right: 4px;
    }
    .badge-ok { background: var(--ok-bg); color: var(--ok-text); border-color: transparent; }
    .badge-warn { background: var(--warn-bg); color: var(--warn-text); border-color: transparent; }

    .msg-bubble {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; padding: 14px 16px; margin: 12px 0; font-size: 0.92rem;
    }
    textarea {
      width: 100%; min-height: 110px; padding: 12px; border-radius: 10px;
      border: 1px solid var(--border); background: var(--bg); color: var(--text);
      font: inherit; font-size: 0.88rem; resize: vertical;
    }
    .guardrail-box {
      padding: 10px 14px; border-radius: 10px; font-size: 0.82rem; margin: 12px 0;
    }
    .guard-ok { background: var(--ok-bg); color: var(--ok-text); }
    .guard-block { background: var(--err-bg); color: var(--err-text); }

    .actions { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: auto; padding-top: 12px; }
    .btn {
      padding: 0.62rem 1.05rem; border-radius: 9px; border: 1px solid var(--border);
      background: var(--surface); color: var(--text); font: inherit; font-size: 0.84rem;
      font-weight: 700; cursor: pointer;
    }
    .btn-primary { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
    .mono { font-family: "JetBrains Mono", monospace; font-size: 0.76rem; color: var(--muted); }

    @media (max-width: 900px) {
      .kpi-grid { grid-template-columns: repeat(2, 1fr); }
      .inbox-split { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="shell-header">
      <div class="brand">
        <span class="logo-mark">IA</span>
        <div>
          <div class="brand-title">Multi-Agent Inbox &amp; Lead Triage</div>
          <div class="brand-sub">Roteamento por Intenção · Human-in-the-Loop · Guardrail CRM</div>
        </div>
      </div>
      <button id="themeToggle" class="theme-btn" type="button">
        <span id="themeIcon">☀</span>
        <span id="themeLabel">Modo Claro</span>
      </button>
    </header>

    <main class="shell-body">
      <section class="kpi-grid">
        <div class="kpi"><div class="kpi-label">Conversas</div><div class="kpi-val" id="kTotal">--</div></div>
        <div class="kpi"><div class="kpi-label">Em Triagem</div><div class="kpi-val" id="kTriage">--</div></div>
        <div class="kpi"><div class="kpi-label">No CRM</div><div class="kpi-val" id="kCrm">--</div></div>
        <div class="kpi"><div class="kpi-label">Sem WhatsApp</div><div class="kpi-val" id="kNoWa">--</div></div>
      </section>

      <section class="inbox-split">
        <aside class="list-pane">
          <input id="searchInput" class="search-input" placeholder="Filtrar contato, canal ou agente..." />
          <div id="convList"></div>
        </aside>
        <section class="detail-pane" id="detailPane">
          <p class="mono">Selecione uma conversa à esquerda.</p>
        </section>
      </section>
    </main>
  </div>

  <script>
    const root = document.documentElement;
    function applyTheme(t) {
      root.setAttribute("data-theme", t);
      localStorage.setItem("inbox-theme", t);
      document.getElementById("themeIcon").textContent = t === "light" ? "☾" : "☀";
      document.getElementById("themeLabel").textContent = t === "light" ? "Modo Escuro" : "Modo Claro";
    }
    applyTheme(localStorage.getItem("inbox-theme") || "dark");
    document.getElementById("themeToggle").addEventListener("click", () => {
      applyTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark");
    });

    let conversations = [];
    let selectedId = null;

    async function load() {
      conversations = await (await fetch("/api/conversations")).json();
      if (!selectedId && conversations.length) selectedId = conversations[0].conv_id;
      document.getElementById("kTotal").textContent = conversations.length;
      document.getElementById("kTriage").textContent = conversations.filter(c => c.status === "TRIAGE").length;
      document.getElementById("kCrm").textContent = conversations.filter(c => c.status === "PROMOTED_TO_CRM").length;
      document.getElementById("kNoWa").textContent = conversations.filter(c => !c.whatsapp_phone).length;
      renderList();
      renderDetail();
    }

    function renderList() {
      const q = document.getElementById("searchInput").value.trim().toLowerCase();
      const box = document.getElementById("convList");
      box.innerHTML = "";
      conversations.filter(c => !q || `${c.contact_name} ${c.channel} ${c.assigned_agent} ${c.last_message}`.toLowerCase().includes(q)).forEach(c => {
        const div = document.createElement("div");
        div.className = "conv-item" + (c.conv_id === selectedId ? " active" : "");
        const stBadge = c.status === "PROMOTED_TO_CRM" ? '<span class="badge badge-ok">CRM</span>' : '<span class="badge badge-warn">TRIAGE</span>';
        div.innerHTML = `
          <div><span class="badge">${c.assigned_agent}</span>${stBadge}</div>
          <div class="conv-name">${c.contact_name}</div>
          <div class="conv-preview">${c.last_message}</div>
        `;
        div.addEventListener("click", () => { selectedId = c.conv_id; renderList(); renderDetail(); });
        box.appendChild(div);
      });
    }

    function renderDetail() {
      const pane = document.getElementById("detailPane");
      const c = conversations.find(x => x.conv_id === selectedId);
      if (!c) { pane.innerHTML = '<p class="mono">Nenhuma conversa selecionada.</p>'; return; }
      const hasWa = Boolean(c.whatsapp_phone);
      const guardHtml = hasWa
        ? `<div class="guardrail-box guard-ok"><strong>✓ WhatsApp validado (${c.whatsapp_phone}):</strong> contato liberado para promoção ao CRM.</div>`
        : `<div class="guardrail-box guard-block"><strong>✕ Guardrail ativo:</strong> sem WhatsApp validado — promoção ao CRM bloqueada até captura do telefone.</div>`;
      pane.innerHTML = `
        <div><span class="badge">${c.assigned_agent}</span><span class="badge">${c.channel}</span><span class="mono">${c.conv_id}</span></div>
        <h2 style="margin:8px 0 4px">${c.contact_name}</h2>
        <div class="msg-bubble"><strong>Mensagem recebida:</strong><br />${c.last_message}</div>
        <label class="mono" style="margin-bottom:6px;display:block">Rascunho sugerido pelo agente (revisão humana):</label>
        <textarea id="replyBox">${c.suggested_reply}</textarea>
        ${guardHtml}
        <div class="actions">
          <button class="btn btn-primary" onclick="promote('${c.conv_id}')">Promover ao CRM</button>
          <button class="btn" onclick="alert('Resposta aprovada na fila de envio!')">Aprovar Resposta IA</button>
        </div>
      `;
    }

    async function promote(id) {
      const r = await fetch(`/api/conversations/${id}/promote`, { method: "POST" });
      const data = await r.json();
      if (!r.ok) alert(data.detail); else load();
    }

    document.getElementById("searchInput").addEventListener("input", renderList);
    load();
  </script>
</body>
</html>
"""


class IncomingMessage(BaseModel):
    conv_id: str
    channel: str
    contact_name: str
    message_text: str
    whatsapp_phone: str = ""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return DASHBOARD_HTML


@app.get("/api/conversations")
def list_conversations() -> list[dict[str, Any]]:
    return store.list_conversations()


@app.post("/api/conversations")
def create_conversation(body: IncomingMessage) -> dict[str, Any]:
    return store.ingest_message(
        conv_id=body.conv_id,
        channel=body.channel,
        contact_name=body.contact_name,
        message_text=body.message_text,
        whatsapp_phone=body.whatsapp_phone,
    )


@app.post("/api/conversations/{conv_id}/promote")
def promote_conversation(conv_id: str) -> dict[str, Any]:
    try:
        return store.promote_to_crm(conv_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
