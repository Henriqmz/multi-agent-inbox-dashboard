from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

PHONE_RX = re.compile(r"^\+?\d{10,15}$")


def route_to_agent(message_text: str) -> str:
    """Classifies incoming conversation intent to a specialized agent profile."""
    low = (message_text or "").lower()
    if any(k in low for k in ("preço", "orçamento", "plano", "proposta", "contratar", "demo")):
        return "sales_agent"
    if any(k in low for k in ("boleto", "fatura", "nota fiscal", "pagamento", "cobrança")):
        return "billing_agent"
    return "support_agent"


def is_valid_whatsapp_phone(phone: str) -> bool:
    digits = re.sub(r"[\s()-]", "", (phone or "").strip())
    return bool(PHONE_RX.match(digits))


class InboxStore:
    """SQLite store for multi-agent triage conversations and CRM promotion guardrails."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conv_id TEXT PRIMARY KEY,
                    channel TEXT NOT NULL,
                    contact_name TEXT NOT NULL,
                    whatsapp_phone TEXT NOT NULL DEFAULT '',
                    last_message TEXT NOT NULL,
                    assigned_agent TEXT NOT NULL,
                    suggested_reply TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'TRIAGE',
                    updated_at TEXT NOT NULL
                )
                """
            )

    def ingest_message(
        self,
        conv_id: str,
        channel: str,
        contact_name: str,
        message_text: str,
        whatsapp_phone: str = "",
    ) -> dict[str, Any]:
        agent = route_to_agent(message_text)
        suggested = f"[{agent}] Olá {contact_name.split()[0]}, recebemos sua mensagem sobre '{message_text[:45]}'. Como posso ajudar?"
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO conversations
                (conv_id, channel, contact_name, whatsapp_phone, last_message, assigned_agent, suggested_reply, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'TRIAGE', ?)
                """,
                (conv_id, channel, contact_name, whatsapp_phone, message_text, agent, suggested, now),
            )
            row = conn.execute("SELECT * FROM conversations WHERE conv_id = ?", (conv_id,)).fetchone()
            return dict(row)

    def update_whatsapp_phone(self, conv_id: str, whatsapp_phone: str) -> dict[str, Any]:
        cleaned = re.sub(r"[\s()-]", "", (whatsapp_phone or "").strip())
        if not is_valid_whatsapp_phone(cleaned):
            raise ValueError("Informe um número válido com DDI/DDD (ex.: +5511999887766).")
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE conv_id = ?", (conv_id,)).fetchone()
            if not row:
                raise KeyError(f"Conversa '{conv_id}' não encontrada.")
            conn.execute(
                "UPDATE conversations SET whatsapp_phone = ?, updated_at = ? WHERE conv_id = ?",
                (cleaned, datetime.now(timezone.utc).isoformat(), conv_id),
            )
            return dict(conn.execute("SELECT * FROM conversations WHERE conv_id = ?", (conv_id,)).fetchone())

    def approve_reply(self, conv_id: str, reply_text: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE conv_id = ?", (conv_id,)).fetchone()
            if not row:
                raise KeyError(f"Conversa '{conv_id}' não encontrada.")
            new_status = row["status"] if row["status"] == "PROMOTED_TO_CRM" else "REPLIED"
            conn.execute(
                "UPDATE conversations SET suggested_reply = ?, status = ?, updated_at = ? WHERE conv_id = ?",
                (reply_text.strip(), new_status, datetime.now(timezone.utc).isoformat(), conv_id),
            )
            return dict(conn.execute("SELECT * FROM conversations WHERE conv_id = ?", (conv_id,)).fetchone())

    def promote_to_crm(self, conv_id: str) -> dict[str, Any]:
        """Promotes a conversation to CRM ONLY if a valid WhatsApp phone has been captured."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE conv_id = ?", (conv_id,)).fetchone()
            if not row:
                raise KeyError(f"Conversa '{conv_id}' não encontrada.")
            if not is_valid_whatsapp_phone(row["whatsapp_phone"]):
                raise ValueError(
                    "Guardrail ativo: não é permitido enviar ao CRM sem número de WhatsApp validado."
                )
            conn.execute(
                "UPDATE conversations SET status = 'PROMOTED_TO_CRM', updated_at = ? WHERE conv_id = ?",
                (datetime.now(timezone.utc).isoformat(), conv_id),
            )
            updated = conn.execute("SELECT * FROM conversations WHERE conv_id = ?", (conv_id,)).fetchone()
            return dict(updated)

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC")]

    def seed_demo_if_empty(self) -> None:
        if self.list_conversations():
            return
        self.ingest_message("C-101", "social_inbox", "Marina Alves", "Quero receber uma proposta do plano Enterprise.", "+5511987654321")
        self.ingest_message("C-102", "social_inbox", "Lucas Pereira", "Qual o preço para 30 usuários?", "")
        self.ingest_message("C-103", "whatsapp", "Carla Souza", "Preciso da segunda via da fatura de novembro.", "+5521999887766")
