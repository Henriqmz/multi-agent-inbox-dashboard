from pathlib import Path

from app.triage import InboxStore, route_to_agent


def test_agent_intent_routing():
    assert route_to_agent("Qual o preço do plano anual?") == "sales_agent"
    assert route_to_agent("Preciso da segunda via do boleto") == "billing_agent"
    assert route_to_agent("O aplicativo não abre no celular") == "support_agent"


def test_crm_promotion_requires_validated_whatsapp(tmp_path: Path):
    store = InboxStore(tmp_path / "inbox.db")
    store.ingest_message("C-1", "social_inbox", "Ana Costa", "Quero proposta", whatsapp_phone="")
    store.ingest_message("C-2", "social_inbox", "Bruno Lima", "Quero proposta", whatsapp_phone="+5511999887766")

    blocked = False
    try:
        store.promote_to_crm("C-1")
    except ValueError:
        blocked = True
    assert blocked is True

    promoted = store.promote_to_crm("C-2")
    assert promoted["status"] == "PROMOTED_TO_CRM"
