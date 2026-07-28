from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.db import get_session, get_config, set_config
from app.deps import require_user
from app.models import (
    Role,
    User,
    UserProfile,
    Astrologer,
    ConsultationSession,
    Payment,
    Feedback,
    IssueCategory,
    AuditLog,
    InAppNotification,
    ChatMessage,
    SavedReport,
    KundliRecord,
    KundliMatchRecord,
    PaymentStatus,
    SessionStatus,
    ConsultType
)
from app.routes._shared import templates
from app.ui_helpers import page_context

from app.settings import settings

router = APIRouter(prefix="/admin", tags=["admin"])

UPLOADS_DIR = Path(settings.UPLOADS_DIR)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def require_admin(request: Request, session: Session) -> User:
    u = require_user(request, session)
    if u.role != Role.admin:
        raise HTTPException(status_code=403, detail="Access denied: Admin only")
    return u


def log_audit(session: Session, action: str, target: str, user_id: Optional[int] = None, ip_address: str = "") -> None:
    log = AuditLog(
        user_id=user_id,
        action=action,
        target=target,
        ip_address=ip_address or "",
        created_at=datetime.utcnow()
    )
    session.add(log)
    session.commit()


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, session_db: Session = Depends(get_session)):
    admin = require_admin(request, session_db)
    
    # 1. Dashboard Stats
    users = session_db.exec(select(User)).all()
    clients = [u for u in users if u.role == Role.user]
    astrologers = [u for u in users if u.role == Role.astrologer]
    
    profiles = session_db.exec(select(UserProfile)).all()
    profiles_map = {p.user_id: p for p in profiles}
    
    astrologers_profile = session_db.exec(select(Astrologer)).all()
    astrologers_profile_map = {a.user_id: a for a in astrologers_profile}
    astrologers_by_id = {a.id: a for a in astrologers_profile}
    
    sessions = session_db.exec(select(ConsultationSession).order_by(ConsultationSession.created_at.desc())).all()
    payments = session_db.exec(select(Payment).order_by(Payment.created_at.desc())).all()
    feedbacks = session_db.exec(select(Feedback).order_by(Feedback.created_at.desc())).all()
    categories = session_db.exec(select(IssueCategory).order_by(IssueCategory.name.asc())).all()
    audit_logs = session_db.exec(select(AuditLog).order_by(AuditLog.created_at.desc())).all()
    notifications = session_db.exec(select(InAppNotification).order_by(InAppNotification.created_at.desc())).all()
    
    reports = session_db.exec(select(SavedReport).order_by(SavedReport.created_at.desc())).all()
    kundlis = session_db.exec(select(KundliRecord).order_by(KundliRecord.created_at.desc())).all()
    matches = session_db.exec(select(KundliMatchRecord).order_by(KundliMatchRecord.created_at.desc())).all()
    
    # Mapping helpers
    users_map = {u.id: u.email for u in users}
    astrologers_map = {a.id: a.display_name for a in astrologers_profile}
    
    total_revenue = sum(p.amount for p in payments if p.status == PaymentStatus.completed)
    active_sessions = [s for s in sessions if s.status == SessionStatus.booked]
    complaints = [f for f in feedbacks if f.complaint_flag]
    refund_requests = [f for f in feedbacks if f.refund_requested]
    
    # CMS / Configs
    commission_rate = float(get_config(session_db, "commission_rate", "0.20"))
    announcement_text = get_config(session_db, "announcement_text", "Welcome to AstroMatch!")
    maintenance_mode = get_config(session_db, "maintenance_mode", "false")
    support_email = get_config(session_db, "support_email", "support@astromatch.com")
    
    pricing = {
        "price_horoscope": get_config(session_db, "price_horoscope", "20"),
        "price_kundli": get_config(session_db, "price_kundli", "50"),
        "price_match": get_config(session_db, "price_match", "50"),
        "price_ask_ai": get_config(session_db, "price_ask_ai", "25"),
        "recharge_option_1": get_config(session_db, "recharge_option_1", "100"),
        "recharge_option_2": get_config(session_db, "recharge_option_2", "500"),
        "recharge_option_3": get_config(session_db, "recharge_option_3", "1000"),
        "recharge_option_4": get_config(session_db, "recharge_option_4", "2000"),
        "commission_rate": get_config(session_db, "commission_rate", "20"), # percentage
        "announcement_text": announcement_text,
        "maintenance_mode": maintenance_mode,
        "support_email": support_email,
    }
    
    # 2. Payouts Logic
    # For each astrologer, compute completed sessions total earnings and payout details
    payout_report = []
    for a in astrologers_profile:
        a_sessions = [s for s in sessions if s.astrologer_id == a.id and s.status == SessionStatus.completed]
        total_sessions_count = len(a_sessions)
        
        # Total earnings = sum(s.price)
        total_earned = sum(s.price for s in a_sessions)
        
        # Pending payout = sum(s.price * (1 - commission_rate)) for s where not payout_processed
        pending_sessions = [s for s in a_sessions if not getattr(s, "payout_processed", False)]
        pending_payout = sum(s.price * (1.0 - commission_rate) for s in pending_sessions)
        
        processed_sessions = [s for s in a_sessions if getattr(s, "payout_processed", False)]
        processed_payout = sum(s.price * (1.0 - commission_rate) for s in processed_sessions)
        
        payout_report.append({
            "astrologer": a,
            "total_sessions": total_sessions_count,
            "total_earned": total_earned,
            "processed_payout": processed_payout,
            "pending_payout": pending_payout,
            "pending_count": len(pending_sessions)
        })
        
    # 3. Chat Management Logs
    # Fetch chats with messages
    chat_sessions_ids = list(set([m.session_id for m in session_db.exec(select(ChatMessage)).all()]))
    chat_logs = []
    for sid in chat_sessions_ids:
        sess = session_db.get(ConsultationSession, sid)
        if not sess:
            continue
        msgs = session_db.exec(
            select(ChatMessage).where(ChatMessage.session_id == sid).order_by(ChatMessage.created_at.asc())
        ).all()
        chat_logs.append({
            "session_id": sid,
            "client_email": users_map.get(sess.user_id, "Unknown"),
            "astrologer_name": astrologers_map.get(sess.astrologer_id, "Unknown"),
            "messages": msgs,
            "created_at": sess.created_at
        })
        
    # 4. Files List
    files = []
    for f in UPLOADS_DIR.iterdir():
        if f.is_file():
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "path": f"/uploads/{f.name}",
                "modified": datetime.fromtimestamp(f.stat().st_mtime)
            })

    # 5. Support / Client mappings & Analytics helpers
    feedback_client_map = {}
    for fb in feedbacks:
        sess = session_db.get(ConsultationSession, fb.session_id)
        if sess:
            feedback_client_map[fb.id] = users_map.get(sess.user_id, "Client User")
        else:
            feedback_client_map[fb.id] = "Client User"

    sessions_completed_count = len([s for s in sessions if s.status == SessionStatus.completed])
    sessions_cancelled_count = len([s for s in sessions if s.status == SessionStatus.cancelled])
    sessions_booked_count = len([s for s in sessions if s.status == SessionStatus.booked])
    
    chat_sessions_count = len([s for s in sessions if s.consult_type == ConsultType.chat])
    call_sessions_count = len([s for s in sessions if s.consult_type == ConsultType.call])
    
    total_recharges_count = len([p for p in payments if p.status == PaymentStatus.completed])

    ctx = page_context(
        session_db, admin,
        clients=clients,
        astrologers=astrologers,
        profiles_map=profiles_map,
        astrologers_profile=astrologers_profile,
        astrologers_profile_map=astrologers_profile_map,
        all_sessions=sessions,
        payments=payments,
        feedbacks=feedbacks,
        categories=categories,
        audit_logs=audit_logs,
        notifications=notifications,
        reports=reports,
        kundlis=kundlis,
        matches=matches,
        users_map=users_map,
        astrologers_map=astrologers_map,
        total_revenue=total_revenue,
        active_sessions=active_sessions,
        complaints=complaints,
        refund_requests=refund_requests,
        pricing=pricing,
        payout_report=payout_report,
        chat_logs=chat_logs,
        files=files,
        feedback_client_map=feedback_client_map,
        sessions_completed_count=sessions_completed_count,
        sessions_cancelled_count=sessions_cancelled_count,
        sessions_booked_count=sessions_booked_count,
        chat_sessions_count=chat_sessions_count,
        call_sessions_count=call_sessions_count,
        total_recharges_count=total_recharges_count
    )
    return templates.TemplateResponse(request, "admin.html", ctx)


# -------------------------------------------------------------
# USER MODERATION
# -------------------------------------------------------------

@router.post("/user/{user_id}/toggle-suspend")
def toggle_suspend_user(
    request: Request,
    user_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    u = session_db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_suspended = not u.is_suspended
    session_db.add(u)
    session_db.commit()
    
    action = "Suspend User" if u.is_suspended else "Reactivate User"
    log_audit(session_db, action, f"User {u.email} (ID {u.id}) is_suspended = {u.is_suspended}", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-users", status_code=303)


@router.post("/user/{user_id}/delete")
def delete_user(
    request: Request,
    user_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    u = session_db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
        
    email = u.email
    # Delete related UserProfile
    prof = session_db.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
    if prof:
        session_db.delete(prof)
        
    # Delete related Astrologer profile if exists
    astro = session_db.exec(select(Astrologer).where(Astrologer.user_id == user_id)).first()
    if astro:
        session_db.delete(astro)
        
    session_db.delete(u)
    session_db.commit()
    
    log_audit(session_db, "Delete User", f"Deleted user email {email} (ID {user_id})", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-users", status_code=303)


@router.post("/user/{user_id}/edit-wallet")
def edit_user_wallet(
    request: Request,
    user_id: int,
    amount: int = Form(...),
    action_type: str = Form(...), # "add" or "set"
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    u = session_db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
        
    from app.account import get_or_create_profile
    prof = get_or_create_profile(session_db, u)
    old_balance = prof.wallet_balance
    
    if action_type == "add":
        prof.wallet_balance += amount
    else:
        prof.wallet_balance = amount
        
    session_db.add(prof)
    session_db.commit()
    
    log_audit(
        session_db, 
        "Adjust Wallet Balance", 
        f"User {u.email} wallet balance changed from {old_balance} to {prof.wallet_balance}", 
        admin.id, 
        request.client.host
    )
    return RedirectResponse(url="/admin#tab-users", status_code=303)


@router.post("/user/{user_id}/edit-profile")
def edit_user_profile(
    request: Request,
    user_id: int,
    full_name: str = Form(...),
    preferred_language: str = Form("English"),
    date_of_birth: str = Form(""),
    birth_time: str = Form(""),
    birth_place: str = Form(""),
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    u = session_db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
        
    from app.account import get_or_create_profile
    prof = get_or_create_profile(session_db, u)
    prof.full_name = full_name.strip()
    prof.preferred_language = preferred_language
    prof.birth_time = birth_time.strip()
    prof.birth_place = birth_place.strip()
    
    if date_of_birth.strip():
        from datetime import date
        prof.date_of_birth = date.fromisoformat(date_of_birth.strip())
        from app.services.horoscope import sun_sign_from_dob
        prof.zodiac_sign = sun_sign_from_dob(prof.date_of_birth)
        
    session_db.add(prof)
    session_db.commit()
    
    log_audit(session_db, "Edit Profile", f"Admin updated profile details for User {u.email}", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-users", status_code=303)


# -------------------------------------------------------------
# ASTROLOGER MANAGEMENT & VERIFICATION
# -------------------------------------------------------------

@router.post("/astrologer/{astrologer_id}/toggle-active")
def toggle_astrologer_active(
    request: Request,
    astrologer_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    astro = session_db.get(Astrologer, astrologer_id)
    if not astro:
        raise HTTPException(status_code=404, detail="Astrologer profile not found")
    astro.active_status = not astro.active_status
    session_db.add(astro)
    session_db.commit()
    
    action = "Activate Astrologer" if astro.active_status else "Pause Astrologer"
    log_audit(session_db, action, f"Astrologer {astro.display_name} active status = {astro.active_status}", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-astrologers", status_code=303)


@router.post("/astrologer/{astrologer_id}/toggle-verified")
def toggle_astrologer_verified(
    request: Request,
    astrologer_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    astro = session_db.get(Astrologer, astrologer_id)
    if not astro:
        raise HTTPException(status_code=404, detail="Astrologer profile not found")
    astro.verified_identity = not astro.verified_identity
    session_db.add(astro)
    session_db.commit()
    
    action = "Verify Astrologer" if astro.verified_identity else "Unverify Astrologer"
    log_audit(session_db, action, f"Astrologer {astro.display_name} verified status = {astro.verified_identity}", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-astrologers", status_code=303)


@router.post("/astrologer/{astrologer_id}/edit")
def edit_astrologer(
    request: Request,
    astrologer_id: int,
    display_name: str = Form(...),
    bio: str = Form(...),
    years_of_experience: int = Form(0),
    primary_language: str = Form("English"),
    min_budget: int = Form(0),
    max_budget: int = Form(9999),
    response_time_minutes: int = Form(30),
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    astro = session_db.get(Astrologer, astrologer_id)
    if not astro:
        raise HTTPException(status_code=404, detail="Astrologer not found")
        
    astro.display_name = display_name.strip()
    astro.bio = bio.strip()
    astro.years_of_experience = years_of_experience
    astro.primary_language = primary_language
    astro.min_budget = min_budget
    astro.max_budget = max_budget
    astro.response_time_minutes = response_time_minutes
    
    session_db.add(astro)
    session_db.commit()
    
    log_audit(session_db, "Edit Astrologer", f"Admin updated astrologer profile details for {astro.display_name}", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-astrologers", status_code=303)


# -------------------------------------------------------------
# ORDER & PAYMENT MANAGEMENT
# -------------------------------------------------------------

@router.post("/payment/{payment_id}/update-status")
def update_payment_status(
    request: Request,
    payment_id: int,
    status: PaymentStatus = Form(...),
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    p = session_db.get(Payment, payment_id)
    if not p:
        raise HTTPException(status_code=404, detail="Payment transaction not found")
        
    old_status = p.status
    p.status = status
    session_db.add(p)
    session_db.commit()
    
    # If payment was completed, add balance to the user
    if status == PaymentStatus.completed and old_status != PaymentStatus.completed:
        u = session_db.get(User, p.user_id)
        if u:
            from app.account import get_or_create_profile
            prof = get_or_create_profile(session_db, u)
            prof.wallet_balance += p.amount
            session_db.add(prof)
            session_db.commit()
            
    log_audit(session_db, "Update Order Status", f"Payment transaction #{p.id} status changed from {old_status} to {status}", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-orders", status_code=303)


@router.post("/payment/{payment_id}/delete")
def delete_payment(
    request: Request,
    payment_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    p = session_db.get(Payment, payment_id)
    if not p:
        raise HTTPException(status_code=404, detail="Payment not found")
        
    session_db.delete(p)
    session_db.commit()
    
    log_audit(session_db, "Delete Order", f"Deleted order record #{payment_id}", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-orders", status_code=303)


# -------------------------------------------------------------
# WEEKLY PAYOUT MANAGEMENT
# -------------------------------------------------------------

@router.post("/payout/process/{astrologer_id}")
def process_weekly_payout(
    request: Request,
    astrologer_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    astro = session_db.get(Astrologer, astrologer_id)
    if not astro:
        raise HTTPException(status_code=404, detail="Astrologer not found")
        
    # Mark all un-processed completed sessions for this astrologer as processed
    sessions = session_db.exec(
        select(ConsultationSession)
        .where(ConsultationSession.astrologer_id == astrologer_id)
        .where(ConsultationSession.status == SessionStatus.completed)
    ).all()
    
    payout_sessions = [s for s in sessions if not getattr(s, "payout_processed", False)]
    if not payout_sessions:
        return RedirectResponse(url="/admin#tab-payouts", status_code=303)
        
    commission_rate = float(get_config(session_db, "commission_rate", "0.20"))
    total_earned = sum(s.price for s in payout_sessions)
    net_payout = total_earned * (1.0 - commission_rate)
    
    for s in payout_sessions:
        s.payout_processed = True
        session_db.add(s)
    session_db.commit()
    
    log_audit(
        session_db, 
        "Process Payout", 
        f"Processed weekly payout for {astro.display_name}. Marked {len(payout_sessions)} sessions as paid. Net payout: {net_payout:.2f} (after {commission_rate*100:.0f}% commission)", 
        admin.id, 
        request.client.host
    )
    return RedirectResponse(url="/admin#tab-payouts", status_code=303)


# -------------------------------------------------------------
# REPORT MANAGEMENT
# -------------------------------------------------------------

@router.post("/reports/{report_type}/{report_id}/delete")
def delete_report(
    request: Request,
    report_type: str,
    report_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    if report_type == "saved":
        r = session_db.get(SavedReport, report_id)
    elif report_type == "kundli":
        r = session_db.get(KundliRecord, report_id)
    elif report_type == "match":
        r = session_db.get(KundliMatchRecord, report_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid report type")
        
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
        
    session_db.delete(r)
    session_db.commit()
    
    log_audit(session_db, "Delete Report", f"Deleted {report_type} report #{report_id}", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-reports", status_code=303)


# -------------------------------------------------------------
# BROADCAST & NOTIFICATIONS
# -------------------------------------------------------------

@router.post("/notifications/send")
def send_notification(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    target_type: str = Form(...), # "all", "clients", "astrologers", "specific"
    specific_email: str = Form(""),
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    
    if target_type == "all":
        notif = InAppNotification(title=title, body=body)
        session_db.add(notif)
    elif target_type == "clients":
        notif = InAppNotification(title=title, body=body, target_role=Role.user)
        session_db.add(notif)
    elif target_type == "astrologers":
        notif = InAppNotification(title=title, body=body, target_role=Role.astrologer)
        session_db.add(notif)
    elif target_type == "specific":
        target_user = session_db.exec(select(User).where(User.email == specific_email.strip().lower())).first()
        if not target_user:
            return RedirectResponse(url="/admin#tab-notifications", status_code=303)
        notif = InAppNotification(user_id=target_user.id, title=title, body=body)
        session_db.add(notif)
        
    session_db.commit()
    log_audit(session_db, "Send Notification", f"Dispatched {target_type} notification: '{title}'", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-notifications", status_code=303)


# -------------------------------------------------------------
# SUPPORT & COMPLAINTS
# -------------------------------------------------------------

@router.post("/support/{feedback_id}/resolve")
def resolve_complaint(
    request: Request,
    feedback_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    fb = session_db.get(Feedback, feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
        
    # Toggle off complaint flags as resolved
    fb.complaint_flag = False
    fb.refund_requested = False
    session_db.add(fb)
    session_db.commit()
    
    log_audit(session_db, "Resolve Complaint", f"Marked feedback/complaint #{feedback_id} as resolved", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-support", status_code=303)


@router.post("/support/{feedback_id}/refund")
def approve_refund(
    request: Request,
    feedback_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    fb = session_db.get(Feedback, feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
        
    sess = session_db.get(ConsultationSession, fb.session_id)
    if sess:
        client = session_db.get(User, sess.user_id)
        if client:
            from app.account import get_or_create_profile
            prof = get_or_create_profile(session_db, client)
            prof.wallet_balance += sess.price
            session_db.add(prof)
            
            # Cancel consultation price
            sess.price = 0
            sess.status = SessionStatus.cancelled
            session_db.add(sess)
            
    fb.refund_requested = False
    fb.complaint_flag = False
    session_db.add(fb)
    session_db.commit()
    
    log_audit(session_db, "Approve Refund", f"Refunded credit amount for session #{sess.id if sess else 0} (Feedback #{feedback_id})", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-support", status_code=303)


# -------------------------------------------------------------
# REVIEWS & FEEDBACK
# -------------------------------------------------------------

@router.post("/feedback/{feedback_id}/delete")
def delete_feedback(
    request: Request,
    feedback_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    fb = session_db.get(Feedback, feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
        
    session_db.delete(fb)
    session_db.commit()
    
    # Recalculate metrics
    from app.learning import recompute_astrologer_metrics
    recompute_astrologer_metrics()
    
    log_audit(session_db, "Delete Feedback", f"Removed user feedback entry #{feedback_id}", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-feedback", status_code=303)


# -------------------------------------------------------------
# PLATFORM SETTINGS & PRICING
# -------------------------------------------------------------

@router.post("/settings/save")
def save_platform_settings(
    request: Request,
    price_horoscope: str = Form(...),
    price_kundli: str = Form(...),
    price_match: str = Form(...),
    price_ask_ai: str = Form(...),
    recharge_option_1: str = Form(...),
    recharge_option_2: str = Form(...),
    recharge_option_3: str = Form(...),
    recharge_option_4: str = Form(...),
    commission_rate: str = Form(...),
    announcement_text: str = Form(...),
    maintenance_mode: str = Form("false"),
    support_email: str = Form(""),
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    
    set_config(session_db, "price_horoscope", price_horoscope.strip())
    set_config(session_db, "price_kundli", price_kundli.strip())
    set_config(session_db, "price_match", price_match.strip())
    set_config(session_db, "price_ask_ai", price_ask_ai.strip())
    set_config(session_db, "recharge_option_1", recharge_option_1.strip())
    set_config(session_db, "recharge_option_2", recharge_option_2.strip())
    set_config(session_db, "recharge_option_3", recharge_option_3.strip())
    set_config(session_db, "recharge_option_4", recharge_option_4.strip())
    
    try:
        pct = float(commission_rate.strip().replace("%", ""))
        set_config(session_db, "commission_rate", str(pct / 100.0))
    except ValueError:
        pass
        
    set_config(session_db, "announcement_text", announcement_text.strip())
    set_config(session_db, "maintenance_mode", maintenance_mode.strip())
    set_config(session_db, "support_email", support_email.strip())
    
    log_audit(session_db, "Update Settings", "Updated platform configurations and credit pricing models", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-settings", status_code=303)


# -------------------------------------------------------------
# SERVICE (SPECIALTIES) CRUD
# -------------------------------------------------------------

@router.post("/services/category/add")
def add_service_category(
    request: Request,
    slug: str = Form(...),
    name: str = Form(...),
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    slug = slug.strip().lower()
    name = name.strip()
    
    existing = session_db.exec(select(IssueCategory).where(IssueCategory.slug == slug)).first()
    if existing:
        return RedirectResponse(url="/admin#tab-services", status_code=303)
        
    cat = IssueCategory(slug=slug, name=name)
    session_db.add(cat)
    session_db.commit()
    
    log_audit(session_db, "Add Service Category", f"Added issue category slug '{slug}' ({name})", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-services", status_code=303)


@router.post("/services/category/{cat_id}/edit")
def edit_service_category(
    request: Request,
    cat_id: int,
    slug: str = Form(...),
    name: str = Form(...),
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    cat = session_db.get(IssueCategory, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Service category not found")
        
    old_slug = cat.slug
    cat.slug = slug.strip().lower()
    cat.name = name.strip()
    session_db.add(cat)
    session_db.commit()
    
    log_audit(session_db, "Edit Service Category", f"Updated issue category ID {cat_id} from '{old_slug}' to '{cat.slug}'", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-services", status_code=303)


@router.post("/services/category/{cat_id}/delete")
def delete_service_category(
    request: Request,
    cat_id: int,
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    cat = session_db.get(IssueCategory, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Service category not found")
        
    slug = cat.slug
    session_db.delete(cat)
    session_db.commit()
    
    log_audit(session_db, "Delete Service Category", f"Removed issue category '{slug}'", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-services", status_code=303)


# -------------------------------------------------------------
# FILE MANAGER
# -------------------------------------------------------------

@router.post("/files/upload")
async def upload_static_file(
    request: Request,
    file: UploadFile = File(...),
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    
    safe_filename = os.path.basename(file.filename)
    file_path = (UPLOADS_DIR / safe_filename).resolve()
    
    if not str(file_path).startswith(str(UPLOADS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path structure detected")
        
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    log_audit(session_db, "Upload File", f"Uploaded static file: '{safe_filename}'", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-files", status_code=303)


@router.post("/files/delete")
def delete_static_file(
    request: Request,
    filename: str = Form(...),
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    
    safe_filename = os.path.basename(filename)
    file_path = (UPLOADS_DIR / safe_filename).resolve()
    
    if not str(file_path).startswith(str(UPLOADS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path structure detected")
        
    if file_path.exists() and file_path.is_file():
        os.remove(file_path)
        log_audit(session_db, "Delete File", f"Deleted static file: '{safe_filename}'", admin.id, request.client.host)
        
    return RedirectResponse(url="/admin#tab-files", status_code=303)


# -------------------------------------------------------------
# WORKFLOW OPERATIONS & SYSTEM AUTOMATION
# -------------------------------------------------------------

@router.post("/workflow/trigger")
def trigger_workflow(
    request: Request,
    workflow_type: str = Form(...),
    session_db: Session = Depends(get_session)
):
    admin = require_admin(request, session_db)
    
    if workflow_type == "recompute_metrics":
        from app.learning import recompute_astrologer_metrics
        recompute_astrologer_metrics()
        msg = "Recalculated quality metrics (success rate, clarity, complaint rate) from feedback logs."
    elif workflow_type == "clear_slots":
        from app.models import AvailabilitySlot
        yesterday = datetime.utcnow() - timedelta(days=1)
        stale_slots = session_db.exec(
            select(AvailabilitySlot).where(AvailabilitySlot.start_at < yesterday).where(AvailabilitySlot.is_booked == False)
        ).all()
        cnt = len(stale_slots)
        for slot in stale_slots:
            session_db.delete(slot)
        session_db.commit()
        msg = f"Cleaned up {cnt} expired, unbooked availability slots older than 24 hours."
    elif workflow_type == "simulate_horoscope":
        users = session_db.exec(select(User).where(User.role == Role.user)).all()
        for u in users:
            notif = InAppNotification(
                user_id=u.id,
                title="✨ Your Daily Jyotish Forecast",
                body="Your custom transit chart matches auspicious stars today! Check details on the Horoscope Hub page."
            )
            session_db.add(notif)
        session_db.commit()
        msg = f"Simulated sending daily horoscope push alerts to all {len(users)} client users."
    elif workflow_type == "seed_db":
        from app.seed import run_seed
        run_seed()
        msg = "Executed database re-seed script (Issue categories, astrologers availability slots resets)."
    else:
        raise HTTPException(status_code=400, detail="Invalid workflow type")
        
    log_audit(session_db, "Trigger Workflow", f"Triggered workflow '{workflow_type}': {msg}", admin.id, request.client.host)
    return RedirectResponse(url="/admin#tab-workflow", status_code=303)
