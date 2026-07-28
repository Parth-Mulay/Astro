from __future__ import annotations

from sqlmodel import Session, select

from app.db import engine
from app.models import Astrologer, ConsultationSession, Feedback, SessionStatus


def recompute_astrologer_metrics() -> None:
    """
    Simple learning loop:
    - topic_success_rate ~= average(relevance_score)/5 for completed sessions with feedback
    - complaint_rate ~= complaints / feedback_count
    - average_rating ~= average(helpfulness_score)/5 * 5 (kept on 0..5 scale)
    """
    with Session(engine) as session:
        astrologers = session.exec(select(Astrologer)).all()
        for a in astrologers:
            # sessions with feedback
            rows = session.exec(
                select(Feedback)
                .join(ConsultationSession, ConsultationSession.id == Feedback.session_id)
                .where(ConsultationSession.astrologer_id == a.id)
                .where(ConsultationSession.status == SessionStatus.completed)
            ).all()

            if not rows:
                continue

            n = len(rows)
            helpful = sum(r.helpfulness_score for r in rows) / n
            clarity = sum(r.clarity_score for r in rows) / n
            relevance = sum(r.relevance_score for r in rows) / n
            complaints = sum(1 for r in rows if r.complaint_flag)

            a.average_rating = float(helpful)
            a.helpfulness_success_rate = float(helpful / 5.0)
            a.clarity_success_rate = float(clarity / 5.0)
            a.relevance_success_rate = float(relevance / 5.0)
            a.topic_success_rate = float(relevance / 5.0)
            a.complaint_rate = float(complaints / n)

            session.add(a)

        session.commit()


if __name__ == "__main__":
    recompute_astrologer_metrics()
    print("Metrics recomputed.")

