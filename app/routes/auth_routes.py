from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.account import get_or_create_profile
from app.auth import clear_session, hash_password, set_session, verify_password
from app.db import get_session
from app.deps import current_user
from app.models import Role, User
from app.routes._shared import templates

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, session: Session = Depends(get_session), next: str = "/"):
    user = current_user(request, session)
    return templates.TemplateResponse(
        request, "login.html", {"error": None, "user": user, "next": next}
    )


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    return templates.TemplateResponse(
        request, "signup.html", {"error": None, "user": user}
    )


@router.post("/signup")
def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    user_type: str = Form("client"),
    years_of_experience: int = Form(5),
    primary_language: str = Form("English"),
    min_budget: int = Form(199),
    bio: str = Form(""),
    session: Session = Depends(get_session),
):
    email = email.strip().lower()
    if session.exec(select(User).where(User.email == email)).first():
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"error": "Email already registered. Please sign in.", "user": None},
            status_code=400,
        )
    role = Role.astrologer if user_type == "astrologer" else Role.user
    user = User(email=email, password_hash=hash_password(password), role=role)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    if role == Role.astrologer:
        from app.models import Astrologer, AvailabilitySlot, AstrologerSpecialty, IssueCategory
        astro = Astrologer(
            user_id=user.id,
            display_name=full_name.strip() or email.split("@")[0],
            bio=bio.strip() or f"{years_of_experience}+ years experience in Vedic Astrology.",
            active_status=True,
            verified_identity=True,
            years_of_experience=years_of_experience,
            primary_language=primary_language,
            min_budget=min_budget,
            max_budget=min_budget * 5,
        )
        session.add(astro)
        session.commit()
        
        # Seed initial availability slots
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        for h in [2, 6, 24, 48]:
            start = now + timedelta(hours=h)
            end = start + timedelta(minutes=45)
            session.add(
                AvailabilitySlot(
                    astrologer_id=astro.id,
                    start_at=start,
                    end_at=end,
                    is_booked=False
                )
            )
        session.commit()
        
        # Register for all issues/specialties
        cats = session.exec(select(IssueCategory)).all()
        for cat in cats:
            session.add(AstrologerSpecialty(astrologer_id=astro.id, issue_category_id=cat.id))
        session.commit()
        resp = RedirectResponse(url="/astro", status_code=303)
    else:
        prof = get_or_create_profile(session, user)
        if full_name.strip():
            prof.full_name = full_name.strip()
            session.add(prof)
            session.commit()
        resp = RedirectResponse(url="/account/profile", status_code=303)
        
    set_session(resp, user.id)
    return resp


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/flow/problem"),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == email.strip().lower())).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid email or password", "user": None, "next": next},
            status_code=400,
        )
    if getattr(user, "is_suspended", False):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Your account has been suspended by an administrator.", "user": None, "next": next},
            status_code=400,
        )
    get_or_create_profile(session, user)
    if user.role == Role.astrologer:
        resp = RedirectResponse(url="/astro", status_code=303)
    else:
        dest = next if next.startswith("/") else "/flow/problem"
        resp = RedirectResponse(url=dest, status_code=303)
    set_session(resp, user.id)
    return resp


@router.post("/logout")
def logout():
    resp = RedirectResponse(url="/", status_code=303)
    clear_session(resp)
    return resp
