from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import floor
from uuid import uuid4

from jose import jwt

from app.agents.orchestrator.schema import JobSessionState, SessionPhase
from app.agents.orchestrator.session_store import SessionStore
from app.core.config import settings
from app.schemas.marketplace import (
    MarketplaceAgentInsightsResponse,
    MarketplaceAgentStats,
    MarketplaceMetricItem,
    MarketplaceResponseDistributionItem,
    MarketplaceReviewItem,
    MarketplaceSessionCreateRequest,
    MarketplaceSessionRead,
    MarketplaceStats,
)


class MarketplaceAgentNotFoundError(Exception):
    """Raised when a public marketplace agent cannot be found."""


class MarketplaceSessionNotFoundError(Exception):
    """Raised when a public marketplace session cannot be found."""


@dataclass(frozen=True)
class PublicAgentSeed:
    slug: str
    name: str
    categories: tuple[str, ...]
    tags: tuple[str, ...]
    starting_price_usdc: int
    speed_rank: int
    success_rate: float
    jobs_completed: int
    rating: float
    review_count: int


PUBLIC_AGENT_SEEDS = (
    PublicAgentSeed(
        slug="northstar-research",
        name="Northstar Research",
        categories=("Research", "Data Analysis"),
        tags=("Competitive Intel", "Market Mapping", "Briefs"),
        starting_price_usdc=150,
        speed_rank=3,
        success_rate=99.1,
        jobs_completed=284,
        rating=4.9,
        review_count=184,
    ),
    PublicAgentSeed(
        slug="signal-relay",
        name="Signal Relay",
        categories=("Automation", "Development"),
        tags=("Ops Automation", "Integrations", "Routing"),
        starting_price_usdc=80,
        speed_rank=2,
        success_rate=97.8,
        jobs_completed=213,
        rating=4.8,
        review_count=151,
    ),
    PublicAgentSeed(
        slug="harbor-assist",
        name="Harbor Assist",
        categories=("Customer Support", "Content"),
        tags=("Inbox Ops", "Escalation", "Support QA"),
        starting_price_usdc=50,
        speed_rank=1,
        success_rate=98.3,
        jobs_completed=412,
        rating=4.9,
        review_count=242,
    ),
    PublicAgentSeed(
        slug="pattern-office",
        name="Pattern Office",
        categories=("Design", "Content"),
        tags=("Design Systems", "Asset Generation", "Documentation"),
        starting_price_usdc=120,
        speed_rank=4,
        success_rate=95.9,
        jobs_completed=127,
        rating=4.6,
        review_count=96,
    ),
    PublicAgentSeed(
        slug="cipher-shield",
        name="Cipher Shield",
        categories=("Security", "Development"),
        tags=("Security Audit", "Compliance", "Risk Review"),
        starting_price_usdc=200,
        speed_rank=4,
        success_rate=99.4,
        jobs_completed=89,
        rating=4.9,
        review_count=88,
    ),
    PublicAgentSeed(
        slug="dataflow-ai",
        name="DataFlow AI",
        categories=("Data Analysis", "Research"),
        tags=("Forecasting", "Dashboards", "Analytics Ops"),
        starting_price_usdc=100,
        speed_rank=3,
        success_rate=96.7,
        jobs_completed=156,
        rating=4.7,
        review_count=129,
    ),
    PublicAgentSeed(
        slug="brief-engine",
        name="Brief Engine",
        categories=("Research", "Content"),
        tags=("Executive Briefs", "Synthesis", "Narrative"),
        starting_price_usdc=95,
        speed_rank=3,
        success_rate=97.3,
        jobs_completed=111,
        rating=4.8,
        review_count=74,
    ),
    PublicAgentSeed(
        slug="deploy-dock",
        name="Deploy Dock",
        categories=("Development", "Automation"),
        tags=("CI/CD", "Release Ops", "Infra Support"),
        starting_price_usdc=180,
        speed_rank=2,
        success_rate=96.8,
        jobs_completed=143,
        rating=4.7,
        review_count=91,
    ),
    PublicAgentSeed(
        slug="resolve-ai",
        name="Resolve AI",
        categories=("Customer Support", "Content"),
        tags=("Escalations", "Recovery", "Policy Workflows"),
        starting_price_usdc=70,
        speed_rank=2,
        success_rate=97.2,
        jobs_completed=201,
        rating=4.7,
        review_count=118,
    ),
    PublicAgentSeed(
        slug="orbit-scout",
        name="Orbit Scout",
        categories=("Research", "Data Analysis"),
        tags=("Market Sizing", "Account Mapping", "Discovery"),
        starting_price_usdc=140,
        speed_rank=4,
        success_rate=98.1,
        jobs_completed=134,
        rating=4.8,
        review_count=83,
    ),
    PublicAgentSeed(
        slug="canvas-forge",
        name="Canvas Forge",
        categories=("Design", "Content"),
        tags=("Creative Ops", "Landing Pages", "Brand Kits"),
        starting_price_usdc=110,
        speed_rank=4,
        success_rate=94.8,
        jobs_completed=98,
        rating=4.5,
        review_count=62,
    ),
    PublicAgentSeed(
        slug="pipeline-pilot",
        name="Pipeline Pilot",
        categories=("Automation", "Data Analysis"),
        tags=("ETL", "CRM Sync", "Scoring"),
        starting_price_usdc=135,
        speed_rank=3,
        success_rate=97.9,
        jobs_completed=167,
        rating=4.8,
        review_count=105,
    ),
    PublicAgentSeed(
        slug="sentinel-queue",
        name="Sentinel Queue",
        categories=("Security", "Customer Support"),
        tags=("Incident Triage", "Monitoring", "Safety Ops"),
        starting_price_usdc=145,
        speed_rank=2,
        success_rate=98.6,
        jobs_completed=92,
        rating=4.7,
        review_count=57,
    ),
    PublicAgentSeed(
        slug="sprint-compiler",
        name="Sprint Compiler",
        categories=("Development",),
        tags=("Code Delivery", "Bugfixes", "Testing"),
        starting_price_usdc=160,
        speed_rank=3,
        success_rate=97.6,
        jobs_completed=189,
        rating=4.8,
        review_count=132,
    ),
    PublicAgentSeed(
        slug="prompt-harbor",
        name="Prompt Harbor",
        categories=("Content", "Research"),
        tags=("Lifecycle Content", "Prompt Systems", "Editorial"),
        starting_price_usdc=65,
        speed_rank=3,
        success_rate=95.7,
        jobs_completed=124,
        rating=4.6,
        review_count=79,
    ),
    PublicAgentSeed(
        slug="ops-beacon",
        name="Ops Beacon",
        categories=("Automation", "Customer Support"),
        tags=("SOPs", "Queue Design", "Ops Routing"),
        starting_price_usdc=90,
        speed_rank=2,
        success_rate=96.9,
        jobs_completed=116,
        rating=4.7,
        review_count=67,
    ),
    PublicAgentSeed(
        slug="ledger-lens",
        name="Ledger Lens",
        categories=("Data Analysis", "Research"),
        tags=("Finance Ops", "Unit Economics", "Reporting"),
        starting_price_usdc=125,
        speed_rank=4,
        success_rate=98.0,
        jobs_completed=81,
        rating=4.8,
        review_count=53,
    ),
    PublicAgentSeed(
        slug="contract-cartographer",
        name="Contract Cartographer",
        categories=("Research", "Security"),
        tags=("Due Diligence", "Scope Review", "Vendor Risk"),
        starting_price_usdc=210,
        speed_rank=4,
        success_rate=99.0,
        jobs_completed=73,
        rating=4.9,
        review_count=49,
    ),
    PublicAgentSeed(
        slug="voice-loom",
        name="Voice Loom",
        categories=("Content", "Customer Support"),
        tags=("Brand Voice", "Macros", "Knowledge Base"),
        starting_price_usdc=55,
        speed_rank=3,
        success_rate=95.9,
        jobs_completed=131,
        rating=4.6,
        review_count=72,
    ),
    PublicAgentSeed(
        slug="trace-garden",
        name="Trace Garden",
        categories=("Development", "Security"),
        tags=("Debugging", "Observability", "Incident Follow-up"),
        starting_price_usdc=175,
        speed_rank=2,
        success_rate=97.1,
        jobs_completed=87,
        rating=4.7,
        review_count=58,
    ),
)


class MarketplacePublicService:
    REVIEWER_NAMES = (
        "Ava Thompson",
        "Liam Carter",
        "Noah Bennett",
        "Isla Park",
        "Ethan Reed",
        "Mia Patel",
        "Zoe Kim",
        "Lucas Grant",
        "Ella Morgan",
        "Caleb Brooks",
        "Nina Shah",
        "Miles Turner",
    )
    COMPANIES = (
        "Pearl Labs",
        "Fieldline",
        "Northwind Health",
        "Sienna Cloud",
        "Hale Commerce",
        "Rivergrid",
        "Meridian Works",
        "Brightwell",
        "Crestline",
        "Northscale",
        "Sable Finance",
        "Morningside Health",
    )
    COMMENT_TEMPLATES = (
        "Clear execution around {primary} and a handoff we could plug straight into operations.",
        "{name} handled the {secondary} work with very little back-and-forth and delivered on schedule.",
        "Strong quality across {primary} with practical output formatting for our team and partner agents.",
        "The delivery helped us move faster on {secondary} and removed a lot of coordination overhead.",
        "Reliable work, crisp communication, and a final package that was easy to operationalize.",
    )
    RESPONSE_BANDS = (
        ("Under 15 min", 11),
        ("15-30 min", 24),
        ("31-60 min", 46),
        ("1-2 hours", 88),
        ("Over 2 hours", 180),
    )
    RESPONSE_FRACTIONS = {
        1: (0.46, 0.28, 0.14, 0.08, 0.04),
        2: (0.28, 0.32, 0.2, 0.12, 0.08),
        3: (0.12, 0.22, 0.29, 0.23, 0.14),
        4: (0.04, 0.12, 0.23, 0.34, 0.27),
        5: (0.02, 0.08, 0.15, 0.32, 0.43),
    }

    def __init__(self, now: datetime | None = None) -> None:
        self.now = now
        self.agent_seeds = {seed.slug: seed for seed in PUBLIC_AGENT_SEEDS}
        self.sessions: dict[str, MarketplaceSessionRead] = {}
        self.session_store = SessionStore()

    def get_stats(self) -> MarketplaceStats:
        total_volume = round(
            sum(
                seed.starting_price_usdc * seed.jobs_completed * (1.38 + (seed.speed_rank * 0.06))
                for seed in self.agent_seeds.values()
            ),
            2,
        )

        return MarketplaceStats(
            totalAgents=len(self.agent_seeds),
            totalVolume=total_volume,
            totalJobs=sum(seed.jobs_completed for seed in self.agent_seeds.values()),
        )

    def get_agent_insights(self, agent_slug: str) -> MarketplaceAgentInsightsResponse:
        seed = self.agent_seeds.get(agent_slug)
        if seed is None:
            raise MarketplaceAgentNotFoundError(f"Agent '{agent_slug}' could not be found.")

        now = self._now()

        response_distribution = self._build_distribution(seed)
        avg_delivery_minutes = max(
            6,
            round(
                sum(item.count * item.average_minutes for item in response_distribution)
                / max(1, sum(item.count for item in response_distribution))
            ),
        )
        total_earned = round(
            seed.starting_price_usdc
            * seed.jobs_completed
            * (1.42 + (seed.speed_rank * 0.07) + ((5 - seed.rating) * 0.03)),
            2,
        )
        avg_job_value = round(total_earned / max(seed.jobs_completed, 1), 2)
        repeat_buyer_rate = round(min(93.0, 54.0 + (seed.review_count * 0.14)), 1)
        on_time_rate = round(min(99.6, seed.success_rate + (1.8 - (seed.speed_rank * 0.2))), 1)
        payout_completion_rate = round(min(99.8, 97.2 + (seed.success_rate - 95.0) * 0.5), 1)

        stats = MarketplaceAgentStats(
            successRate=seed.success_rate,
            totalJobs=seed.jobs_completed,
            totalEarned=total_earned,
            avgJobValue=avg_job_value,
            avgDeliveryMinutes=avg_delivery_minutes,
            avgDeliveryLabel=self._format_minutes(avg_delivery_minutes),
            repeatBuyerRate=repeat_buyer_rate,
            onTimeRate=on_time_rate,
            payoutCompletionRate=payout_completion_rate,
            metrics=[
                MarketplaceMetricItem(
                    label="On-time delivery",
                    value=f"{on_time_rate:.1f}%",
                    detail="Completed inside the quoted delivery window.",
                ),
                MarketplaceMetricItem(
                    label="Repeat buyers",
                    value=f"{repeat_buyer_rate:.1f}%",
                    detail="Share of recent contracts from returning customers or coordinating agents.",
                ),
                MarketplaceMetricItem(
                    label="Avg contract value",
                    value=f"${avg_job_value:,.0f}",
                    detail="Average settled spend across recent marketplace jobs.",
                ),
                MarketplaceMetricItem(
                    label="Payout completion",
                    value=f"{payout_completion_rate:.1f}%",
                    detail="Escrow-to-settlement success across completed jobs.",
                ),
            ],
            responseTimeDistribution=response_distribution,
        )

        return MarketplaceAgentInsightsResponse(
            agentSlug=seed.slug,
            agentName=seed.name,
            generatedAt=now,
            stats=stats,
            reviews=self._build_reviews(seed, now),
        )

    async def create_session(
        self, agent_slug: str, payload: MarketplaceSessionCreateRequest
    ) -> MarketplaceSessionRead:
        seed = self.agent_seeds.get(agent_slug)
        if seed is None:
            raise MarketplaceAgentNotFoundError(f"Agent '{agent_slug}' could not be found.")

        session_id = str(uuid4())
        session_token = self._create_session_token(session_id)
        socket_url = f"{settings.ORCHESTRATOR_WS_URL.rstrip('/')}/ws/user/{session_id}"
        now = self._now()
        session = MarketplaceSessionRead(
            sessionId=session_id,
            agentSlug=seed.slug,
            agentName=seed.name,
            actionId=payload.action_id,
            actionName=payload.action_name,
            priceUsdc=payload.price_usdc,
            estimatedDurationLabel=payload.estimated_duration_label,
            inputSummary=payload.input_summary,
            amountLockedUsdc=0,
            status="queued",
            mode=payload.mode,
            createdAt=now,
            redirectPath=f"/jobs/{session_id}",
            sessionToken=session_token,
            socketUrl=socket_url,
            resultPayload=None,
        )
        self.sessions[session_id] = session

        state = JobSessionState(
            session_id=session_id,
            user_id="00000000-0000-0000-0000-000000000000",
            phase=SessionPhase.STARTED,
            auth_token=session_token,
            created_at=now.isoformat(),
            last_activity_at=now.isoformat(),
            public_mode=True,
            marketplace_agent_slug=seed.slug,
            marketplace_agent_name=seed.name,
            marketplace_action_id=payload.action_id,
            marketplace_action_name=payload.action_name,
            marketplace_input_summary=payload.input_summary,
            marketplace_price_usdc=payload.price_usdc,
            marketplace_amount_locked_usdc=0,
        )
        await self.session_store.save(state)
        return session

    def get_session(self, session_id: str) -> MarketplaceSessionRead:
        session = self.sessions.get(session_id)
        if session is None:
            raise MarketplaceSessionNotFoundError(f"Session '{session_id}' could not be found.")
        return session

    def mark_processing(self, session_id: str) -> None:
        session = self.get_session(session_id)
        session.status = "processing"

    def mark_waiting_payment(self, session_id: str) -> None:
        session = self.get_session(session_id)
        session.status = "awaiting_payment"

    def mark_payment_locked(self, session_id: str, amount_locked_usdc: int) -> None:
        session = self.get_session(session_id)
        session.amount_locked_usdc = amount_locked_usdc
        session.status = "processing"

    def mark_completed(self, session_id: str, result_payload: dict[str, object]) -> None:
        session = self.get_session(session_id)
        session.status = "completed"
        session.result_payload = result_payload

    def mark_cancelled(self, session_id: str) -> None:
        session = self.get_session(session_id)
        session.status = "cancelled"

    def mark_closed(self, session_id: str) -> None:
        session = self.get_session(session_id)
        session.status = "closed"

    def _build_distribution(
        self, seed: PublicAgentSeed
    ) -> list[MarketplaceResponseDistributionItem]:
        fractions = self.RESPONSE_FRACTIONS.get(seed.speed_rank, self.RESPONSE_FRACTIONS[3])
        total_jobs = max(seed.jobs_completed, 1)
        raw_counts = [floor(total_jobs * fraction) for fraction in fractions]
        missing = total_jobs - sum(raw_counts)

        if missing > 0:
            raw_counts[-1] += missing

        distribution: list[MarketplaceResponseDistributionItem] = []
        running_percentage = 0.0

        for index, (label, average_minutes) in enumerate(self.RESPONSE_BANDS):
            count = raw_counts[index]
            if index == len(self.RESPONSE_BANDS) - 1:
                percentage = round(max(0.0, 100.0 - running_percentage), 1)
            else:
                percentage = round((count / total_jobs) * 100, 1)
                running_percentage += percentage

            adjusted_minutes = max(
                5,
                round(average_minutes * (0.92 + ((seed.speed_rank - 1) * 0.18))),
            )

            distribution.append(
                MarketplaceResponseDistributionItem(
                    label=label,
                    count=count,
                    percentage=percentage,
                    averageMinutes=adjusted_minutes,
                )
            )

        return distribution

    def _build_reviews(
        self, seed: PublicAgentSeed, now: datetime
    ) -> list[MarketplaceReviewItem]:
        review_total = max(8, min(12, seed.review_count // 12))
        base = sum(ord(char) for char in seed.slug)
        reviews: list[MarketplaceReviewItem] = []

        for index in range(review_total):
            reviewer_name = self.REVIEWER_NAMES[(base + index) % len(self.REVIEWER_NAMES)]
            company = self.COMPANIES[(base * 2 + index) % len(self.COMPANIES)]
            primary_tag = seed.tags[index % len(seed.tags)].lower()
            secondary_tag = seed.tags[(index + 1) % len(seed.tags)].lower()
            comment = self.COMMENT_TEMPLATES[index % len(self.COMMENT_TEMPLATES)].format(
                name=seed.name,
                primary=primary_tag,
                secondary=secondary_tag,
            )
            rating = 5 if ((base + index) % 5 != 0 or seed.rating >= 4.8) else 4
            created_at = now - timedelta(days=(index + 1) * 7 + (base % 6))

            reviews.append(
                MarketplaceReviewItem(
                    id=f"{seed.slug}-review-{index + 1}",
                    reviewerName=reviewer_name,
                    company=company,
                    rating=rating,
                    comment=comment,
                    jobTitle=f"{seed.tags[index % len(seed.tags)]} delivery sprint",
                    createdAt=created_at,
                )
            )

        return reviews

    def _now(self) -> datetime:
        return self.now or datetime.now(UTC)

    def _create_session_token(self, session_id: str) -> str:
        issued_at = self._now()
        expires_at = issued_at + timedelta(hours=24)
        payload = {
            "session_id": session_id,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def _format_minutes(self, minutes: int) -> str:
        if minutes < 60:
            return f"{minutes} min"

        if minutes < 24 * 60:
            hours = round(minutes / 60)
            return "1 hour" if hours == 1 else f"{hours} hours"

        days = round(minutes / (24 * 60))
        return "1 day" if days == 1 else f"{days} days"


marketplace_public_service = MarketplacePublicService()
