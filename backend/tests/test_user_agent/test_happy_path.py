"""
Full happy-path session:
  user message → search → connect → invoke → payment → close
"""

import pytest

from app.agents.user_agent.types import AgentState
from tests.test_user_agent.conftest import (
    _llm_response,
    _text_block,
    _tool_use_block,
    build_agent,
)


@pytest.mark.asyncio
async def test_happy_path_full_session() -> None:
    """
    LLM turn sequence:
    1. search for agents
    2. show user feedback + connect to chosen agent
    3. invoke SERVICE_AGENT
    4. send PAYMENT_SUCCESSFUL (mocked auto-approve)
    5. close session with result
    """
    responses = [
        # Turn 1: search
        _llm_response(
            [
                _tool_use_block(
                    "user_feedback",
                    {"message": "Searching for agents...", "type": "progress"},
                    "tu_1",
                ),
                _tool_use_block(
                    "send_orchestrator_message",
                    {"message_type": "SEARCH_AGENT", "data": {"message": "summarize document"}},
                    "tu_2",
                ),
            ]
        ),
        # Turn 2: after SEARCH_AGENT context — choose and connect
        _llm_response(
            [
                _tool_use_block(
                    "user_feedback",
                    {"message": "Connecting to Doc Summarizer", "type": "progress"},
                    "tu_3",
                ),
                _tool_use_block(
                    "send_orchestrator_message",
                    {"message_type": "CONNECT_AGENT", "data": {"agent_id": "agent-1"}},
                    "tu_4",
                ),
            ]
        ),
        # Turn 3: after CONNECT context — invoke service
        _llm_response(
            [
                _tool_use_block(
                    "send_orchestrator_message",
                    {
                        "message_type": "SERVICE_AGENT",
                        "data": {"command": "summarize", "arguments": {"document": "hello world"}},
                    },
                    "tu_5",
                ),
            ]
        ),
        # Turn 4: after PAYMENT context — confirm payment
        _llm_response(
            [
                _tool_use_block(
                    "send_orchestrator_message",
                    {"message_type": "PAYMENT_SUCCESSFUL", "data": {"invoice_id": "inv-1"}},
                    "tu_6",
                ),
            ]
        ),
        # Turn 5: after CLOSE_APPEAL context — close session
        _llm_response(
            [
                _tool_use_block(
                    "close_session",
                    {"final_result": "Here is your summary: ...", "success": True},
                    "tu_7",
                ),
            ]
        ),
    ]

    agent, fake_user_ws, fake_orch_ws = build_agent(responses)

    # Simulate receiving the user's initial message
    await agent.memory.add_user_message("Please summarize this document: hello world")
    await agent.run_llm_turn()

    # Simulate receiving orchestrator SEARCH_AGENT response
    await agent.handle_orchestrator_message(
        {
            "type": "SEARCH_AGENT",
            "data": {
                "agents": [
                    {
                        "id": "agent-1",
                        "name": "Doc Summarizer",
                        "description": "Summarizes docs",
                        "rating": 4.8,
                        "pricing": {"summarize": 0.5},
                    }
                ]
            },
        }
    )

    # Simulate receiving orchestrator CONNECT response
    await agent.handle_orchestrator_message(
        {
            "type": "CONNECT",
            "data": {
                "agent_id": "agent-1",
                "capabilities": "I summarize documents. Command: summarize.",
            },
        }
    )

    # Simulate PAYMENT response
    await agent.handle_orchestrator_message(
        {
            "type": "PAYMENT",
            "data": {
                "amount": 0.5,
                "description": "Summarization",
                "payment_info": {
                    "invoice_id": "inv-1",
                    "invoice_wallet": "0xABC",
                    "blockchain": "ARC-TESTNET",
                },
            },
        }
    )

    # Simulate CLOSE_APPEAL response
    await agent.handle_orchestrator_message(
        {
            "type": "CLOSE_APPEAL",
            "data": {"message": "Done", "details": {"summary": "Summary text here"}},
        }
    )

    # Verify key orchestrator messages were sent
    orch_types = [m["type"] for m in fake_orch_ws.sent]
    assert "SEARCH_AGENT" in orch_types
    assert "CONNECT_AGENT" in orch_types
    assert "SERVICE_AGENT" in orch_types
    assert "PAYMENT_SUCCESSFUL" in orch_types
    assert "CLOSE" in orch_types

    # Verify user was informed
    agent_msgs = fake_user_ws.of_type("AGENT_MESSAGE")
    assert len(agent_msgs) >= 2  # at least progress + result

    # Verify session ended
    complete_msgs = fake_user_ws.of_type("SESSION_COMPLETE")
    assert len(complete_msgs) == 1
    assert complete_msgs[0]["data"]["success"] is True


@pytest.mark.asyncio
async def test_user_feedback_delivered_during_session() -> None:
    """user_feedback tool correctly pushes AGENT_MESSAGE to frontend."""
    responses = [
        _llm_response(
            [
                _tool_use_block(
                    "user_feedback", {"message": "Working on it!", "type": "progress"}, "tu_1"
                ),
                _tool_use_block("close_session", {"final_result": "done", "success": True}, "tu_2"),
            ]
        ),
    ]
    agent, fake_user_ws, _ = build_agent(responses)

    await agent.run_llm_turn()

    msgs = fake_user_ws.of_type("AGENT_MESSAGE")
    assert len(msgs) == 1
    assert msgs[0]["data"]["message"] == "Working on it!"
    assert msgs[0]["data"]["message_type"] == "progress"


@pytest.mark.asyncio
async def test_session_complete_on_close_session_tool() -> None:
    """close_session tool sends SESSION_COMPLETE and marks state CLOSED."""
    responses = [
        _llm_response(
            [
                _tool_use_block(
                    "close_session",
                    {"final_result": "All done!", "success": True, "summary": "Job complete"},
                    "tu_1",
                ),
            ]
        ),
    ]
    agent, fake_user_ws, fake_orch_ws = build_agent(responses)

    await agent.run_llm_turn()

    complete = fake_user_ws.of_type("SESSION_COMPLETE")
    assert len(complete) == 1
    assert complete[0]["data"]["final_result"] == "All done!"
    assert complete[0]["data"]["success"] is True

    # Orchestrator received CLOSE
    assert any(m["type"] == "CLOSE" for m in fake_orch_ws.sent)
    assert agent.state == AgentState.CLOSED


@pytest.mark.asyncio
async def test_text_response_delivered_as_agent_message() -> None:
    """Pure text LLM response (no tool calls) is forwarded to user."""
    responses = [
        _llm_response([_text_block("Let me help you with that!")], stop_reason="end_turn"),
    ]
    agent, fake_user_ws, _ = build_agent(responses)

    await agent.run_llm_turn()

    msgs = fake_user_ws.of_type("AGENT_MESSAGE")
    assert len(msgs) == 1
    assert "help you" in msgs[0]["data"]["message"]
