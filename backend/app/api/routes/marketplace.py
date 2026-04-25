from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.agents import Agent
from app.models.reviews import Review
from app.services.search_service import MarketplaceSearchError, MarketplaceSort, SearchService

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class PaginationMeta(APIModel):
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    has_next: bool = Field(alias="hasNext")


class MarketplaceActionRead(APIModel):
    id: UUID
    name: str
    description: str
    input_schema: dict[str, Any] = Field(alias="inputSchema")
    output_schema: dict[str, Any] = Field(alias="outputSchema")
    price_usdc: Decimal | None = Field(alias="priceUsdc")
    is_active: bool = Field(alias="isActive")


class MarketplaceAgentCard(APIModel):
    id: UUID
    name: str
    slug: str
    description: str
    profile_image_url: str | None = Field(alias="profileImageUrl")
    categories: list[Any]
    tags: list[Any]
    status: str
    avg_rating: Decimal = Field(alias="avgRating")
    total_jobs: int = Field(alias="totalJobs")
    success_rate: Decimal = Field(alias="successRate")
    starting_price_usdc: Decimal | None = Field(alias="startingPriceUsdc")
    avg_duration_sec: Decimal | None = Field(alias="avgDurationSec")


class MarketplaceAgentListResponse(APIModel):
    items: list[MarketplaceAgentCard]
    meta: PaginationMeta


class MarketplaceReviewRead(APIModel):
    id: UUID
    rating: int
    body: str | None
    verified_purchase: bool = Field(alias="verifiedPurchase")
    helpful_votes: int = Field(alias="helpfulVotes")
    created_at: datetime = Field(alias="createdAt")


class MarketplaceAgentDetail(MarketplaceAgentCard):
    base_url: str = Field(alias="baseUrl")
    actions: list[MarketplaceActionRead]
    reviews: list[MarketplaceReviewRead]


class MarketplaceSearchHit(APIModel):
    agent: MarketplaceAgentCard
    relevance_score: float = Field(alias="relevanceScore")
    match_reason: str = Field(alias="matchReason")


class MarketplaceSearchResponse(APIModel):
    query: str
    enriched_query: str = Field(alias="enrichedQuery")
    orchestrator_suggestion: str = Field(alias="orchestratorSuggestion")
    results: list[MarketplaceSearchHit]


class MarketplaceCategoryRead(APIModel):
    category: str
    agent_count: int = Field(alias="agentCount")


class MarketplaceStatsResponse(APIModel):
    total_agents: int = Field(alias="totalAgents")
    total_volume: float = Field(alias="totalVolume")
    total_jobs: int = Field(alias="totalJobs")


def starting_price(agent: Agent) -> Decimal | None:
    prices = [
        action.price for action in agent.actions if action.is_active and action.price is not None
    ]
    return min(prices) if prices else None


def serialize_action(action: Any) -> MarketplaceActionRead:
    return MarketplaceActionRead(
        id=action.id,
        name=action.name,
        description=action.description,
        inputSchema=action.input_schema,
        outputSchema=action.output_schema,
        priceUsdc=action.price,
        isActive=action.is_active,
    )


def serialize_agent_card(agent: Agent) -> MarketplaceAgentCard:
    return MarketplaceAgentCard(
        id=agent.id,
        name=agent.name,
        slug=agent.slug,
        description=agent.description,
        profileImageUrl=agent.profile_image_url,
        categories=agent.categories,
        tags=agent.tags,
        status=agent.status.value,
        avgRating=agent.avg_rating,
        totalJobs=agent.total_jobs,
        successRate=agent.success_rate,
        startingPriceUsdc=starting_price(agent),
        avgDurationSec=agent.avg_duration_sec,
    )


def serialize_review(review: Review) -> MarketplaceReviewRead:
    return MarketplaceReviewRead(
        id=review.id,
        rating=review.rating,
        body=review.body,
        verifiedPurchase=review.verified_purchase,
        helpfulVotes=review.helpful_votes,
        createdAt=review.created_at,
    )


@router.get("/agents", response_model=MarketplaceAgentListResponse)
async def list_marketplace_agents(
    category: str | None = None,
    min_rating: float | None = Query(default=None, ge=0, le=5),
    max_price: Decimal | None = Query(default=None, ge=0),
    speed: str | None = Query(default=None),
    sort: MarketplaceSort = Query(default="relevance"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
) -> MarketplaceAgentListResponse:
    result = await SearchService(db).list_agents(
        category=category,
        min_rating=min_rating,
        max_price=max_price,
        speed=speed,
        sort=sort,
        page=page,
        page_size=page_size,
        q=q,
    )
    return MarketplaceAgentListResponse(
        items=[serialize_agent_card(agent) for agent in result.agents],
        meta=PaginationMeta(
            total=result.meta.total,
            page=result.meta.page,
            pageSize=result.meta.page_size,
            hasNext=result.meta.has_next,
        ),
    )


@router.get("/agents/{agent_id}", response_model=MarketplaceAgentDetail)
async def get_marketplace_agent_detail(
    agent_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> MarketplaceAgentDetail:
    service = SearchService(db)
    agent = await service.get_agent_detail(agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    reviews = await service.get_reviews(agent.id)
    card = serialize_agent_card(agent)
    return MarketplaceAgentDetail(
        **card.model_dump(by_alias=True),
        baseUrl=agent.base_url,
        actions=[serialize_action(action) for action in agent.actions if action.is_active],
        reviews=[serialize_review(review) for review in reviews],
    )


@router.get("/search", response_model=MarketplaceSearchResponse)
async def search_marketplace(
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_session),
) -> MarketplaceSearchResponse:
    try:
        result = await SearchService(db).search(query=q, limit=limit)
    except MarketplaceSearchError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return MarketplaceSearchResponse(
        query=result.query,
        enrichedQuery=result.enriched_query,
        orchestratorSuggestion=result.orchestrator_suggestion,
        results=[
            MarketplaceSearchHit(
                agent=serialize_agent_card(hit.agent),
                relevanceScore=hit.relevance_score,
                matchReason=hit.match_reason,
            )
            for hit in result.results
        ],
    )


@router.get("/categories", response_model=list[MarketplaceCategoryRead])
async def list_marketplace_categories(
    db: AsyncSession = Depends(get_session),
) -> list[MarketplaceCategoryRead]:
    categories = await SearchService(db).categories()
    return [MarketplaceCategoryRead.model_validate(category) for category in categories]


@router.get("/featured", response_model=list[MarketplaceAgentCard])
async def get_featured_agents(
    limit: int = Query(default=6, ge=1, le=24),
    db: AsyncSession = Depends(get_session),
) -> list[MarketplaceAgentCard]:
    agents = await SearchService(db).featured(limit=limit)
    return [serialize_agent_card(agent) for agent in agents]


@router.get("/stats", response_model=MarketplaceStatsResponse)
async def get_marketplace_stats(
    db: AsyncSession = Depends(get_session),
) -> MarketplaceStatsResponse:
    stats = await SearchService(db).stats()
    return MarketplaceStatsResponse.model_validate(stats)
