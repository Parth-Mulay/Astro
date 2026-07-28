from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.account import get_or_create_profile
from app.auth import hash_password
from app.db import create_db_and_tables, engine
from app.models import (
    Astrologer,
    AstrologerLanguage,
    AstrologerSpecialty,
    AvailabilitySlot,
    IssueCategory,
    Role,
    User,
)


ISSUES = [
    ("relationships", "Relationships / Marriage"),
    ("career", "Career / Job"),
    ("finance", "Finance / Money"),
    ("health", "Health / Wellbeing"),
    ("family", "Family"),
]


def _get_or_create_user(session: Session, email: str, role: Role) -> User:
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        return existing
    u = User(email=email, password_hash=hash_password("password"), role=role)
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def run_seed() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        demo_user = _get_or_create_user(session, "user@example.com", Role.user)
        admin_user = _get_or_create_user(session, "admin@example.com", Role.admin)
        get_or_create_profile(session, demo_user)
        get_or_create_profile(session, admin_user)

        # categories
        existing = {c.slug: c for c in session.exec(select(IssueCategory)).all()}
        for slug, name in ISSUES:
            if slug not in existing:
                session.add(IssueCategory(slug=slug, name=name))
        session.commit()

        cats = {c.slug: c for c in session.exec(select(IssueCategory)).all()}

        # astrologers (as users with role=astrologer)
        def add_astro(
            email: str,
            name: str,
            years: int,
            primary_language: str,
            langs: list[str],
            specialties: list[str],
            min_budget: int,
            max_budget: int,
            avg_rating: float,
            response_min: int,
            topic_success: float,
            verified: bool = True,
            active: bool = True,
        ):
            u = _get_or_create_user(session, email, Role.astrologer)
            a = session.exec(select(Astrologer).where(Astrologer.user_id == u.id)).first()
            if not a:
                a = Astrologer(
                    user_id=u.id,
                    display_name=name,
                    bio=f"{years}+ years experience",
                    years_of_experience=years,
                    primary_language=primary_language,
                    min_budget=min_budget,
                    max_budget=max_budget,
                    average_rating=avg_rating,
                    response_time_minutes=response_min,
                    topic_success_rate=topic_success,
                    verified_identity=verified,
                    active_status=active,
                )
                session.add(a)
                session.commit()
                session.refresh(a)

            # languages
            for l in langs:
                try:
                    session.add(AstrologerLanguage(astrologer_id=a.id, language=l))
                    session.commit()
                except Exception:
                    session.rollback()

            # specialties
            for slug in specialties:
                cat = cats[slug]
                try:
                    session.add(AstrologerSpecialty(astrologer_id=a.id, issue_category_id=cat.id))
                    session.commit()
                except Exception:
                    session.rollback()

            # availability slots
            now = datetime.utcnow()
            for h in [2, 6, 26, 50]:
                start = now + timedelta(hours=h)
                end = start + timedelta(minutes=45)
                existing_slot = session.exec(
                    select(AvailabilitySlot)
                    .where(AvailabilitySlot.astrologer_id == a.id)
                    .where(AvailabilitySlot.start_at == start)
                ).first()
                if not existing_slot:
                    session.add(
                        AvailabilitySlot(
                            astrologer_id=a.id,
                            start_at=start,
                            end_at=end,
                            is_booked=False,
                        )
                    )
            session.commit()

        add_astro(
            "astro1@example.com",
            "Ananya Sharma",
            years=9,
            primary_language="Hindi",
            langs=["Hindi", "English"],
            specialties=["relationships", "family"],
            min_budget=199,
            max_budget=599,
            avg_rating=4.7,
            response_min=12,
            topic_success=0.82,
        )
        add_astro(
            "astro2@example.com",
            "Rohit Mehta",
            years=6,
            primary_language="English",
            langs=["English"],
            specialties=["career", "finance"],
            min_budget=299,
            max_budget=999,
            avg_rating=4.5,
            response_min=20,
            topic_success=0.78,
        )
        add_astro(
            "astro3@example.com",
            "Priya Nair",
            years=12,
            primary_language="Malayalam",
            langs=["Malayalam", "English"],
            specialties=["health", "family"],
            min_budget=149,
            max_budget=499,
            avg_rating=4.2,
            response_min=35,
            topic_success=0.70,
        )
        add_astro(
            "astro4@example.com",
            "Karan Singh",
            years=4,
            primary_language="Hindi",
            langs=["Hindi"],
            specialties=["career", "relationships"],
            min_budget=99,
            max_budget=299,
            avg_rating=4.0,
            response_min=15,
            topic_success=0.62,
        )


if __name__ == "__main__":
    run_seed()
    print("Seed complete. Login: user@example.com / password")

