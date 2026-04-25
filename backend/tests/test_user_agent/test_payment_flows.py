"""
Payment flow tests:
  - Auto-pay enabled path (PAYMENT_SUCCESSFUL sent without user confirmation)
  - Auto-pay disabled path (modal shown, user confirms)
  - Auto-pay amount exceeds limit (falls back to confirmation)
"""

import pytest

from app.agents.user_agent.types import AutoPaySettings
from tests.test_user_agent.conftest import (
    _llm_response,
    _tool_use_block,
    build_agent,
)

_PAYMENT_MSG = {
    "type": "PAYMENT",
    "data": {
        "amount": 0.5,
        "description": "Summarization",
        "payment_info": {
            "invoice_id": "inv-99",
            "invoice_wallet": "0xESCROW",
            "blockchain": "ARC-TESTNET",
        },
    },
}


@pytest.mark.asyncio
async def test_auto_pay_enabled_sends_payment_successful_directly() -> None:
    """With auto_pay on and amount within limit, LLM should call send_orchestrator_message(PAYMENT_SUCCESSFUL)."""
    auto_pay = AutoPaySettings(
        auto_pay_enabled=True,
        auto_pay_max_per_job=10.0,
        auto_pay_max_per_day=100.0,
    )

    responses = [
        _llm_response(
            [
                _tool_use_block(
                    "send_orchestrator_message",
                    {"message_type": "PAYMENT_SUCCESSFUL", "data": {"invoice_id": "inv-99"}},
                    "tu_1",
                ),
            ]
        ),
    ]

    agent, fake_user_ws, fake_orch_ws = build_agent(responses, auto_pay=auto_pay)
    await agent.handle_orchestrator_message(_PAYMENT_MSG)

    # Confirm the LLM received context saying auto_pay is enabled
    memory_msgs = await agent.memory.get_messages_for_llm()
    context_text = " ".join(m["content"] for m in memory_msgs if isinstance(m.get("content"), str))
    assert "auto_pay enabled" in context_text

    # No confirmation modal should have been shown
    modals = fake_user_ws.of_type("PAYMENT_CONFIRMATION_MODAL")
    assert len(modals) == 0


@pytest.mark.asyncio
async def test_auto_pay_disabled_shows_confirmation_modal() -> None:
    """With auto_pay off, the LLM should call request_payment_confirmation."""
    auto_pay = AutoPaySettings(
        auto_pay_enabled=False,
        auto_pay_max_per_job=0,
        auto_pay_max_per_day=0,
    )

    responses = [
        _llm_response(
            [
                _tool_use_block(
                    "request_payment_confirmation",
                    {
                        "invoice_id": "inv-99",
                        "amount": 0.5,
                        "description": "Summarization",
                        "escrow_wallet": "0xESCROW",
                    },
                    "tu_1",
                ),
            ]
        ),
    ]

    agent, fake_user_ws, _ = build_agent(responses, auto_pay=auto_pay)
    await agent.handle_orchestrator_message(_PAYMENT_MSG)

    modals = fake_user_ws.of_type("PAYMENT_CONFIRMATION_MODAL")
    assert len(modals) == 1
    assert modals[0]["data"]["invoice_id"] == "inv-99"
    assert modals[0]["data"]["amount"] == 0.5
    assert modals[0]["data"]["requires_response"] is True

    from app.agents.user_agent.types import AgentState

    assert agent.state == AgentState.AWAITING_USER


@pytest.mark.asyncio
async def test_auto_pay_amount_exceeds_limit_shows_modal() -> None:
    """Amount (5 USDC) above per-job limit (2 USDC) → context should say limit exceeded."""
    auto_pay = AutoPaySettings(
        auto_pay_enabled=True,
        auto_pay_max_per_job=2.0,
        auto_pay_max_per_day=100.0,
    )
    high_payment_msg = {
        "type": "PAYMENT",
        "data": {
            "amount": 5.0,
            "description": "Expensive op",
            "payment_info": {
                "invoice_id": "inv-big",
                "invoice_wallet": "0xESCROW",
                "blockchain": "ARC-TESTNET",
            },
        },
    }

    responses = [
        _llm_response(
            [
                _tool_use_block(
                    "request_payment_confirmation",
                    {
                        "invoice_id": "inv-big",
                        "amount": 5.0,
                        "description": "Expensive op",
                        "escrow_wallet": "0xESCROW",
                    },
                    "tu_1",
                ),
            ]
        ),
    ]

    agent, _, _ = build_agent(responses, auto_pay=auto_pay)
    await agent.handle_orchestrator_message(high_payment_msg)

    memory_msgs = await agent.memory.get_messages_for_llm()
    context_text = " ".join(m["content"] for m in memory_msgs if isinstance(m.get("content"), str))
    # Context should tell LLM the amount exceeds the limit
    assert "exceeds" in context_text or "limit" in context_text


@pytest.mark.asyncio
async def test_user_modal_response_triggers_llm_turn() -> None:
    """MODAL_RESPONSE from user restores ACTIVE state and triggers LLM."""
    responses = [
        _llm_response(
            [
                _tool_use_block(
                    "send_orchestrator_message",
                    {"message_type": "PAYMENT_SUCCESSFUL", "data": {"invoice_id": "inv-99"}},
                    "tu_1",
                ),
                _tool_use_block("close_session", {"final_result": "paid", "success": True}, "tu_2"),
            ]
        ),
    ]

    agent, fake_user_ws, fake_orch_ws = build_agent(responses)
    from app.agents.user_agent.types import AgentState

    agent.state = AgentState.AWAITING_USER

    await agent.handle_user_response(
        {"type": "payment_confirmed", "value": True, "invoice_id": "inv-99"}
    )

    assert agent.state == AgentState.CLOSED
    payment_sent = [m for m in fake_orch_ws.sent if m.get("type") == "PAYMENT_SUCCESSFUL"]
    assert len(payment_sent) == 1
