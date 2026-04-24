from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field


class MarketplaceStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_agents: int = Field(alias="totalAgents")
    total_volume: float = Field(alias="totalVolume")
    total_jobs: int = Field(alias="totalJobs")


router = APIRouter()


@router.get("/stats", response_model=MarketplaceStats)
async def get_marketplace_stats() -> MarketplaceStats:
    """Return aggregate marketplace metrics for the public landing page."""
    return MarketplaceStats(
        totalAgents=248,
        totalVolume=1_240_000,
        totalJobs=3842,
    )
