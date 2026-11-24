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

app = FastAPI(title="Multi-Agent Inbox Dashboard", version="1.0.0")

DASHBOARD_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>Multi-Agent Inbox Dashboard</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 2rem; }
    h1 { color: #38bdf8; margin-top: 0; }
    .card { background: #1e293b; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; background: #334155; margin-right: 6px; }
    button { background: #38bdf8; color: #0f172a; border: 0; padding: 6px 12px; border-radius: 6px; font-weight: 700; cursor: pointer; }
  </style>
</head>
<body>
  <h1>Multi-Agent Inbox & Lead Triage</h1>
  <div id="list">Carregando conversas...</div>
  <script>
    async function load() {
      const items = await (await fetch('/api/conversations')).json();
      const box = document.getElementById('list');
      box.innerHTML = '';
      items.forEach(c => {
        const div = document.createElement('div');
        div.className = 'card';
        div.innerHTML = `
          <div><span class="badge">${c.assigned_agent}</span><span class="badge">${c.channel}</span><span class="badge">${c.status}</span></div>
          <h3>${c.contact_name} ${c.whatsapp_phone ? '(' + c.whatsapp_phone + ')' : '(sem WhatsApp)'}</h3>
          <p><strong>Mensagem:</strong> ${c.last_message}</p>
          <p><strong>Sugestão IA:</strong> ${c.suggested_reply}</p>
          <button onclick="promote('${c.conv_id}')">Promover ao CRM</button>
        `;
        box.appendChild(div);
      });
    }
    async function promote(id) {
      const r = await fetch(`/api/conversations/${id}/promote`, { method: 'POST' });
      const data = await r.json();
      if (!r.ok) { alert(data.detail); } else { load(); }
    }
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
