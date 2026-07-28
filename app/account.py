from __future__ import annotations

from sqlmodel import Session, select

from app.models import User, UserProfile


def get_or_create_profile(session: Session, user: User) -> UserProfile:
    prof = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    if prof:
        return prof
    prof = UserProfile(user_id=user.id, full_name=user.email.split("@")[0])
    session.add(prof)
    session.commit()
    session.refresh(prof)
    return prof


def wallet_balance(session: Session, user_id: int) -> int:
    prof = session.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
    return prof.wallet_balance if prof else 0


def deduct_wallet(session: Session, user_id: int, amount: int) -> bool:
    user = session.get(User, user_id)
    if not user:
        return False
    prof = get_or_create_profile(session, user)
    if prof.wallet_balance < amount:
        return False
    prof.wallet_balance -= amount
    session.add(prof)
    session.commit()
    return True


def add_wallet(session: Session, user_id: int, amount: int) -> None:
    user = session.get(User, user_id)
    if not user:
        return
    prof = get_or_create_profile(session, user)
    prof.wallet_balance += amount
    session.add(prof)
    session.commit()
