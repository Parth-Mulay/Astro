from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple

from sqlmodel import Session, select

from app.models import (
    Astrologer,
    AstrologerLanguage,
    AstrologerSpecialty,
    AvailabilitySlot,
    Intake,
    IssueCategory,
)


DEFAULT_WEIGHTS = {
    "specialty": 0.35,
    "language": 0.15,
    "rating": 0.15,
    "topic_success": 0.15,
    "availability": 0.10,
    "budget": 0.10,
    "response_speed": 0.05,
}


@dataclass
class MatchResult:
    astrologer: Astrologer
    score: float
    reasons: List[str]


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _normalize_rating(avg_rating: float) -> float:
    return _clamp01(avg_rating / 5.0)


def _normalize_response_speed(minutes: int) -> float:
    # 0 min => best; 120+ => worst
    return _clamp01(1.0 - (min(max(minutes, 0), 120) / 120.0))


def _budget_fit(intake_min: int, intake_max: int, astro_min: int, astro_max: int) -> float:
    # Prefer overlap; 1.0 if fully inside; downscale as overlap shrinks
    if intake_max <= 0:
        return 1.0
    overlap_min = max(intake_min, astro_min)
    overlap_max = min(intake_max, astro_max)
    if overlap_max <= overlap_min:
        return 0.0
    overlap = overlap_max - overlap_min
    span = max(intake_max - intake_min, 1)
    return _clamp01(overlap / span)


def _has_availability_soon(
    session: Session, astrologer_id: int, within_hours: int
) -> Tuple[bool, datetime | None]:
    now = datetime.utcnow()
    window_end = now + timedelta(hours=within_hours)
    slot = session.exec(
        select(AvailabilitySlot)
        .where(AvailabilitySlot.astrologer_id == astrologer_id)
        .where(AvailabilitySlot.is_booked == False)  # noqa: E712
        .where(AvailabilitySlot.start_at >= now)
        .where(AvailabilitySlot.start_at <= window_end)
        .order_by(AvailabilitySlot.start_at.asc())
        .limit(1)
    ).first()
    return (slot is not None, slot.start_at if slot else None)


def recommend_astrologers(
    session: Session,
    intake: Intake,
    top_k: int = 3,
    weights: dict | None = None,
) -> List[MatchResult]:
    weights = weights or DEFAULT_WEIGHTS

    issue = session.get(IssueCategory, intake.issue_category_id)
    issue_name = issue.name if issue else "the selected issue"

    # --- Hard filters (fast rejects) ---
    # verified, active
    base = (
        select(Astrologer)
        .where(Astrologer.active_status == True)  # noqa: E712
        .where(Astrologer.verified_identity == True)  # noqa: E712
    )
    astrologers = list(session.exec(base))
    if not astrologers:
        return []

    # filter: language must match either primary or in language table
    lang = intake.language.strip()
    allowed_ids = set()
    if lang:
        for a in astrologers:
            if a.primary_language.lower() == lang.lower():
                allowed_ids.add(a.id)
        rows = session.exec(
            select(AstrologerLanguage.astrologer_id).where(
                AstrologerLanguage.language.ilike(lang)
            )
        ).all()
        allowed_ids.update([r for r in rows])
        astrologers = [a for a in astrologers if a.id in allowed_ids]

    # filter: budget overlap (if provided)
    if intake.budget_max and intake.budget_max > 0:
        astrologers = [
            a
            for a in astrologers
            if not (a.max_budget < intake.budget_min or a.min_budget > intake.budget_max)
        ]

    # filter: specialty relevant to issue (must have tag)
    spec_rows = session.exec(
        select(AstrologerSpecialty.astrologer_id).where(
            AstrologerSpecialty.issue_category_id == intake.issue_category_id
        )
    ).all()
    spec_ids = set(spec_rows)
    astrologers = [a for a in astrologers if a.id in spec_ids]

    if not astrologers:
        return []

    # urgency -> availability window
    within_hours = 6 if intake.urgency == "high" else 24 if intake.urgency == "normal" else 72

    results: List[MatchResult] = []
    for a in astrologers:
        reasons: List[str] = []

        specialty_score = 1.0
        reasons.append(f"Specializes in {issue_name}")

        language_score = 1.0 if (lang and a.primary_language.lower() == lang.lower()) else 0.9
        reasons.append(f"Speaks {lang}" if lang else f"Language match")

        rating_score = _normalize_rating(a.average_rating)
        if a.average_rating:
            reasons.append(f"Strong ratings ({a.average_rating:.1f}/5)")

        topic_success_score = _clamp01(a.topic_success_rate)
        if a.topic_success_rate:
            reasons.append("High success for similar topics")

        has_soon, soon_at = _has_availability_soon(session, a.id, within_hours=within_hours)
        availability_score = 1.0 if has_soon else 0.0
        if has_soon and soon_at:
            reasons.append(f"Available soon ({soon_at:%Y-%m-%d %H:%M} UTC)")

        budget_score = _budget_fit(intake.budget_min, intake.budget_max, a.min_budget, a.max_budget)
        if intake.budget_max:
            reasons.append("Fits your budget range")

        response_speed_score = _normalize_response_speed(a.response_time_minutes)
        if a.response_time_minutes:
            reasons.append(f"Fast response (~{a.response_time_minutes} min)")

        score = (
            weights["specialty"] * specialty_score
            + weights["language"] * language_score
            + weights["rating"] * rating_score
            + weights["topic_success"] * topic_success_score
            + weights["availability"] * availability_score
            + weights["budget"] * budget_score
            + weights["response_speed"] * response_speed_score
        )

        results.append(MatchResult(astrologer=a, score=score, reasons=reasons[:4]))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]

