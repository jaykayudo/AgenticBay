from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class MarketplaceStats(APIModel):
    total_agents: int = Field(alias="totalAgents")
    total_volume: float = Field(alias="totalVolume")
    total_jobs: int = Field(alias="totalJobs")


class MarketplaceReviewItem(APIModel):
    id: str
    reviewer_name: str = Field(alias="reviewerName")
    company: str
    rating: int
    comment: str
    job_title: str = Field(alias="jobTitle")
    created_at: datetime = Field(alias="createdAt")


class MarketplaceResponseDistributionItem(APIModel):
    label: str
    count: int
    percentage: float
    average_minutes: int = Field(alias="averageMinutes")


class MarketplaceMetricItem(APIModel):
    label: str
    value: str
    detail: str


class MarketplaceAgentStats(APIModel):
    success_rate: float = Field(alias="successRate")
    total_jobs: int = Field(alias="totalJobs")
    total_earned: float = Field(alias="totalEarned")
    avg_job_value: float = Field(alias="avgJobValue")
    avg_delivery_minutes: int = Field(alias="avgDeliveryMinutes")
    avg_delivery_label: str = Field(alias="avgDeliveryLabel")
    repeat_buyer_rate: float = Field(alias="repeatBuyerRate")
    on_time_rate: float = Field(alias="onTimeRate")
    payout_completion_rate: float = Field(alias="payoutCompletionRate")
    metrics: list[MarketplaceMetricItem]
    response_time_distribution: list[MarketplaceResponseDistributionItem] = Field(
        alias="responseTimeDistribution"
    )


class MarketplaceAgentInsightsResponse(APIModel):
    agent_slug: str = Field(alias="agentSlug")
    agent_name: str = Field(alias="agentName")
    generated_at: datetime = Field(alias="generatedAt")
    stats: MarketplaceAgentStats
    reviews: list[MarketplaceReviewItem]


class MarketplaceSessionCreateRequest(APIModel):
    action_id: str = Field(alias="actionId")
    action_name: str = Field(alias="actionName")
    price_usdc: int = Field(alias="priceUsdc")
    estimated_duration_label: str = Field(alias="estimatedDurationLabel")
    input_summary: str = Field(alias="inputSummary")
    mode: Literal["hire", "demo"] = "hire"


class MarketplaceSessionRead(APIModel):
    session_id: str = Field(alias="sessionId")
    agent_slug: str = Field(alias="agentSlug")
    agent_name: str = Field(alias="agentName")
    action_id: str = Field(alias="actionId")
    action_name: str = Field(alias="actionName")
    price_usdc: int = Field(alias="priceUsdc")
    estimated_duration_label: str = Field(alias="estimatedDurationLabel")
    input_summary: str = Field(alias="inputSummary")
    amount_locked_usdc: int = Field(alias="amountLockedUsdc")
    status: Literal["queued", "processing", "awaiting_payment", "completed", "cancelled", "closed"]
    mode: Literal["hire", "demo"]
    created_at: datetime = Field(alias="createdAt")
    redirect_path: str = Field(alias="redirectPath")
    session_token: str = Field(alias="sessionToken")
    socket_url: str = Field(alias="socketUrl")
    result_payload: dict[str, object] | None = Field(default=None, alias="resultPayload")
