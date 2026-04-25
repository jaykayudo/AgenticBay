from agent_sdk import BaseAgentLogic, CapabilityPrice, HandlerResult

from app.services.research_service import ResearchInput, ResearchReport, ResearchService

class ResearchAgentLogic(BaseAgentLogic):
    agent_id = "research_agent_001"
    agent_name = "Research Agent"
    agent_description = "Generates structured research reports on a given topic"
    agent_version = "1.0.0"

    capability_id = "research_topic"
    capability_name = "Research Topic"
    capability_description = "Generate a structured research report on a topic"
    capability_category = "research"
    capability_requires_payment = True
    capability_price = CapabilityPrice(
        amount="5.00",
        currency="USDC",
        type="FIXED",
    )
    capability_estimated_execution_time_seconds = 30

    input_model = ResearchInput
    output_model = ResearchReport

    _research_service = ResearchService()

    async def run(self, payload: ResearchInput, invocation) -> HandlerResult:
        generation = await self._research_service.generate_report(payload)
        return HandlerResult(
            result=generation.report,
            provider=generation.provider,
            model=generation.model,
            usage=generation.usage,
        )
