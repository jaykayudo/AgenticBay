from __future__ import annotations

import logging
import json
import re
from textwrap import dedent

from anthropic import AsyncAnthropic

from .config import settings
from .models import ResearchArguments, ResearchBrief

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None

RESEARCH_SYSTEM_PROMPT = dedent(
    """
    You are an expert research analyst.

    Your job is to produce a concise but useful research brief from a topic,
    optional context, and optional focus areas.

    Requirements:
    - Be specific and practical.
    - Distinguish facts from assumptions.
    - Call out gaps, uncertainty, and open questions.
    - Recommend next steps that a product team or founder can take.
    - Keep the output structured and easy to skim.

    Return valid JSON only, matching this schema:
    {
      "topic": "string",
      "executive_summary": "string",
      "key_findings": ["string"],
      "assumptions_and_caveats": ["string"],
      "open_questions": ["string"],
      "recommended_next_steps": ["string"],
      "focus_areas": ["string"] | null,
      "evidence_notes": ["string"] | null,
      "extra": { "any": "optional" } | null
    }
    """
).strip()


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


async def research_topic(args: ResearchArguments) -> ResearchBrief:
    focus_areas = args.focus_areas or []
    constraints = args.constraints or []
    context = args.context.strip() if args.context else ""

    logger.info("Researching topic %r", args.topic)

    user_prompt = dedent(
        f"""
        Topic: {args.topic}

        Context:
        {context or "None provided"}

        Focus areas:
        {focus_areas if focus_areas else "None"}

        Constraints:
        {constraints if constraints else "None"}

        Produce a concise research brief for a hackathon demo and product discussion.
        """
    ).strip()

    message = await _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3500,
        system=RESEARCH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = message.content[0].text  # type: ignore[union-attr]
    logger.info("Generated research brief for %r", args.topic)
    return _parse_brief(text)


def _parse_brief(text: str) -> ResearchBrief:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match is None:
            raise
        payload = json.loads(match.group(0))

    return ResearchBrief.model_validate(payload)
