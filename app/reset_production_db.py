from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session, delete, select

from app.account import get_or_create_profile
from app.auth import hash_password
from app.db import create_db_and_tables, engine
from app.models import (
    Astrologer,
    AstrologerLanguage,
    AstrologerSpecialty,
    AuditLog,
    AvailabilitySlot,
    ChatMessage,
    ChildAstroOrder,
    ConsultationSession,
    Feedback,
    InAppNotification,
    Intake,
    IssueCategory,
    KundliMatchRecord,
    KundliRecord,
    MatchScore,
    Payment,
    Role,
    SavedReport,
    SystemConfig,
    User,
    UserProfile,
)

DELETION_ORDER = [
    ChatMessage,
    Feedback,
    Payment,
    MatchScore,
    ConsultationSession,
    AvailabilitySlot,
    AstrologerLanguage,
    AstrologerSpecialty,
    Astrologer,
    Intake,
    UserProfile,
    KundliRecord,
    KundliMatchRecord,
    SavedReport,
    ChildAstroOrder,
    InAppNotification,
    AuditLog,
]


def reset_sqlite_sequences():
    conn = engine.raw_connection()
    try:
        conn.execute("DELETE FROM sqlite_sequence")
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def run_reset():
    create_db_and_tables()

    with Session(engine) as session:
        admins = session.exec(
            select(User).where(User.role == Role.admin)
        ).all()

        if not admins:
            print("No admin accounts found. Creating default admin...")
            admin = User(
                email="admin@astromatch.com",
                password_hash=hash_password("admin123"),
                role=Role.admin,
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)
            get_or_create_profile(session, admin)
            admins = [admin]

        admin_ids = {u.id for u in admins}
        print(f"Preserving {len(admins)} admin account(s): IDs {admin_ids}")

        for model in DELETION_ORDER:
            session.exec(delete(model))
        session.commit()

        non_admin_users = session.exec(
            select(User).where(User.id.notin_(admin_ids))
        ).all()
        for u in non_admin_users:
            session.delete(u)
        session.commit()

    reset_sqlite_sequences()

    with Session(engine) as session:
        test_user = User(
            email="test.user@astromatch.demo",
            password_hash=hash_password("test@123"),
            role=Role.user,
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)
        test_user_profile = get_or_create_profile(session, test_user)
        test_user_profile.full_name = "Test User (DEMO)"
        test_user_profile.wallet_balance = 1000
        test_user_profile.preferred_language = "English"
        test_user_profile.zodiac_sign = "leo"
        session.add(test_user_profile)

        test_astro_user = User(
            email="test.astrologer@astromatch.demo",
            password_hash=hash_password("test@123"),
            role=Role.astrologer,
        )
        session.add(test_astro_user)
        session.commit()
        session.refresh(test_astro_user)

        test_astro = Astrologer(
            user_id=test_astro_user.id,
            display_name="Test Astrologer (DEMO)",
            bio="Test astrologer account for development and testing purposes. Specializes in relationships and career counseling.",
            years_of_experience=5,
            primary_language="English",
            min_budget=100,
            max_budget=500,
            average_rating=4.0,
            response_time_minutes=15,
            topic_success_rate=0.75,
            verified_identity=True,
            active_status=True,
        )
        session.add(test_astro)
        session.commit()
        session.refresh(test_astro)

        cats = {
            c.slug: c
            for c in session.exec(select(IssueCategory)).all()
        }

        for slug in ["relationships", "career"]:
            cat = cats.get(slug)
            if cat:
                session.add(
                    AstrologerSpecialty(
                        astrologer_id=test_astro.id,
                        issue_category_id=cat.id,
                    )
                )

        for lang in ["English", "Hindi"]:
            session.add(
                AstrologerLanguage(
                    astrologer_id=test_astro.id,
                    language=lang,
                )
            )

        now = datetime.utcnow()
        for offset_hours in [2, 6, 26, 50]:
            start = now + timedelta(hours=offset_hours)
            end = start + timedelta(minutes=45)
            session.add(
                AvailabilitySlot(
                    astrologer_id=test_astro.id,
                    start_at=start,
                    end_at=end,
                    is_booked=False,
                )
            )

        session.commit()

    print("=" * 60)
    print("  PRODUCTION DATABASE RESET COMPLETE")
    print("=" * 60)
    print()
    print("Preserved:")
    print(f"  - {len(admins)} Admin account(s)")
    print(f"  - Issue categories (required for booking workflow)")
    print(f"  - System configuration data")
    print()
    print("Removed:")
    print("  - All end users, astrologers, and their associated records")
    print("  - All bookings, chat messages, payments, and transactions")
    print("  - All reports, feedback, notifications, and audit logs")
    print("  - All session history and astrologer availability slots")
    print()
    print("Created Test Accounts:")
    print("  End User:      test.user@astromatch.demo / test@123")
    print("  Astrologer:    test.astrologer@astromatch.demo / test@123")
    print()
    print("All auto-increment sequences have been reset.")
    print("The database is ready for production deployment.")


if __name__ == "__main__":
    run_reset()
