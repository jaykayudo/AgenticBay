from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from math import floor

from app.schemas.analytics import (
    ActionBreakdownItem,
    AgentAnalyticsResponse,
    AgentReviewItem,
    AgentSummaryMetrics,
    AnalyticsRange,
    ResponseTimeDistributionItem,
    RevenueBucket,
)


class AgentAnalyticsNotFoundError(Exception):
    """Raised when analytics are requested for an unknown agent."""


@dataclass(frozen=True)
class ReviewRecord:
    reviewer_name: str
    company: str
    rating: int
    comment: str


@dataclass(frozen=True)
class JobRecord:
    id: str
    agent_id: str
    completed_at: datetime
    title: str
    action: str
    amount: float
    was_successful: bool
    response_time_minutes: int
    review: ReviewRecord | None = None


@dataclass(frozen=True)
class AgentProfile:
    id: str
    name: str
    owner_name: str


@dataclass(frozen=True)
class DistributionBand:
    label: str
    minimum: int
    maximum: int | None = None


def _bucket_label(start: datetime, end: datetime) -> str:
    if start.date() == end.date():
        return start.strftime("%b %d")

    if start.month == end.month:
        return f"{start.strftime('%b %d')}-{end.strftime('%d')}"

    return f"{start.strftime('%b %d')}-{end.strftime('%b %d')}"


def _month_label(start: datetime) -> str:
    return start.strftime("%b")


def _normalized_percentages(counts: list[int]) -> list[float]:
    total = sum(counts)
    if total == 0:
        return [0.0 for _ in counts]

    percentages: list[float] = []
    running_total = 0.0

    for index, count in enumerate(counts):
        if index == len(counts) - 1:
            percentages.append(round(max(0.0, 100.0 - running_total), 1))
            continue

        percentage = round((count / total) * 100, 1)
        percentages.append(percentage)
        running_total += percentage

    return percentages


class AgentAnalyticsService:
    RESPONSE_TIME_BANDS = (
        DistributionBand("Under 15 min", 0, 14),
        DistributionBand("15-30 min", 15, 30),
        DistributionBand("31-60 min", 31, 60),
        DistributionBand("1-2 hours", 61, 120),
        DistributionBand("Over 2 hours", 121, None),
    )

    def __init__(self, now: datetime | None = None):
        self.now = now or datetime.now(UTC)
        self.agent_profiles = {
            "northstar-research": AgentProfile(
                id="northstar-research",
                name="Northstar Research",
                owner_name="Maya Chen",
            ),
            "signal-relay": AgentProfile(
                id="signal-relay",
                name="Signal Relay",
                owner_name="Jordan Hale",
            ),
            "harbor-assist": AgentProfile(
                id="harbor-assist",
                name="Harbor Assist",
                owner_name="Leah Morgan",
            ),
            "pattern-office": AgentProfile(
                id="pattern-office",
                name="Pattern Office",
                owner_name="Avery Cole",
            ),
        }
        self.job_records = self._build_job_records()

    def get_agent_analytics(
        self,
        agent_id: str,
        range_key: AnalyticsRange,
    ) -> AgentAnalyticsResponse:
        profile = self.agent_profiles.get(agent_id)
        if profile is None:
            raise AgentAnalyticsNotFoundError(f"Agent '{agent_id}' could not be found.")

        filtered_jobs = self._filter_jobs(agent_id, range_key)
        revenue_series = self._build_revenue_series(filtered_jobs, range_key)
        action_breakdown = self._build_action_breakdown(filtered_jobs)
        reviews = self._build_reviews(filtered_jobs)
        response_distribution = self._build_response_distribution(filtered_jobs)

        total_jobs = len(filtered_jobs)
        total_earned = round(sum(job.amount for job in filtered_jobs), 2)
        successful_jobs = sum(1 for job in filtered_jobs if job.was_successful)
        success_rate = round((successful_jobs / total_jobs) * 100, 1) if total_jobs else 0.0
        avg_job_value = round((total_earned / total_jobs), 2) if total_jobs else 0.0

        return AgentAnalyticsResponse(
            agent_id=profile.id,
            agent_name=profile.name,
            owner_name=profile.owner_name,
            range=range_key,
            generated_at=self.now,
            summary=AgentSummaryMetrics(
                total_jobs=total_jobs,
                total_earned=total_earned,
                success_rate=success_rate,
                avg_job_value=avg_job_value,
            ),
            revenue_series=revenue_series,
            action_breakdown=action_breakdown,
            reviews=reviews,
            response_time_distribution=response_distribution,
        )

    def _build_job_records(self) -> tuple[JobRecord, ...]:
        northstar_jobs = self._seed_agent_jobs(
            agent_id="northstar-research",
            base_amount=3100,
            actions=(
                "Market research brief",
                "Competitor analysis",
                "Customer insight synthesis",
                "Executive summary delivery",
            ),
            titles=(
                "Expansion readiness brief",
                "Competitor positioning report",
                "Customer journey signal pack",
                "Quarterly insight memo",
                "Enterprise buyer research sprint",
                "Launch narrative evidence pack",
            ),
            response_times=(12, 18, 28, 36, 54, 78, 144, 21, 42, 16, 63, 32),
            review_templates=(
                ReviewRecord(
                    reviewer_name="Rina Patel",
                    company="Pearl Labs",
                    rating=5,
                    comment="Fast turnaround, sharp synthesis, and unusually easy to operationalize.",
                ),
                ReviewRecord(
                    reviewer_name="Marcus Lee",
                    company="Fieldline",
                    rating=4,
                    comment="Very strong research quality with a concise final narrative for leadership.",
                ),
                ReviewRecord(
                    reviewer_name="Nadia Brooks",
                    company="Northwind Health",
                    rating=5,
                    comment="The insight framing helped us make the staffing call in one review pass.",
                ),
                ReviewRecord(
                    reviewer_name="Arjun Rao",
                    company="Sienna Cloud",
                    rating=5,
                    comment="High signal work and the action recommendations were immediately usable.",
                ),
                ReviewRecord(
                    reviewer_name="Talia Grant",
                    company="Hale Commerce",
                    rating=4,
                    comment="Clear thinking throughout and a polished delivery package for stakeholders.",
                ),
            ),
        )

        signal_jobs = self._seed_agent_jobs(
            agent_id="signal-relay",
            base_amount=2100,
            actions=(
                "Workflow automation",
                "CRM routing update",
                "Lead qualification logic",
                "Operational QA pass",
            ),
            titles=(
                "Lead routing rebuild",
                "Ops automation sprint",
                "CRM workflow hardening",
                "Qualification rules refresh",
            ),
            response_times=(8, 14, 22, 27, 34, 49, 68, 105, 18, 24, 39, 57),
            review_templates=(
                ReviewRecord(
                    reviewer_name="Gina Moss",
                    company="Hale Commerce",
                    rating=5,
                    comment="Automation quality was solid and the rollout needed almost no cleanup.",
                ),
                ReviewRecord(
                    reviewer_name="Elijah Ford",
                    company="Meridian Works",
                    rating=4,
                    comment="The logic updates landed quickly and reduced handoffs in the queue.",
                ),
                ReviewRecord(
                    reviewer_name="Noah Kent",
                    company="Brightwell",
                    rating=5,
                    comment="Great communication and the workflow changes improved lead handling immediately.",
                ),
            ),
        )

        harbor_jobs = self._seed_agent_jobs(
            agent_id="harbor-assist",
            base_amount=1600,
            actions=(
                "Inbox triage coverage",
                "Tier-1 support handling",
                "Refund policy response",
                "Escalation tagging pass",
            ),
            titles=(
                "Weekend inbox coverage",
                "Priority response burst",
                "Refund queue clean-up",
                "Escalation classification sprint",
            ),
            response_times=(7, 11, 14, 19, 24, 33, 41, 58, 16, 22, 37, 52),
            review_templates=(
                ReviewRecord(
                    reviewer_name="Jenna Marsh",
                    company="Morningside Health",
                    rating=5,
                    comment="Very reliable coverage and our queue stayed stable through peak volume.",
                ),
                ReviewRecord(
                    reviewer_name="Cameron Blake",
                    company="Sable Finance",
                    rating=4,
                    comment="Fast handling with consistent tone and useful escalation notes.",
                ),
                ReviewRecord(
                    reviewer_name="Priya Shah",
                    company="Rivergrid",
                    rating=5,
                    comment="The support handoff quality was excellent and saved real ops time.",
                ),
            ),
        )

        pattern_jobs = self._seed_agent_jobs(
            agent_id="pattern-office",
            base_amount=2400,
            actions=(
                "Design system documentation",
                "Component audit",
                "Workflow enablement pack",
                "Interface QA review",
            ),
            titles=(
                "Component documentation refresh",
                "Design QA pass",
                "System adoption sprint",
                "Interaction audit pack",
            ),
            response_times=(18, 25, 31, 44, 56, 73, 88, 126, 29, 34, 47, 67),
            review_templates=(
                ReviewRecord(
                    reviewer_name="Anika Rose",
                    company="Sienna Cloud",
                    rating=5,
                    comment="The documentation quality was strong and removed friction for our product team.",
                ),
                ReviewRecord(
                    reviewer_name="Milo Greene",
                    company="Northscale",
                    rating=4,
                    comment="Good structure, clean recommendations, and polished delivery assets.",
                ),
                ReviewRecord(
                    reviewer_name="Eva Turner",
                    company="Crestline",
                    rating=5,
                    comment="A thoughtful review that helped us close several quality issues quickly.",
                ),
            ),
        )

        return northstar_jobs + signal_jobs + harbor_jobs + pattern_jobs

    def _seed_agent_jobs(
        self,
        *,
        agent_id: str,
        base_amount: float,
        actions: tuple[str, ...],
        titles: tuple[str, ...],
        response_times: tuple[int, ...],
        review_templates: tuple[ReviewRecord, ...],
    ) -> tuple[JobRecord, ...]:
        day_offsets = (1, 2, 3, 4, 6, 9, 13, 18, 24, 31, 40, 52, 68, 83, 101, 123)
        jobs: list[JobRecord] = []

        for index, day_offset in enumerate(day_offsets):
            action = actions[index % len(actions)]
            title = titles[index % len(titles)]
            completed_at = self.now - timedelta(days=day_offset, hours=(index % 5) + 2)
            amount = round(base_amount + (index % 4) * 420 + floor(index / 2) * 65, 2)
            was_successful = index % 6 != 4
            response_minutes = response_times[index % len(response_times)]
            review = review_templates[index % len(review_templates)] if index < 10 else None

            jobs.append(
                JobRecord(
                    id=f"{agent_id}-job-{index + 1}",
                    agent_id=agent_id,
                    completed_at=completed_at,
                    title=title,
                    action=action,
                    amount=amount,
                    was_successful=was_successful,
                    response_time_minutes=response_minutes,
                    review=review,
                )
            )

        return tuple(jobs)

    def _filter_jobs(self, agent_id: str, range_key: AnalyticsRange) -> list[JobRecord]:
        jobs = [job for job in self.job_records if job.agent_id == agent_id]
        if range_key == "all":
            return sorted(jobs, key=lambda job: job.completed_at)

        day_windows = {"7d": 7, "30d": 30, "90d": 90}
        cutoff = self.now - timedelta(days=day_windows[range_key])
        filtered = [job for job in jobs if job.completed_at >= cutoff]
        return sorted(filtered, key=lambda job: job.completed_at)

    def _build_revenue_series(
        self, jobs: list[JobRecord], range_key: AnalyticsRange
    ) -> list[RevenueBucket]:
        if range_key == "all":
            return self._build_monthly_series(jobs)

        interval_days = {"7d": 1, "30d": 5, "90d": 15}[range_key]
        bucket_count = {"7d": 7, "30d": 6, "90d": 6}[range_key]
        buckets: list[RevenueBucket] = []

        current_day = datetime.combine(self.now.date(), time.min, tzinfo=UTC)
        current_day_end = current_day + timedelta(hours=23, minutes=59, seconds=59)

        for index in range(bucket_count):
            start = current_day - timedelta(days=(interval_days * (bucket_count - index)) - 1)
            end = min(
                current_day_end,
                start + timedelta(days=interval_days - 1, hours=23, minutes=59, seconds=59),
            )
            bucket_jobs = [job for job in jobs if start <= job.completed_at <= end]

            buckets.append(
                RevenueBucket(
                    label=_bucket_label(start, end),
                    amount=round(sum(job.amount for job in bucket_jobs), 2),
                    jobs=len(bucket_jobs),
                )
            )

        return buckets

    def _build_monthly_series(self, jobs: list[JobRecord]) -> list[RevenueBucket]:
        if not jobs:
            current_month = datetime.combine(
                date(self.now.year, self.now.month, 1),
                time.min,
                tzinfo=UTC,
            )
            return [RevenueBucket(label=_month_label(current_month), amount=0.0, jobs=0)]

        first_job = jobs[0].completed_at
        month_cursor = datetime.combine(
            date(first_job.year, first_job.month, 1),
            time.min,
            tzinfo=UTC,
        )
        last_month = datetime.combine(
            date(self.now.year, self.now.month, 1),
            time.min,
            tzinfo=UTC,
        )

        buckets: list[RevenueBucket] = []
        while month_cursor <= last_month:
            if month_cursor.month == 12:
                next_month = datetime.combine(
                    date(month_cursor.year + 1, 1, 1),
                    time.min,
                    tzinfo=UTC,
                )
            else:
                next_month = datetime.combine(
                    date(month_cursor.year, month_cursor.month + 1, 1),
                    time.min,
                    tzinfo=UTC,
                )

            bucket_jobs = [job for job in jobs if month_cursor <= job.completed_at < next_month]
            buckets.append(
                RevenueBucket(
                    label=_month_label(month_cursor),
                    amount=round(sum(job.amount for job in bucket_jobs), 2),
                    jobs=len(bucket_jobs),
                )
            )
            month_cursor = next_month

        return buckets

    def _build_action_breakdown(self, jobs: list[JobRecord]) -> list[ActionBreakdownItem]:
        grouped: dict[str, list[JobRecord]] = {}
        for job in jobs:
            grouped.setdefault(job.action, []).append(job)

        sorted_groups = sorted(
            grouped.items(),
            key=lambda item: (-len(item[1]), -sum(job.amount for job in item[1]), item[0]),
        )
        percentages = _normalized_percentages([len(action_jobs) for _, action_jobs in sorted_groups])

        items = [
            ActionBreakdownItem(
                action=action,
                count=len(action_jobs),
                percentage=percentages[index],
                earned=round(sum(job.amount for job in action_jobs), 2),
            )
            for index, (action, action_jobs) in enumerate(sorted_groups)
        ]

        return items

    def _build_reviews(self, jobs: list[JobRecord]) -> list[AgentReviewItem]:
        review_jobs = [job for job in jobs if job.review is not None]
        latest_reviews = sorted(review_jobs, key=lambda job: job.completed_at, reverse=True)[:5]

        return [
            AgentReviewItem(
                id=job.id,
                reviewer_name=job.review.reviewer_name,
                company=job.review.company,
                rating=job.review.rating,
                comment=job.review.comment,
                job_title=job.title,
                created_at=job.completed_at,
            )
            for job in latest_reviews
            if job.review is not None
        ]

    def _build_response_distribution(
        self, jobs: list[JobRecord]
    ) -> list[ResponseTimeDistributionItem]:
        band_job_groups = [
            [
                job
                for job in jobs
                if job.response_time_minutes >= band.minimum
                and (band.maximum is None or job.response_time_minutes <= band.maximum)
            ]
            for band in self.RESPONSE_TIME_BANDS
        ]
        percentages = _normalized_percentages([len(band_jobs) for band_jobs in band_job_groups])
        distribution: list[ResponseTimeDistributionItem] = []

        for index, band in enumerate(self.RESPONSE_TIME_BANDS):
            band_jobs = band_job_groups[index]
            average_minutes = (
                round(sum(job.response_time_minutes for job in band_jobs) / len(band_jobs))
                if band_jobs
                else 0
            )
            distribution.append(
                ResponseTimeDistributionItem(
                    label=band.label,
                    count=len(band_jobs),
                    percentage=percentages[index],
                    average_minutes=average_minutes,
                )
            )

        return distribution
