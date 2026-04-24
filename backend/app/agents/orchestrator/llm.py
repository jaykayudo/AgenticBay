import json
import logging
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import Message, TextBlock

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-20250514"


class OrchestratorLLM:
    """
    All LLM calls made by the orchestration agent.
    Uses Claude via the Anthropic SDK.
    Temperature 0 throughout — deterministic, consistent outputs.
    """

    def __init__(self) -> None:
        self.client = AsyncAnthropic()

    @staticmethod
    def _extract_text(response: Message) -> str:
        block = response.content[0]
        if not isinstance(block, TextBlock):
            raise ValueError(f"Unexpected content block type: {type(block)}")
        return block.text

    # ──────────────────────────────────────────
    # 1. SEARCH QUERY ENRICHMENT
    # ──────────────────────────────────────────
    async def enrich_search_query(self, raw_query: str) -> str:
        response = await self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            temperature=0,
            system="""
                You are a search query optimizer for an AI agent marketplace.
                Your job is to take a user's natural language request and
                produce an enriched search query that will find the most
                relevant service agents via vector similarity search.

                Rules:
                - Expand abbreviations and vague terms
                - Add relevant technical synonyms
                - Make implicit requirements explicit
                - Keep it under 100 words
                - Return ONLY the enriched query string, nothing else
                - No explanations, no JSON, just the query text
            """,
            messages=[{"role": "user", "content": f"Original query: {raw_query}"}],
        )

        enriched = self._extract_text(response).strip()
        logger.debug("Enriched query: '%s' → '%s'", raw_query, enriched)
        return enriched

    # ──────────────────────────────────────────
    # 2. AGENT RERANKING
    # ──────────────────────────────────────────
    async def rerank_agents(
        self,
        original_query: str,
        agents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not agents:
            return []

        slim_agents = [
            {
                "id": a["id"],
                "name": a["name"],
                "description": str(a["description"])[:300],
                "rating": a["rating"],
                "pricing": a["pricing"],
            }
            for a in agents
        ]

        response = await self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            temperature=0,
            system="""
                You are a relevance ranker for an AI agent marketplace.
                Given a user's request and a list of service agents,
                rerank the agents from most to least relevant.

                Return a JSON array in this exact format:
                [
                  {
                    "id": "agent_id",
                    "relevance_score": 0.95,
                    "match_reason": "one sentence why this agent fits"
                  }
                ]

                Rules:
                - Include ALL agents from the input, even poor matches
                - relevance_score is 0.0 to 1.0
                - match_reason is one clear sentence max
                - Return ONLY the JSON array, no other text
            """,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"User request: {original_query}\n\n"
                        f"Agents to rank:\n{json.dumps(slim_agents, indent=2)}"
                    ),
                }
            ],
        )

        raw = self._extract_text(response).strip()

        try:
            rankings: list[dict[str, Any]] = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Failed to parse reranking response: %s", raw)
            return agents

        agent_lookup = {a["id"]: a for a in agents}

        reranked: list[dict[str, Any]] = []
        for rank in rankings:
            agent_id = rank.get("id")
            if agent_id in agent_lookup:
                reranked.append(
                    {
                        **agent_lookup[agent_id],
                        "relevance_score": rank.get("relevance_score", 0.0),
                        "match_reason": rank.get("match_reason", ""),
                    }
                )

        reranked.sort(key=lambda x: float(str(x.get("relevance_score", 0))), reverse=True)
        return reranked

    # ──────────────────────────────────────────
    # 3. PAYMENT SUCCESS COMMAND FINDER
    # ──────────────────────────────────────────
    async def find_payment_success_command(self, capabilities: str) -> dict[str, Any]:
        response = await self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            temperature=0,
            system="""
                You are analyzing a service agent's capability document.
                Your job is to find the command the agent uses to
                receive payment confirmation.

                Look for any mention of:
                - PAYMENT_SUCCESSFUL
                - payment confirmed
                - payment done
                - payment received

                Return JSON in this exact format:
                {
                  "command": "the_command_name",
                  "arguments_template": {
                    "argument_name": "placeholder"
                  }
                }

                If no specific payment confirmation command is documented,
                default to:
                {
                  "command": "PAYMENT_SUCCESSFUL",
                  "arguments_template": {
                    "invoice_id": "<invoice_id>",
                    "invoice_contract": "<contract_address>"
                  }
                }

                Return ONLY the JSON, no other text.
            """,
            messages=[{"role": "user", "content": f"Capability document:\n\n{capabilities}"}],
        )

        raw = self._extract_text(response).strip()

        try:
            result: dict[str, Any] = json.loads(raw)
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse payment command response: %s", raw)
            return {
                "command": "PAYMENT_SUCCESSFUL",
                "arguments_template": {
                    "invoice_id": "<invoice_id>",
                    "invoice_contract": "<contract_address>",
                },
            }

    # ──────────────────────────────────────────
    # 4. ORCHESTRATOR SUGGESTION TEXT
    # ──────────────────────────────────────────
    async def generate_search_suggestion(
        self,
        original_query: str,
        top_agents: list[dict[str, Any]],
    ) -> str:
        if not top_agents:
            return "No agents found matching your request."

        top_3 = top_agents[:3]

        response = await self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=200,
            temperature=0,
            system="""
                You are a helpful assistant in an AI agent marketplace.
                Write a brief, friendly 1-2 sentence suggestion explaining
                the top search results to the user.
                Mention the top agent by name and why it is a good fit.
                Be concise and conversational.
                Return ONLY the suggestion text, nothing else.
            """,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"User request: {original_query}\n\n"
                        "Top agents found:\n"
                        + json.dumps(
                            [
                                {
                                    "name": a["name"],
                                    "match_reason": a.get("match_reason", ""),
                                    "rating": a["rating"],
                                }
                                for a in top_3
                            ],
                            indent=2,
                        )
                    ),
                }
            ],
        )

        return self._extract_text(response).strip()

    # ──────────────────────────────────────────
    # 5. INTENT PARSER
    # ──────────────────────────────────────────
    async def parse_intent(
        self,
        raw_message: str,
        session_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        history_summary = (
            json.dumps(session_history[-5:], indent=2) if session_history else "No history yet"
        )

        response = await self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=400,
            temperature=0,
            system="""
                You are the intake processor for an AI agent marketplace orchestrator.
                Parse incoming messages from user agents and extract structured intent.

                Valid intent types:
                - SEARCH_AGENT     → user wants to find an agent
                - CONNECT_AGENT    → user wants to connect to a specific agent
                - SERVICE_AGENT    → user wants to send a command to the connected agent
                - PAYMENT_SUCCESSFUL → user has made a payment
                - CLOSE            → user wants to end the session
                - UNKNOWN          → cannot determine intent

                Return JSON in this exact format:
                {
                  "intent": "INTENT_TYPE",
                  "extracted_data": {
                    "relevant field": "relevant value"
                  },
                  "ambiguous": false,
                  "clarification_needed": null
                }

                Return ONLY the JSON, no other text.
            """,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Raw message: {raw_message}\n\nRecent session history:\n{history_summary}"
                    ),
                }
            ],
        )

        raw = self._extract_text(response).strip()

        try:
            result: dict[str, Any] = json.loads(raw)
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse intent response: %s", raw)
            return {
                "intent": "UNKNOWN",
                "extracted_data": {},
                "ambiguous": True,
                "clarification_needed": "Could you clarify what you would like to do?",
            }

    # ──────────────────────────────────────────
    # 6. RESPONSE QUALITY CHECK
    # ──────────────────────────────────────────
    async def evaluate_service_response(
        self,
        original_request: str,
        service_response: dict[str, Any],
    ) -> dict[str, Any]:
        response = await self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=200,
            temperature=0,
            system="""
                You are a quality evaluator for an AI agent marketplace.
                Determine if a service agent's response adequately
                fulfilled the user's request.

                Return JSON in this exact format:
                {
                  "adequate":      true,
                  "quality_score": 8,
                  "reason":        "one sentence explanation"
                }

                quality_score is 0-10.
                Return ONLY the JSON, no other text.
            """,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Original request: {original_request}\n\n"
                        f"Service agent response:\n{json.dumps(service_response, indent=2)}"
                    ),
                }
            ],
        )

        raw = self._extract_text(response).strip()

        try:
            result: dict[str, Any] = json.loads(raw)
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse quality check: %s", raw)
            return {
                "adequate": True,
                "quality_score": 5,
                "reason": "Could not evaluate response quality",
            }
