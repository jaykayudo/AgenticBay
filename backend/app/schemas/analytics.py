from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


AnalyticsRange = Literal["7d", "30d", "90d", "all"]


class AgentSummaryMetrics(APIModel):
    total_jobs: int = Field(alias="totalJobs")
    total_earned: float = Field(alias="totalEarned")
    success_rate: float = Field(alias="successRate")
    avg_job_value: float = Field(alias="avgJobValue")


class RevenueBucket(APIModel):
    label: str
    amount: float
    jobs: int


class ActionBreakdownItem(APIModel):
    action: str
    count: int
    percentage: float
    earned: float


class AgentReviewItem(APIModel):
    id: str
    reviewer_name: str = Field(alias="reviewerName")
    company: str
    rating: int
    comment: str
    job_title: str = Field(alias="jobTitle")
    created_at: datetime = Field(alias="createdAt")


class ResponseTimeDistributionItem(APIModel):
    label: str
    count: int
    percentage: float
    average_minutes: int = Field(alias="averageMinutes")


class AgentAnalyticsResponse(APIModel):
    agent_id: str = Field(alias="agentId")
    agent_name: str = Field(alias="agentName")
    owner_name: str = Field(alias="ownerName")
    range: AnalyticsRange
    generated_at: datetime = Field(alias="generatedAt")
    summary: AgentSummaryMetrics
    revenue_series: list[RevenueBucket] = Field(alias="revenueSeries")
    action_breakdown: list[ActionBreakdownItem] = Field(alias="actionBreakdown")
    reviews: list[AgentReviewItem]
    response_time_distribution: list[ResponseTimeDistributionItem] = Field(
        alias="responseTimeDistribution"
    )
