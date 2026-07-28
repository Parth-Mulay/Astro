from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.account import add_wallet, get_or_create_profile
from app.db import get_session
from app.deps import require_user
from app.models import ChildAstroOrder, ConsultationSession, Feedback, Intake, IssueCategory, KundliMatchRecord, KundliRecord, SavedReport
from app.routes._shared import templates
from app.services.horoscope import sun_sign_from_dob

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    prof = get_or_create_profile(session, user)
    return templates.TemplateResponse(
        request, "profile.html", {"user": user, "prof": prof}
    )


@router.post("/profile")
def profile_save(
    request: Request,
    full_name: str = Form(""),
    date_of_birth: str = Form(""),
    birth_time: str = Form(""),
    birth_place: str = Form(""),
    zodiac_sign: str = Form("aries"),
    preferred_language: str = Form("English"),
    session: Session = Depends(get_session),
):
    user = require_user(request, session)
    prof = get_or_create_profile(session, user)
    prof.full_name = full_name.strip()
    if date_of_birth and date_of_birth.strip():
        prof.date_of_birth = date.fromisoformat(date_of_birth.strip())
        prof.zodiac_sign = sun_sign_from_dob(prof.date_of_birth)
    else:
        prof.zodiac_sign = zodiac_sign
    prof.birth_time = birth_time
    prof.birth_place = birth_place
    prof.preferred_language = preferred_language
    session.add(prof)
    session.commit()
    return RedirectResponse(url="/account/profile", status_code=303)


@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    intakes = session.exec(
        select(Intake).where(Intake.user_id == user.id).order_by(Intake.created_at.desc())
    ).all()
    sessions = session.exec(
        select(ConsultationSession)
        .where(ConsultationSession.user_id == user.id)
        .order_by(ConsultationSession.created_at.desc())
    ).all()
    kundlis = session.exec(
        select(KundliRecord).where(KundliRecord.user_id == user.id).order_by(KundliRecord.created_at.desc())
    ).all()
    matches = session.exec(
        select(KundliMatchRecord).where(KundliMatchRecord.user_id == user.id).order_by(KundliMatchRecord.created_at.desc())
    ).all()
    reports = session.exec(
        select(SavedReport).where(SavedReport.user_id == user.id).order_by(SavedReport.created_at.desc())
    ).all()
    child_orders = session.exec(
        select(ChildAstroOrder).where(ChildAstroOrder.user_id == user.id).order_by(ChildAstroOrder.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        request,
        "history.html",
        {
            "user": user,
            "intakes": intakes,
            "sessions": sessions,
            "kundlis": kundlis,
            "matches": matches,
            "reports": reports,
            "child_orders": child_orders,
        },
    )


@router.get("/wallet", response_class=HTMLResponse)
def wallet_page(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    prof = get_or_create_profile(session, user)
    from app.db import get_config
    pkg1 = int(get_config(session, "recharge_option_1", "100"))
    pkg2 = int(get_config(session, "recharge_option_2", "500"))
    pkg3 = int(get_config(session, "recharge_option_3", "1000"))
    pkg4 = int(get_config(session, "recharge_option_4", "2000"))
    packages = [pkg1, pkg2, pkg3, pkg4]
    return templates.TemplateResponse(
        request, "wallet.html", {"user": user, "prof": prof, "message": None, "packages": packages}
    )


@router.post("/wallet/recharge")
def wallet_recharge(
    request: Request,
    amount: int = Form(500),
    session: Session = Depends(get_session),
):
    user = require_user(request, session)
    add_wallet(session, user.id, max(amount, 0))
    prof = get_or_create_profile(session, user)
    return templates.TemplateResponse(
        request,
        "wallet.html",
        {"user": user, "prof": prof, "message": f"Added ₹{amount} to wallet (demo payment)."},
    )


@router.get("/reports/{report_id}", response_class=HTMLResponse)
def view_report(request: Request, report_id: int, session: Session = Depends(get_session)):
    user = require_user(request, session)
    report = session.get(SavedReport, report_id)
    if not report or report.user_id != user.id:
        return RedirectResponse("/account/history", status_code=303)
    return templates.TemplateResponse(
        request, "report_view.html", {"user": user, "report": report}
    )
