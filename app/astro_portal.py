from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.auth import set_session, verify_password
from app.db import get_session
from app.deps import current_user, require_user
from app.models import Astrologer, ChatMessage, ChatSender, ConsultationSession, Payment, PaymentStatus, Role, User, ChildAstroOrder, SavedReport, InAppNotification, ReportType
from app.routes._shared import templates
from app.ui_helpers import page_context

router = APIRouter(prefix="/astro", tags=["astrologer"])


def _require_astrologer_user(request: Request, session: Session) -> User:
    u = require_user(request, session)
    if u.role != Role.astrologer:
        raise HTTPException(status_code=403, detail="Astrologer only")
    return u


@router.get("/login", response_class=HTMLResponse)
def astro_login_page(request: Request, session: Session = Depends(get_session), next: str = "/astro"):
    user = current_user(request, session)
    return templates.TemplateResponse(
        request, "astro_login.html", {"user": user, "error": None, "next": next}
    )


@router.post("/login")
def astro_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/astro"),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == email.strip().lower())).first()
    if not user or user.role != Role.astrologer or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "astro_login.html",
            {"user": None, "error": "Invalid astrologer credentials", "next": next},
            status_code=400,
        )
    if getattr(user, "is_suspended", False):
        return templates.TemplateResponse(
            request,
            "astro_login.html",
            {"user": None, "error": "Your astrologer account has been suspended by an administrator.", "next": next},
            status_code=400,
        )
    resp = RedirectResponse(url=next if next.startswith("/") else "/astro", status_code=303)
    set_session(resp, user.id)
    return resp


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def astro_dashboard(request: Request, session_db: Session = Depends(get_session)):
    user = _require_astrologer_user(request, session_db)
    astro = session_db.exec(select(Astrologer).where(Astrologer.user_id == user.id)).first()
    if not astro:
        raise HTTPException(status_code=404, detail="Astrologer profile not found")
        
    # Query all sessions for this astrologer
    sessions = session_db.exec(
        select(ConsultationSession)
        .where(ConsultationSession.astrologer_id == astro.id)
        .order_by(ConsultationSession.created_at.desc())
    ).all()
    
    # Calculate statistics
    total_clients_set = {s.user_id for s in sessions}
    total_clients = len(total_clients_set)
    total_earnings = sum(s.price for s in sessions if (s.status.value == "completed" or s.status == "completed"))
    active_sessions_count = len([s for s in sessions if (s.status.value == "booked" or s.status == "booked")])
    
    # Roster of unique clients with details
    from app.models import Intake, User, UserProfile
    clients = []
    for client_id in total_clients_set:
        c_user = session_db.get(User, client_id)
        if not c_user:
            continue
        c_prof = session_db.exec(select(UserProfile).where(UserProfile.user_id == client_id)).first()
        
        # Find latest session and intake for this client
        latest_sess = next((s for s in sessions if s.user_id == client_id), None)
        latest_intake = session_db.get(Intake, latest_sess.intake_id) if latest_sess else None
        
        c_sessions = [s for s in sessions if s.user_id == client_id]
        c_sessions_count = len(c_sessions)
        
        # Counts for pending/ongoing and completed
        pending_count = len([s for s in c_sessions if (s.status.value == "booked" or s.status == "booked")])
        completed_count = len([s for s in c_sessions if (s.status.value == "completed" or s.status == "completed")])
        
        # Total credits spent by the client to this astrologer
        total_credits_spent = sum(s.price for s in c_sessions)
        
        clients.append({
            "id": client_id,
            "email": c_user.email,
            "name": latest_intake.full_name if (latest_intake and latest_intake.full_name) else (c_prof.full_name if c_prof else "Client"),
            "dob": latest_intake.date_of_birth if latest_intake else (c_prof.date_of_birth if c_prof else None),
            "birth_place": latest_intake.birth_place if latest_intake else (c_prof.birth_place if c_prof else ""),
            "preferred_system": latest_intake.preferred_system if latest_intake else "Moon-Based Jyotish",
            "sessions_count": c_sessions_count,
            "pending_count": pending_count,
            "completed_count": completed_count,
            "total_credits_spent": total_credits_spent,
            "wallet_balance": c_prof.wallet_balance if c_prof else 0,
            "latest_problem": latest_intake.problem if latest_intake else "",
        })
        
    intakes_map = {s.intake_id: session_db.get(Intake, s.intake_id) for s in sessions}
    users_map = {s.user_id: session_db.get(User, s.user_id) for s in sessions}
    child_orders = session_db.exec(
        select(ChildAstroOrder).order_by(ChildAstroOrder.created_at.desc())
    ).all()
    
    saved_reports = session_db.exec(
        select(SavedReport).where(SavedReport.report_type == ReportType.child_astro)
    ).all()
    reports_map = {r.ref_id: r.id for r in saved_reports if r.ref_id}
    
    return templates.TemplateResponse(
        request,
        "astro_dashboard.html",
        page_context(
            session_db, user, 
            astro=astro, 
            sessions=sessions[:50],  # Keep display limited to 50 recent bookings
            intakes_map=intakes_map, 
            users_map=users_map,
            total_clients=total_clients,
            total_earnings=total_earnings,
            active_sessions_count=active_sessions_count,
            clients=clients,
            child_orders=child_orders,
            reports_map=reports_map
        ),
    )


@router.get("/chat/{session_id}", response_class=HTMLResponse)
def astro_chat(request: Request, session_id: int, session_db: Session = Depends(get_session)):
    user = _require_astrologer_user(request, session_db)
    astro = session_db.exec(select(Astrologer).where(Astrologer.user_id == user.id)).first()
    if not astro:
        raise HTTPException(status_code=404, detail="Astrologer profile not found")
    sess = session_db.get(ConsultationSession, session_id)
    if not sess or sess.astrologer_id != astro.id:
        raise HTTPException(status_code=404, detail="Session not found")

    payment = session_db.exec(select(Payment).where(Payment.session_id == sess.id)).first()
    paid = (payment is None) or (payment.status == PaymentStatus.completed)

    messages = session_db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == sess.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    ).all()
    
    from app.models import Intake
    intake = session_db.get(Intake, sess.intake_id)
    
    # Calculate custom birth chart for client details display
    from app.services.kundli import build_kundli
    from datetime import time
    chart = None
    if intake and intake.date_of_birth and intake.birth_time:
        try:
            parts = intake.birth_time.split(":")
            t = time(int(parts[0]), int(parts[1]))
            chart = build_kundli(
                intake.full_name or "Client",
                intake.date_of_birth,
                t,
                intake.birth_place or "New Delhi"
            )
        except Exception as e:
            import logging
            logging.error(f"Failed to generate client chart for astrologer view: {e}")
            
    return templates.TemplateResponse(
        request,
        "astro_chat.html",
        page_context(
            session_db, user, 
            astro=astro, 
            sess=sess, 
            messages=messages, 
            paid=paid, 
            intake=intake,
            chart=chart
        ),
    )


@router.post("/chat/{session_id}/send")
def astro_send_chat(
    request: Request,
    session_id: int,
    body: str = Form(...),
    session_db: Session = Depends(get_session),
):
    user = _require_astrologer_user(request, session_db)
    astro = session_db.exec(select(Astrologer).where(Astrologer.user_id == user.id)).first()
    if not astro:
        raise HTTPException(status_code=404, detail="Astrologer profile not found")
    sess = session_db.get(ConsultationSession, session_id)
    if not sess or sess.astrologer_id != astro.id:
        raise HTTPException(status_code=404, detail="Session not found")

    text = (body or "").strip()
    if text:
        session_db.add(
            ChatMessage(
                session_id=sess.id,
                sender=ChatSender.astrologer,
                sender_user_id=user.id,
                body=text,
            )
        )
        session_db.commit()
    return RedirectResponse(url=f"/astro/chat/{sess.id}", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
def astro_profile_page(request: Request, session_db: Session = Depends(get_session)):
    user = _require_astrologer_user(request, session_db)
    astro = session_db.exec(select(Astrologer).where(Astrologer.user_id == user.id)).first()
    if not astro:
        raise HTTPException(status_code=404, detail="Astrologer profile not found")
        
    from app.models import AstrologerLanguage, AstrologerSpecialty, IssueCategory
    langs = [l.language for l in session_db.exec(select(AstrologerLanguage).where(AstrologerLanguage.astrologer_id == astro.id)).all()]
    
    specialties = session_db.exec(
        select(IssueCategory)
        .join(AstrologerSpecialty, AstrologerSpecialty.issue_category_id == IssueCategory.id)
        .where(AstrologerSpecialty.astrologer_id == astro.id)
    ).all()
    specialty_ids = {spec.id for spec in specialties}
    
    all_categories = session_db.exec(select(IssueCategory)).all()
    
    return templates.TemplateResponse(
        request,
        "astro_profile.html",
        page_context(
            session_db, user,
            astro=astro,
            langs=", ".join(langs),
            specialty_ids=specialty_ids,
            all_categories=all_categories
        )
    )


@router.post("/profile")
def astro_profile_save(
    request: Request,
    display_name: str = Form(...),
    bio: str = Form(""),
    years_of_experience: int = Form(...),
    primary_language: str = Form(...),
    min_budget: int = Form(...),
    languages: str = Form(""),
    specialty_ids: list[int] = Form([]),
    session_db: Session = Depends(get_session)
):
    user = _require_astrologer_user(request, session_db)
    astro = session_db.exec(select(Astrologer).where(Astrologer.user_id == user.id)).first()
    if not astro:
        raise HTTPException(status_code=404, detail="Astrologer profile not found")
        
    astro.display_name = display_name.strip()
    astro.bio = bio.strip()
    astro.years_of_experience = years_of_experience
    astro.primary_language = primary_language.strip()
    astro.min_budget = min_budget
    astro.max_budget = min_budget * 5
    session_db.add(astro)
    
    from app.models import AstrologerLanguage, AstrologerSpecialty
    # Clear old languages
    old_langs = session_db.exec(select(AstrologerLanguage).where(AstrologerLanguage.astrologer_id == astro.id)).all()
    for ol in old_langs:
        session_db.delete(ol)
            
    # Clear old specialties
    old_specs = session_db.exec(select(AstrologerSpecialty).where(AstrologerSpecialty.astrologer_id == astro.id)).all()
    for os in old_specs:
        session_db.delete(os)
        
    # Commit deletions to database first to clear the constraints
    session_db.commit()
    
    # Add new languages
    for l in languages.split(","):
        l_cleaned = l.strip()
        if l_cleaned:
            session_db.add(AstrologerLanguage(astrologer_id=astro.id, language=l_cleaned))
            
    # Add new specialties
    for cat_id in specialty_ids:
        session_db.add(AstrologerSpecialty(astrologer_id=astro.id, issue_category_id=cat_id))
        
    session_db.commit()
    return RedirectResponse(url="/astro/profile", status_code=303)


@router.post("/child-orders/{order_id}/complete")
def complete_child_order(
    request: Request,
    order_id: int,
    report_content: str = Form(...),
    pdf_file: UploadFile = File(None),
    session_db: Session = Depends(get_session)
):
    user = _require_astrologer_user(request, session_db)
    order = session_db.get(ChildAstroOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    import os
    import shutil
    from pathlib import Path
    from app.settings import settings

    if pdf_file and pdf_file.filename:
        uploads_dir = Path(settings.UPLOADS_DIR)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        safe_filename = f"child_report_{order.id}_{os.path.basename(pdf_file.filename)}"
        file_path = uploads_dir / safe_filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(pdf_file.file, buffer)
        
        order.pdf_path = f"/uploads/{safe_filename}"

    # Update order status
    order.status = "completed"
    session_db.add(order)
    
    # Update the SavedReport or create it if not found
    saved_report = session_db.exec(
        select(SavedReport)
        .where(SavedReport.ref_id == order.id)
    ).first()
    
    # Fallback to search by title/child_name if ref_id was not populated yet
    if not saved_report:
        saved_report = session_db.exec(
            select(SavedReport)
            .where(SavedReport.user_id == order.user_id)
            .where(SavedReport.report_type == ReportType.child_astro)
            .where(SavedReport.title.like(f"%{order.child_name}%"))
        ).first()
        
    pdf_download_html = ""
    if order.pdf_path:
        pdf_download_html = f"""
        <div style="margin-top: 24px; text-align: center;">
            <a href="{order.pdf_path}" target="_blank" class="as-btn as-btn-orange" style="display: inline-block; padding: 12px 24px; text-decoration: none; color: white; background: #f97316; border-radius: 6px; font-weight: bold; box-shadow: 0 4px 6px rgba(249, 115, 22, 0.2);">📥 Download Completed PDF Report</a>
        </div>
        """

    from datetime import datetime
    report_html = f"""
    <div style="font-family: sans-serif; padding: 24px; line-height: 1.7; max-width: 700px; margin: 0 auto; color: #1e293b;">
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); color: #ffffff; padding: 24px; border-radius: 12px; margin-bottom: 24px; text-align: center;">
            <h2 style="margin: 0; font-size: 24px; letter-spacing: 0.5px;">📜 Child Astro Report (Vedic Analysis)</h2>
            <p style="margin: 6px 0 0 0; opacity: 0.85; font-size: 14px;">Guaranteed Manual Review & Consultation Guidance</p>
        </div>
        
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 24px;">
            <h3 style="margin-top: 0; color: #0f172a; font-size: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">Child Information</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <tr><td style="padding: 6px 0; color: #64748b; width: 140px;">Child Name:</td><td style="font-weight: 600; color: #0f172a;">{order.child_name} ({order.child_gender.title()})</td></tr>
                <tr><td style="padding: 6px 0; color: #64748b;">Date of Birth:</td><td style="font-weight: 600; color: #0f172a;">{order.date_of_birth.strftime('%d %B %Y')}</td></tr>
                <tr><td style="padding: 6px 0; color: #64748b;">Time of Birth:</td><td style="font-weight: 600; color: #0f172a;">{order.birth_time}</td></tr>
                <tr><td style="padding: 6px 0; color: #64748b;">Place of Birth:</td><td style="font-weight: 600; color: #0f172a;">{order.birth_place}, {order.country_of_residence}</td></tr>
            </table>
        </div>

        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <h3 style="margin-top: 0; color: #0f172a; font-size: 18px; border-bottom: 2px solid var(--as-orange, #f97316); padding-bottom: 8px;">Vedic Astrologer Analysis</h3>
            <div style="font-size: 15px; color: #334155; white-space: pre-line;">
                {report_content}
            </div>
            {pdf_download_html}
        </div>

        <div style="text-align: center; margin-top: 30px; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 16px;">
            This report was manually analyzed and compiled by our Vedic Astrology expert team on {datetime.utcnow().strftime('%Y-%m-%d')}.
        </div>
    </div>
    """
    
    if saved_report:
        saved_report.html_content = report_html
        saved_report.ref_id = order.id
        session_db.add(saved_report)
    else:
        saved_report = SavedReport(
            user_id=order.user_id,
            report_type=ReportType.child_astro,
            title=f"Child Astro Report — {order.child_name}",
            html_content=report_html,
            ref_id=order.id
        )
        session_db.add(saved_report)
        
    session_db.add(
        InAppNotification(
            user_id=order.user_id,
            title="Child Astro Report Ready",
            body=f"Your child astrology report for {order.child_name} is complete and ready to view."
        )
    )
    
    session_db.commit()
    return RedirectResponse(url="/astro#tab-child-orders", status_code=303)


