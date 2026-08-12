from __future__ import annotations

from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import secrets
import time
from typing import Optional
from collections import defaultdict

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from app.account import deduct_wallet, get_or_create_profile
from app.db import create_db_and_tables, get_session
from app.deps import current_user, require_user
from app.learning import recompute_astrologer_metrics
from app.matching import recommend_astrologers
from app.models import (
    Astrologer,
    ChatMessage,
    ChatSender,
    ConsultationSession,
    Feedback,
    Intake,
    IssueCategory,
    MatchScore,
    Payment,
    PaymentStatus,
    Role,
    ReportType,
    SavedReport,
    SessionStatus,
    User,
)
from app.routes import account_routes, admin_routes, auth_routes, tools_routes, payment_routes
from app.routes._shared import templates
from app.services.reports import session_report_html
from app.ui_helpers import get_featured_astrologers, get_specialty_names_for_astrologer, page_context
from app.astro_portal import router as astro_router
from app.settings import settings

# --- LOGGING INITIALIZATION ---
def setup_logging():
    logs_dir = Path(settings.LOGS_DIR)
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Application handler
    app_handler = RotatingFileHandler(
        logs_dir / "application.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding="utf-8"
    )
    app_handler.setLevel(logging.INFO if settings.LOG_LEVEL == "INFO" else logging.DEBUG)
    app_handler.setFormatter(formatter)
    
    # Error handler
    error_handler = RotatingFileHandler(
        logs_dir / "error.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Access handler
    access_handler = RotatingFileHandler(
        logs_dir / "access.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding="utf-8"
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
    
    # Setup loggers
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)
    
    app_logger = logging.getLogger("application")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(app_handler)
    app_logger.addHandler(error_handler)
    
    access_logger = logging.getLogger("access")
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(access_handler)
    access_logger.propagate = False

setup_logging()
logger = logging.getLogger("application")
access_logger = logging.getLogger("access")

ROOT = Path(__file__).resolve().parent

# Ensure runtime directories exist
Path(settings.UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.REPORTS_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="AstroMatch – Astrology Platform",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc"
)

# --- CSRF Pure ASGI Middleware ---
from starlette.datastructures import MutableHeaders

class CSRFASGIMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path
        is_safe_method = request.method in ["GET", "HEAD", "OPTIONS"]
        is_excluded = (
            path in ["/health", "/status", "/version"]
            or path.startswith("/static")
            or path.startswith("/uploads")
            or path.startswith("/payment/razorpay/webhook")
        )

        cookie_token = request.cookies.get("csrf_token")
        generated_token = None
        if not cookie_token:
            generated_token = secrets.token_urlsafe(32)
            cookie_token = generated_token

        request.state.csrf_token = cookie_token

        if not is_safe_method and not is_excluded:
            submitted_token = request.headers.get("X-CSRF-Token")
            
            if not submitted_token:
                content_type = request.headers.get("content-type", "")
                if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                    body_chunks = []
                    body_bytes = b""
                    while True:
                        message = await receive()
                        body_chunks.append(message)
                        if message["type"] == "http.request":
                            body_bytes += message.get("body", b"")
                            if not message.get("more_body", False):
                                break
                        elif message["type"] == "http.disconnect":
                            break
                    
                    import urllib.parse
                    parsed_form = urllib.parse.parse_qs(body_bytes.decode("utf-8", errors="ignore"))
                    csrf_list = parsed_form.get("csrf_token")
                    if csrf_list:
                        submitted_token = csrf_list[0]
                    else:
                        match = re.search(rb'name="csrf_token"\r\n\r\n([A-Za-z0-9_-]+)', body_bytes)
                        if match:
                            submitted_token = match.group(1).decode("utf-8", errors="ignore")
                    
                    async def cached_receive():
                        if body_chunks:
                            return body_chunks.pop(0)
                        return {"type": "http.request", "body": b"", "more_body": False}
                    
                    receive = cached_receive
            
            stored_cookie_token = request.cookies.get("csrf_token")
            if not stored_cookie_token or not submitted_token or not secrets.compare_digest(stored_cookie_token, submitted_token):
                logger.warning(f"CSRF validation failed for IP: {request.client.host if request.client else 'unknown'} on path {path}")
                
                accept_header = request.headers.get("accept", "")
                if "text/html" in accept_header:
                    response = HTMLResponse(
                        status_code=403,
                        content="""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>CSRF Verification Failed</title>
                            <style>
                                body { background: #0f172a; color: #f8fafc; font-family: sans-serif; text-align: center; padding: 50px; }
                                h1 { color: #ef4444; }
                                p { color: #94a3b8; }
                            </style>
                        </head>
                        <body>
                            <h1>🔒 CSRF Verification Failed</h1>
                            <p>Security verification failed. Please refresh the page and try again.</p>
                        </body>
                        </html>
                        """
                    )
                    await response(scope, receive, send)
                    return
                else:
                    response = JSONResponse(status_code=403, content={"detail": "CSRF token validation failed"})
                    await response(scope, receive, send)
                    return

        if generated_token:
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(raw=message["headers"])
                    cookie_val = f"csrf_token={generated_token}; HttpOnly; Path=/; SameSite=lax"
                    if settings.SECURE_COOKIES:
                        cookie_val += "; Secure"
                    headers.append("set-cookie", cookie_val)
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)

# Gzip Compression Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CSRFASGIMiddleware)

class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=31536000, must-revalidate"
        return response

# Static and Dynamic Uploads/Reports Mounting
app.mount("/static", CachedStaticFiles(directory=ROOT / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=Path(settings.UPLOADS_DIR)), name="uploads")
app.mount("/reports", StaticFiles(directory=Path(settings.REPORTS_DIR)), name="reports")

# Include Routers
app.include_router(auth_routes.router)
app.include_router(tools_routes.router)
app.include_router(account_routes.router)
app.include_router(admin_routes.router)
app.include_router(astro_router)
app.include_router(payment_routes.router)

# --- MIDDLEWARES ---

# 1. Access Logging Middleware
@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    if request.url.query:
        path += f"?{request.url.query}"
    
    access_logger.info(
        f'{client_ip} - "{method} {path} HTTP/1.1" {response.status_code} - {process_time:.2f}ms'
    )
    return response

# 2. Rate Limiting Middleware
rate_limit_records = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in ["/health", "/status", "/version"] or path.startswith("/static") or path.startswith("/uploads"):
        return await call_next(request)
        
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Filter within 60 second window
    rate_limit_records[client_ip] = [t for t in rate_limit_records[client_ip] if now - t < 60]
    
    if len(rate_limit_records[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
        logger.warning(f"Rate limit exceeded for IP: {client_ip} on path {path}")
        if "text/html" in request.headers.get("accept", ""):
            return HTMLResponse(
                status_code=429,
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Too Many Requests</title>
                    <style>
                        body { background: #0f172a; color: #f8fafc; font-family: sans-serif; text-align: center; padding: 50px; }
                        h1 { color: #f97316; }
                        p { color: #94a3b8; }
                    </style>
                </head>
                <body>
                    <h1>⏳ Too Many Requests</h1>
                    <p>You have made too many requests in a short period. Please wait a minute and try again.</p>
                </body>
                </html>
                """
            )
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again later."})
        
    rate_limit_records[client_ip].append(now)
    return await call_next(request)



# 4. Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    if settings.SECURE_COOKIES:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://checkout.razorpay.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://*.razorpay.com; "
        "frame-src 'self' https://api.razorpay.com https://checkout.razorpay.com; "
        "connect-src 'self' https://api.razorpay.com;"
    )
    return response

# --- ERROR HANDLERS ---
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(request, "errors/404.html", {"request": request}, status_code=404)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})

@app.exception_handler(403)
async def custom_403_handler(request: Request, exc):
    if "text/html" in request.headers.get("accept", ""):
        detail = str(exc.detail) if hasattr(exc, "detail") else "Access Denied"
        return templates.TemplateResponse(request, "errors/403.html", {"request": request, "detail": detail}, status_code=403)
    return JSONResponse(status_code=403, content={"detail": "Forbidden"})

@app.exception_handler(500)
async def custom_500_handler(request: Request, exc):
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(request, "errors/500.html", {"request": request}, status_code=500)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

@app.exception_handler(503)
async def custom_503_handler(request: Request, exc):
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(request, "errors/503.html", {"request": request}, status_code=503)
    return JSONResponse(status_code=503, content={"detail": "Service Unavailable"})

# --- HEALTH ENDPOINTS ---
@app.get("/health")
def health_check(session: Session = Depends(get_session)):
    try:
        from sqlmodel import text
        session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_ok = False
        logger.error(f"Database health check failed: {e}")
        
    if not db_ok:
        raise HTTPException(status_code=500, detail="Database connection down")
        
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/status")
def status_endpoint(session: Session = Depends(get_session)):
    import sys
    import os
    
    ephemeris_ok = False
    try:
        if os.path.exists("de421.bsp"):
            ephemeris_ok = True
    except Exception:
        pass
        
    return {
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "python_version": sys.version,
        "database": "sqlite (connected)",
        "ephemeris_loaded": ephemeris_ok,
        "pid": os.getpid()
    }

@app.get("/version")
def version_endpoint():
    return {"version": "1.0.0"}


@app.middleware("http")
async def redirect_astrologers_from_client_pages(request: Request, call_next):
    path = request.url.path
    if path == "/" or path.startswith("/tools") or path.startswith("/services") or path.startswith("/flow"):
        from app.auth import get_user_id_from_request
        user_id = get_user_id_from_request(request)
        if user_id:
            from app.db import engine
            from sqlmodel import Session
            from app.models import User
            with Session(engine) as session_db:
                user = session_db.get(User, user_id)
                if user and user.role.value == 'astrologer':
                    return RedirectResponse(url="/astro", status_code=303)
                    
    response = await call_next(request)
    return response


@app.on_event("startup")
def _startup():
    create_db_and_tables()
    try:
        from app.ephemeris import eph, ts
    except Exception as e:
        import logging
        logging.error(f"Failed to pre-load Skyfield ephemeris: {e}")



@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401 and "text/html" in request.headers.get("accept", ""):
        import urllib.parse
        dest = request.url.path
        if request.url.query:
            dest += f"?{request.url.query}"
        return RedirectResponse(url=f"/auth/login?next={urllib.parse.quote(dest)}", status_code=303)
    if exc.status_code == 403 and "text/html" in request.headers.get("accept", ""):
        from app.auth import get_user_id_from_request
        user_id = get_user_id_from_request(request)
        if user_id:
            from app.db import engine
            from sqlmodel import Session
            from app.models import User
            with Session(engine) as session_db:
                user = session_db.get(User, user_id)
                if user and user.role.value == 'admin' and request.url.path.startswith('/astro'):
                    return RedirectResponse(url="/admin", status_code=303)
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Access Restricted – AstroMatch</title>
                <link rel="stylesheet" href="/static/css/theme.css" />
                <style>
                    body {{ display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #0f172a; color: #f8fafc; font-family: system-ui, sans-serif; text-align: center; margin: 0; padding: 1rem; }}
                    .card {{ background: #1e293b; padding: 2.5rem 2rem; border-radius: 16px; max-width: 480px; width: 100%; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }}
                    h1 {{ font-size: 1.5rem; margin-bottom: 0.75rem; color: #f97316; }}
                    p {{ color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.75rem; line-height: 1.5; }}
                    .btn-group {{ display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }}
                    a {{ display: inline-block; padding: 10px 18px; background: var(--as-orange, #f97316); color: white; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.9rem; transition: background 0.2s; }}
                    a:hover {{ background: #ea580c; }}
                    a.secondary {{ background: #334155; color: #e2e8f0; }}
                    a.secondary:hover {{ background: #475569; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>🔒 Access Restricted</h1>
                    <p>{exc.detail}. If you are looking for the Admin Dashboard or standard user view, click below.</p>
                    <div class="btn-group">
                        <a href="/admin">Admin Dashboard</a>
                        <a href="/" class="secondary">Home</a>
                        <a href="/auth/login" class="secondary">Log In</a>
                    </div>
                </div>
            </body>
            </html>
            """,
            status_code=403,
        )
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


SHLOKAS = [
    {
        "title": "🕉️ Gayatri Mantra (Wisdom & Enlightenment)",
        "text": "ॐ भूर्भुवः स्वः।\nतत्सवितुर्वरेण्यं।\nभर्गो देवस्य धीमहि।\nधियो यो नः प्रचोदयात्॥"
    },
    {
        "title": "🔱 Mahamrityunjaya Mantra (Health & Protection)",
        "text": "ॐ त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम्।\nउर्वारुकमिव बन्धनान्मृत्योर्मुक्षीय मामृतात्॥"
    },
    {
        "title": "🪔 Bhagavad Gita – Karma Yoga",
        "text": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।\nमा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥"
    },
    {
        "title": "🌍 Universal Peace Prayer",
        "text": "सर्वे भवन्तु सुखिनः।\nसर्वे सन्तु निरामयाः।\nसर्वे भद्राणि पश्यन्तु।\nमा कश्चिद्दुःखभाग्भवेत्॥"
    },
    {
        "title": "📿 Guru Stotram",
        "text": "गुरुर्ब्रह्मा गुरुर्विष्णुः गुरुर्देवो महेश्वरः।\nगुरुः साक्षात् परं ब्रह्म तस्मै श्रीगुरवे नमः॥"
    },
    {
        "title": "🪷 Ganesh Vandana",
        "text": "वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ।\nनिर्विघ्नं कुरु मे देव सर्वकार्येषु सर्वदा॥"
    },
    {
        "title": "🌅 Shanti Mantra",
        "text": "असतो मा सद्गमय।\nतमसो मा ज्योतिर्गमय।\nमृत्योर्माऽमृतं गमय॥"
    },
    {
        "title": "🚩 Hanuman Prayer",
        "text": "मनोजवं मारुततुल्यवेगं\nजितेन्द्रियं बुद्धिमतां वरिष्ठम्।\nवातात्मजं वानरयूथमुख्यं\nश्रीरामदूतं शरणं प्रपद्ये॥"
    },
    {
        "title": "💙 Krishna Vandana",
        "text": "कृष्णाय वासुदेवाय हरये परमात्मने।\nप्रणतक्लेशनाशाय गोविन्दाय नमो नमः॥"
    },
    {
        "title": "🌸 Vishnu Shanti Stotram",
        "text": "शान्ताकारं भुजगशयनं पद्मनाभं सुरेशम्।\nविश्वाधारं गगनसदृशं मेघवर्णं शुभाङ्गम्।\nलक्ष्मीकान्तं कमलनयनं योगिभिर्ध्यानगम्यम्।\nवन्दे विष्णुं भवभयहरं सर्वलोकैकनाथम्॥"
    }
]

@app.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    from datetime import date, time
    from app.services.kundli import build_kundli
    from app.models import PanchangData

    user = current_user(request, session)
    today = date.today()
    transit_chart = build_kundli("Gochar Chart", today, time(12, 0), "New Delhi")
    
    panchang_data = session.exec(select(PanchangData)).first()
    if not panchang_data:
        panchang_data = PanchangData()
        session.add(panchang_data)
        session.commit()
        session.refresh(panchang_data)
        
    current_datetime = datetime.now().strftime("%A, %d %B %Y — %I:%M %p")
    
    # Calculate daily shloka based on ordinal date to repeat every 10 days
    shloka_index = today.toordinal() % len(SHLOKAS)
    daily_shloka = SHLOKAS[shloka_index]

    ctx = page_context(
        session,
        user,
        featured=get_featured_astrologers(session),
        categories=session.exec(select(IssueCategory).order_by(IssueCategory.name.asc())).all(),
        transit_chart=transit_chart,
        panchang_data=panchang_data,
        daily_shloka=daily_shloka,
        current_datetime=current_datetime,
    )
    return templates.TemplateResponse(request, "home.html", ctx)


@app.get("/services", response_class=HTMLResponse)
def services_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    return templates.TemplateResponse(request, "services.html", page_context(session, user))


@app.get("/flow/problem", response_class=HTMLResponse)
def problem_selection(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    categories = session.exec(select(IssueCategory).order_by(IssueCategory.name.asc())).all()
    return templates.TemplateResponse(
        request, "problem.html", page_context(session, user, categories=categories)
    )


@app.get("/flow/intake", response_class=HTMLResponse)
def intake_page(request: Request, issue: int, session: Session = Depends(get_session)):
    user = require_user(request, session)
    category = session.get(IssueCategory, issue)
    if not category:
        raise HTTPException(status_code=404, detail="Issue category not found")
    return templates.TemplateResponse(
        request, "intake.html", page_context(session, user, category=category)
    )


@app.post("/flow/intake")
def submit_intake(
    request: Request,
    issue_category_id: int = Form(...),
    sub_issue: str = Form(""),
    language: str = Form("English"),
    budget_min: int = Form(0),
    budget_max: int = Form(0),
    consult_type: str = Form("chat"),
    urgency: str = Form("normal"),
    goal: str = Form(""),
    session: Session = Depends(get_session),
):
    user = require_user(request, session)
    intake = Intake(
        user_id=user.id,
        issue_category_id=issue_category_id,
        sub_issue=sub_issue.strip(),
        language=language.strip() or "English",
        budget_min=int(budget_min or 0),
        budget_max=int(budget_max or 0),
        consult_type=consult_type,
        urgency=urgency,
        goal=goal.strip(),
    )
    session.add(intake)
    session.commit()
    session.refresh(intake)
    return RedirectResponse(url=f"/flow/recommendations?intake_id={intake.id}", status_code=303)


@app.get("/flow/recommendations", response_class=HTMLResponse)
def recommendations_page(request: Request, intake_id: int, session: Session = Depends(get_session)):
    user = require_user(request, session)
    intake = session.get(Intake, intake_id)
    if not intake or intake.user_id != user.id:
        raise HTTPException(status_code=404, detail="Intake not found")
    matches = recommend_astrologers(session, intake=intake, top_k=3)
    category = session.get(IssueCategory, intake.issue_category_id)

    for m in matches:
        existing = session.exec(
            select(MatchScore)
            .where(MatchScore.intake_id == intake.id)
            .where(MatchScore.astrologer_id == m.astrologer.id)
        ).first()
        reason = "; ".join(m.reasons)
        if existing:
            existing.score = m.score
            existing.reason = reason
            session.add(existing)
        else:
            session.add(
                MatchScore(
                    intake_id=intake.id,
                    astrologer_id=m.astrologer.id,
                    score=m.score,
                    reason=reason,
                )
            )
    session.commit()

    match_specialties = {
        m.astrologer.id: get_specialty_names_for_astrologer(session, m.astrologer.id)
        for m in matches
    }
    return templates.TemplateResponse(
        request,
        "recommendations.html",
        page_context(
            session,
            user,
            intake=intake,
            category=category,
            matches=matches,
            match_specialties=match_specialties,
        ),
    )


@app.post("/flow/book")
def book(
    request: Request,
    intake_id: int = Form(...),
    astrologer_id: int = Form(...),
    session_db: Session = Depends(get_session),
):
    user = require_user(request, session_db)
    intake = session_db.get(Intake, intake_id)
    astrologer = session_db.get(Astrologer, astrologer_id)
    if not intake or intake.user_id != user.id or not astrologer:
        raise HTTPException(status_code=400, detail="Invalid booking request")

    price = max(astrologer.min_budget, intake.budget_min or 0) or astrologer.min_budget or 199
    scheduled_at = datetime.utcnow() + timedelta(hours=1)
    sess = ConsultationSession(
        user_id=user.id,
        astrologer_id=astrologer.id,
        intake_id=intake.id,
        consult_type=intake.consult_type,
        scheduled_at=scheduled_at,
        status=SessionStatus.booked,
        price=price,
    )
    session_db.add(sess)
    session_db.commit()
    session_db.refresh(sess)

    payment = Payment(user_id=user.id, session_id=sess.id, amount=price, status=PaymentStatus.pending)
    session_db.add(payment)
    session_db.commit()

    return RedirectResponse(url=f"/flow/pay/{sess.id}", status_code=303)


@app.get("/flow/pay/{session_id}", response_class=HTMLResponse)
def pay_page(request: Request, session_id: int, session_db: Session = Depends(get_session)):
    user = require_user(request, session_db)
    sess = session_db.get(ConsultationSession, session_id)
    if not sess or sess.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    astrologer = session_db.get(Astrologer, sess.astrologer_id)
    prof = get_or_create_profile(session_db, user)
    payment = session_db.exec(select(Payment).where(Payment.session_id == sess.id)).first()
    return templates.TemplateResponse(
        request,
        "payment.html",
        page_context(
            session_db,
            user,
            sess=sess,
            astrologer=astrologer,
            prof=prof,
            payment=payment,
            error=None,
        ),
    )


@app.post("/flow/pay/{session_id}")
def pay_confirm(request: Request, session_id: int, session_db: Session = Depends(get_session)):
    user = require_user(request, session_db)
    sess = session_db.get(ConsultationSession, session_id)
    if not sess or sess.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    astrologer = session_db.get(Astrologer, sess.astrologer_id)
    prof = get_or_create_profile(session_db, user)
    payment = session_db.exec(select(Payment).where(Payment.session_id == sess.id)).first()

    if payment and payment.status == PaymentStatus.completed:
        return RedirectResponse(url=f"/flow/chat/{sess.id}", status_code=303)

    if not deduct_wallet(session_db, user.id, sess.price):
        return templates.TemplateResponse(
            request,
            "payment.html",
            page_context(
                session_db,
                user,
                sess=sess,
                astrologer=astrologer,
                prof=prof,
                payment=payment,
                error=f"Insufficient Credit Points. Need {sess.price} Credits, you have {prof.wallet_balance} Credits.",
            ),
            status_code=400,
        )

    if payment:
        payment.status = PaymentStatus.completed
        session_db.add(payment)
    category = session_db.get(IssueCategory, session_db.get(Intake, sess.intake_id).issue_category_id)
    session_db.add(
        SavedReport(
            user_id=user.id,
            report_type=ReportType.session,
            title=f"Consultation — {astrologer.display_name}",
            html_content=session_report_html(
                sess.id, astrologer.display_name, sess.price, category.name if category else ""
            ),
            ref_id=sess.id,
        )
    )
    session_db.commit()
    return RedirectResponse(url=f"/flow/chat/{sess.id}", status_code=303)


@app.get("/flow/chat/{session_id}", response_class=HTMLResponse)
def chat_page(request: Request, session_id: int, session_db: Session = Depends(get_session)):
    user = require_user(request, session_db)
    sess = session_db.get(ConsultationSession, session_id)
    if not sess or sess.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    payment = session_db.exec(select(Payment).where(Payment.session_id == sess.id)).first()
    if payment and payment.status != PaymentStatus.completed:
        return RedirectResponse(url=f"/flow/pay/{sess.id}", status_code=303)
    astrologer = session_db.get(Astrologer, sess.astrologer_id)
    messages = session_db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == sess.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    ).all()
    return templates.TemplateResponse(
        request,
        "chat.html",
        page_context(session_db, user, sess=sess, astrologer=astrologer, messages=messages),
    )


@app.post("/flow/chat/{session_id}/send")
def user_send_chat(
    request: Request,
    session_id: int,
    body: str = Form(...),
    session_db: Session = Depends(get_session),
):
    user = require_user(request, session_db)
    sess = session_db.get(ConsultationSession, session_id)
    if not sess or sess.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    payment = session_db.exec(select(Payment).where(Payment.session_id == sess.id)).first()
    if payment and payment.status != PaymentStatus.completed:
        return RedirectResponse(url=f"/flow/pay/{sess.id}", status_code=303)
    text = (body or "").strip()
    if text:
        session_db.add(
            ChatMessage(
                session_id=sess.id,
                sender=ChatSender.user,
                sender_user_id=user.id,
                body=text,
            )
        )
        session_db.commit()
    return RedirectResponse(url=f"/flow/chat/{sess.id}", status_code=303)


@app.get("/flow/session/{session_id}", response_class=HTMLResponse)
def session_page(request: Request, session_id: int, session_db: Session = Depends(get_session)):
    user = require_user(request, session_db)
    sess = session_db.get(ConsultationSession, session_id)
    if not sess or sess.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    astrologer = session_db.get(Astrologer, sess.astrologer_id)
    feedback = session_db.exec(select(Feedback).where(Feedback.session_id == sess.id)).first()
    return templates.TemplateResponse(
        request,
        "session.html",
        page_context(session_db, user, sess=sess, astrologer=astrologer, feedback=feedback),
    )


@app.post("/flow/session/{session_id}/complete")
def complete_session(request: Request, session_id: int, session_db: Session = Depends(get_session)):
    user = require_user(request, session_db)
    sess = session_db.get(ConsultationSession, session_id)
    if not sess or sess.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    sess.status = SessionStatus.completed
    session_db.add(sess)
    session_db.commit()
    return RedirectResponse(url=f"/flow/session/{session_id}", status_code=303)


@app.post("/flow/session/{session_id}/feedback")
def submit_feedback(
    request: Request,
    session_id: int,
    helpfulness_score: int = Form(...),
    clarity_score: int = Form(...),
    relevance_score: int = Form(...),
    refund_requested: Optional[str] = Form(None),
    complaint_flag: Optional[str] = Form(None),
    repeat_booking_intent: Optional[str] = Form(None),
    notes: str = Form(""),
    session_db: Session = Depends(get_session),
):
    user = require_user(request, session_db)
    sess = session_db.get(ConsultationSession, session_id)
    if not sess or sess.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    existing = session_db.exec(select(Feedback).where(Feedback.session_id == sess.id)).first()
    fb = existing or Feedback(session_id=sess.id)
    fb.helpfulness_score = int(helpfulness_score)
    fb.clarity_score = int(clarity_score)
    fb.relevance_score = int(relevance_score)
    fb.refund_requested = refund_requested is not None
    fb.complaint_flag = complaint_flag is not None
    fb.repeat_booking_intent = repeat_booking_intent is not None
    fb.notes = notes.strip()
    session_db.add(fb)
    session_db.commit()
    recompute_astrologer_metrics()
    return RedirectResponse(url=f"/flow/session/{session_id}", status_code=303)


@app.get("/sitemap.xml")
def sitemap():
    from fastapi import Response
    base = "https://astro-6eq0.onrender.com"
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{base}/services</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>{base}/tools/horoscope</loc>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>{base}/tools/sample-kundli</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>{base}/tools/panchang</loc>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>{base}/tools/ask-ai</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>{base}/tools/tarot</loc>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>{base}/tools/remedies</loc>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>{base}/tools/astrologers</loc>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>{base}/tools/temple-of-the-week</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
"""
    return Response(content=xml_content, media_type="application/xml")


@app.get("/robots.txt")
def robots():
    from fastapi import Response
    content = """User-agent: *
Disallow: /auth/
Disallow: /account/
Disallow: /admin/
Disallow: /flow/
Disallow: /payment/
Disallow: /astro/

Sitemap: https://astro-6eq0.onrender.com/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")
