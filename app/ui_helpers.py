from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session, select

from app.account import get_or_create_profile
from app.models import Astrologer, AstrologerSpecialty, IssueCategory, User


def get_featured_astrologers(session: Session, limit: int = 12) -> list[Astrologer]:
    return list(
        session.exec(
            select(Astrologer)
            .where(Astrologer.active_status == True)  # noqa: E712
            .where(Astrologer.verified_identity == True)  # noqa: E712
            .order_by(Astrologer.average_rating.desc())
            .limit(limit)
        ).all()
    )


def get_specialty_names_for_astrologer(session: Session, astrologer_id: int) -> list[str]:
    rows = session.exec(
        select(IssueCategory.name)
        .join(AstrologerSpecialty, AstrologerSpecialty.issue_category_id == IssueCategory.id)
        .where(AstrologerSpecialty.astrologer_id == astrologer_id)
    ).all()
    return list(rows)


def page_context(session: Session, user: Optional[User] = None, **extra: Any) -> dict[str, Any]:
    ctx: dict[str, Any] = {"user": user, "wallet": 0}
    if user:
        prof = get_or_create_profile(session, user)
        ctx["wallet"] = prof.wallet_balance
    ctx.update(extra)
    return ctx
