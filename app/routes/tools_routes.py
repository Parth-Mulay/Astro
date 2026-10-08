from __future__ import annotations

import json
import random
from datetime import date, time, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.db import get_session, get_config
from app.deps import current_user, require_user
from app.settings import settings
from app.models import (
    KundliMatchRecord,
    KundliRecord,
    ReportType,
    SavedReport,
    Intake,
    ConsultType,
    IssueCategory,
    Urgency,
    ChildAstroOrder,
    InAppNotification,
    PanchangData,
    TempleOfTheWeek,
    PitruPakshaBooking,
)
from app.matching import recommend_astrologers
from app.routes._shared import templates

from app.services.horoscope import ZODIAC, get_horoscope, sun_sign_from_dob
from app.services.kundli import build_kundli, chart_to_json, AstrologyJsonEncoder
from app.services.kundli_match import match_score
from app.services.panchang import get_panchang, get_remedies
from app.services.reports import kundli_report_html, match_report_html

router = APIRouter(prefix="/tools", tags=["tools"])

TAROT_CARDS = [
    "The Star — hope and renewal",
    "The Sun — success and clarity",
    "The Moon — intuition; watch illusions",
    "The Lovers — choices in relationships",
    "Wheel of Fortune — change is coming",
    "Strength — patience wins",
    "The Hermit — reflection needed",
    "Justice — fair outcomes with honesty",
]


@router.get("/horoscope", response_class=HTMLResponse)
def horoscope_hub(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    return templates.TemplateResponse(
        request, "horoscope_hub.html", {"user": user, "signs": ZODIAC}
    )


@router.get("/horoscope/{period}", response_class=HTMLResponse)
def horoscope_read(
    request: Request,
    period: str,
    sign: str = "aries",
    session: Session = Depends(get_session),
):
    user = require_user(request, session)
    cost = int(get_config(session, "price_horoscope", "20"))
    from app.account import get_or_create_profile, deduct_wallet
    prof = get_or_create_profile(session, user)
    if prof.wallet_balance < cost:
        return templates.TemplateResponse(
            request,
            "wallet.html",
            {
                "user": user,
                "prof": prof,
                "message": f"Insufficient credit balance. You need {cost} Credits to view detailed Horoscope, but you only have {prof.wallet_balance} Credits.",
                "error": True
            }
        )
    deduct_wallet(session, user.id, cost)
    if period not in ("daily", "weekly", "monthly", "yearly"):
        period = "daily"
    data = get_horoscope(sign, period)
    return templates.TemplateResponse(
        request,
        "horoscope_read.html",
        {
            "user": user, 
            "data": data, 
            "signs": ZODIAC, 
            "period": period,
            "deduction": cost,
            "balance": prof.wallet_balance
        },
    )


@router.get("/sample-kundli", response_class=HTMLResponse)
def sample_kundli(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    cost = int(get_config(session, "price_kundli", "50"))
    from app.account import get_or_create_profile, deduct_wallet
    prof = get_or_create_profile(session, user)
    if prof.wallet_balance < cost:
        return templates.TemplateResponse(
            request,
            "wallet.html",
            {
                "user": user,
                "prof": prof,
                "message": f"Insufficient credit balance. You need {cost} Credits to view the basic sample Kundali, but you only have {prof.wallet_balance} Credits.",
                "error": True
            }
        )
    deduct_wallet(session, user.id, cost)
    d = date(1995, 5, 15)
    t = time(12, 0)
    chart = build_kundli("Sample Devadatta (Demo)", d, t, "New Delhi")
    return templates.TemplateResponse(
        request, "kundli_result.html", {
            "user": user, 
            "chart": chart, 
            "deduction": cost, 
            "balance": prof.wallet_balance
        }
    )


@router.get("/panchang", response_class=HTMLResponse)
def panchang_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    data = session.exec(select(PanchangData)).first()
    if not data:
        data = PanchangData()
        session.add(data)
        session.commit()
        session.refresh(data)
    return templates.TemplateResponse(
        request, "panchang.html", {"user": user, "data": data}
    )


@router.get("/remedies", response_class=HTMLResponse)
def remedies_page(request: Request, issue: str = "general", session: Session = Depends(get_session)):
    user = current_user(request, session)
    items = get_remedies(issue)
    return templates.TemplateResponse(
        request, "remedies.html", {"user": user, "items": items, "issue": issue}
    )


@router.get("/tarot", response_class=HTMLResponse)
def tarot_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    return templates.TemplateResponse(request, "tarot.html", {"user": user, "cards": None})


@router.post("/tarot")
def tarot_draw(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    cards = random.sample(TAROT_CARDS, 3)
    return templates.TemplateResponse(
        request, "tarot.html", {"user": user, "cards": cards}
    )


@router.get("/astrologers", response_class=HTMLResponse)
def browse_astrologers(request: Request, session: Session = Depends(get_session)):
    from app.ui_helpers import get_featured_astrologers

    user = current_user(request, session)
    astrologers = get_featured_astrologers(session, limit=50)
    return templates.TemplateResponse(
        request, "astrologers.html", {"user": user, "astrologers": astrologers}
    )


# --- AI Astrological Suggestion Bot ---

AI_RESPONSES = {
    "relationships": {
        "en": "In Vedic Astrology, relationships and marriage are governed by the 7th house (partnership), its lord, and Venus (the significator of love) or Jupiter (for women). If you face compatibility issues or delays, it could be due to Rahu/Ketu transit impacts or Mangal Dosha. Strengthening Venus by performing acts of charity on Fridays or offering prayers can reduce negative influences.",
        "hi": "वैदिक ज्योतिष में, संबंध और विवाह सातवें भाव (साझेदारी), उसके स्वामी और शुक्र (प्रेम का कारक) या बृहस्पति (महिलाओं के लिए) द्वारा शासित होते हैं। यदि आपको अनुकूलता की समस्या या देरी का सामना करना पड़ता है, तो यह राहु/केतु गोचर या मंगल दोष के कारण हो सकता है। शुक्रवार को दान करने या प्रार्थना करने से शुक्र को मजबूत करने से नकारात्मक प्रभाव कम हो सकते हैं।"
    },
    "career": {
        "en": "Career and professional success are ruled by the 10th house (Karma Bhava), its ruling planet, and Saturn (the natural significator of work). Sun represents leadership, and Mercury governs communications and analytical jobs. A strong placement of Mercury and Sun together forms Budhaditya Yoga, granting high intellect and success in government or business sectors.",
        "hi": "करियर और व्यावसायिक सफलता को दसवां भाव (कर्म भाव), उसके स्वामी ग्रह और शनि (कार्य का प्राकृतिक कारक) द्वारा नियंत्रित किया जाता है। सूर्य नेतृत्व का प्रतिनिधित्व करता है, और बुध संचार और विश्लेषणात्मक कार्यों का संचालन करता है। बुध और सूर्य का एक साथ मजबूत स्थान बुधादित्य योग बनाता है, जो उच्च बुद्धि और सरकारी या व्यावसायिक क्षेत्रों में सफलता प्रदान करता है।"
    },
    "finance": {
        "en": "Wealth and financial security are evaluated from the 2nd house (Accumulated wealth) and 11th house (Gains/Income). Jupiter is the prime planet of wealth (Dhana Karaka). Strong connections between the lords of the 2nd, 5th, 9th, and 11th houses produce powerful Dhana Yogas that indicate wealth, success, and success in investment portfolios.",
        "hi": "धन और वित्तीय सुरक्षा का मूल्यांकन दूसरे भाव (संचित धन) और ग्यारहवें भाव (लाभ/आय) से किया जाता है। बृहस्पति धन का प्रमुख ग्रह (धन कारक) है। दूसरे, पांचवें, नौवें और ग्यारहवें भाव के स्वामियों के बीच मजबूत संबंध शक्तिशाली धन योग उत्पन्न करते हैं जो धन, सफलता और निवेश में लाभ का संकेत देते हैं।"
    },
    "health": {
        "en": "Vitality is represented by the 1st house (Lagna/Ascendant) and the Sun, which governs physical health. The 6th house rules disease, disputes, and recovery. If your Lagna lord is well-placed and strong in Shadbala, it grants high immunity and quick recovery from physical ailments. Keeping a disciplined routine supports overall wellbeing.",
        "hi": "जीवन शक्ति का प्रतिनिधित्व पहले भाव (लग्न) और सूर्य द्वारा किया जाता है, जो शारीरिक स्वास्थ्य को नियंत्रित करता है। छठा भाव रोग, विवाद और ठीक होने की प्रक्रिया को नियंत्रित करता है। यदि लग्न स्वामी अच्छी स्थिति में है और षडबल में मजबूत है, तो लग्न स्वामी का मंत्र जाप करने से और सूर्य देव को जल चढ़ाने से शारीरिक आरोग्य की वृद्धि होती है।"
    },
    "family": {
        "en": "Home, land, family, and domestic peace are governed by the 4th house (Sukha Bhava). Mars rules real estate, lands, and property acquisitions, while Moon represents family bonds and mental peace. Purchasing a home is favorable when Mars is well-placed in transit and the 4th house lord is strong, preventing disputes and legal hurdles.",
        "hi": "घर, भूमि, परिवार और घरेलू शांति को चौथा भाव (सुख भाव) द्वारा नियंत्रित किया जाता है। मंगल अचल संपत्ति, भूमि और संपत्ति की खरीद को नियंत्रित करता है, जबकि चंद्रमा पारिवारिक संबंधों और मानसिक शांति का प्रतिनिधित्व करता है। नया घर या संपत्ति खरीदना तब सबसे शुभ होता है जब गोचर में मंगल 4वें भाव से संबंध बनाए या बलवान हो।"
    }
}

def classify_question(question: str) -> str:
    q = question.lower()
    if any(k in q for k in ["love", "relationship", "marriage", "spouse", "husband", "wife", "partner", "couple", "shaadi", "vivah", "preeti", "compatibility", "compatible", "girlfriend", "boyfriend", "प्यार", "प्रेम", "मोहब्बत", "शादी", "विवाह", "दाम्पत्य", "पति", "पत्नी", "जीवनसाथी", "साझेदार", "सम्बन्ध", "संबंध"]):
        return "relationships"
    if any(k in q for k in ["career", "job", "business", "work", "promotion", "office", "boss", "salary", "naukr", "vyapaar", "sarkari", "नौकरी", "काम", "धंधा", "व्यवसाय", "व्यापार", "पदोन्नति", "तरक्की", "प्रमोशन", "करियर"]):
        return "career"
    if any(k in q for k in ["money", "finance", "wealth", "debt", "loan", "investment", "rich", "poor", "loss", "profit", "dhan", "paisa", "धन", "पैसा", "रुपया", "दौलत", "वित्त", "कर्ज", "ऋण", "लाभ", "हानि", "फायदा", "नुकसान"]):
        return "finance"
    if any(k in q for k in ["health", "illness", "disease", "wellbeing", "pain", "medical", "doctor", "swasthya", "rog", "beemari", "स्वास्थ्य", "रोग", "बीमारी", "तबीयत", "इलाज", "डॉक्टर"]):
        return "health"
    if any(k in q for k in ["family", "parent", "father", "mother", "child", "son", "daughter", "home", "house", "building", "flat", "land", "property", "gharr", "makaal", "vidhi", "griha", "परिवार", "घर", "मकान", "फ्लैट", "संपत्ति", "जमीन", "भूमि"]):
        return "family"
    return "relationships"


@router.get("/ask-ai", response_class=HTMLResponse)
def ask_ai_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user and user.role.value == 'astrologer':
        return RedirectResponse(url="/astro", status_code=303)
        
    cost = int(get_config(session, "price_ask_ai", "25"))
    from app.account import get_or_create_profile
    prof = None
    if user:
        prof = get_or_create_profile(session, user)
        if prof.wallet_balance < cost:
            return templates.TemplateResponse(
                request,
                "wallet.html",
                {
                    "user": user,
                    "prof": prof,
                    "message": f"Insufficient credit balance. You need {cost} Credits to request a consultation, but you only have {prof.wallet_balance} Credits.",
                    "error": True
                }
            )
    return templates.TemplateResponse(request, "ask_ai.html", {"user": user, "prof": prof, "step": "form", "cost": cost, "intake": None})


@router.post("/ask-ai")
def submit_consultation(
    request: Request,
    full_name: str = Form(...),
    dob: str = Form(...),
    day_of_birth: str = Form(...),
    birth_time: str = Form(...),
    birth_place: str = Form(...),
    current_address: str = Form(...),
    current_location: str = Form(...),
    problem: str = Form(...),
    preferred_system: str = Form(...),
    session: Session = Depends(get_session)
):
    user = current_user(request, session)
    if user and user.role.value == 'astrologer':
        return RedirectResponse(url="/astro", status_code=303)
        
    cost = int(get_config(session, "price_ask_ai", "25"))
    from app.account import get_or_create_profile, deduct_wallet
    
    if user:
        prof = get_or_create_profile(session, user)
        if prof.wallet_balance < cost:
            return RedirectResponse(url="/account/wallet", status_code=303)
        deduct_wallet(session, user.id, cost)
        user_id = user.id
    else:
        user_id = None
        
    slug = classify_question(problem)
    category = session.exec(
        select(IssueCategory).where(IssueCategory.slug == slug)
    ).first()
    if not category:
        category = session.exec(select(IssueCategory)).first()
    if not category:
        category = IssueCategory(slug="relationships", name="Love & Relationships")
        session.add(category)
        session.commit()
        session.refresh(category)
        
    d = None
    if dob:
        try:
            d = date.fromisoformat(dob.strip())
        except Exception:
            try:
                from datetime import datetime as _dt
                d = _dt.strptime(dob.strip(), "%d-%m-%Y").date()
            except Exception:
                d = None
    
    intake = Intake(
        user_id=user_id,
        issue_category_id=category.id,
        sub_issue=problem[:200],
        language="English",
        budget_min=0,
        budget_max=1000,
        consult_type=ConsultType.chat,
        urgency=Urgency.normal,
        goal=f"Preferred System: {preferred_system}",
        full_name=full_name.strip(),
        date_of_birth=d,
        day_of_birth=day_of_birth.strip(),
        birth_time=birth_time.strip(),
        birth_place=birth_place.strip(),
        current_address=current_address.strip(),
        current_location=current_location.strip(),
        problem=problem.strip(),
        preferred_system=preferred_system.strip()
    )
    session.add(intake)
    session.commit()
    session.refresh(intake)
    return RedirectResponse(url=f"/tools/ask-ai/recommendations?intake_id={intake.id}", status_code=303)


@router.get("/ask-ai/recommendations", response_class=HTMLResponse)
def ask_ai_recommendations(
    request: Request,
    intake_id: int,
    session: Session = Depends(get_session)
):
    user = current_user(request, session)
    intake = session.get(Intake, intake_id)
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")
        
    if user and intake.user_id is None:
        intake.user_id = user.id
        session.add(intake)
        session.commit()
        session.refresh(intake)
        
    if intake.user_id is not None and (not user or intake.user_id != user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
        
    matches = recommend_astrologers(session, intake=intake, top_k=3)
    category = session.get(IssueCategory, intake.issue_category_id)
    
    from app.models import MatchScore
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
    
    from app.ui_helpers import get_specialty_names_for_astrologer
    match_specialties = {
        m.astrologer.id: get_specialty_names_for_astrologer(session, m.astrologer.id)
        for m in matches
    }
    return templates.TemplateResponse(
        request,
        "ask_ai.html",
        {
            "user": user,
            "intake": intake,
            "category": category,
            "matches": matches,
            "match_specialties": match_specialties,
            "step": "recommendations"
        }
    )


@router.get("/kundli", response_class=HTMLResponse)
def kundli_form(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    return templates.TemplateResponse(
        request, "kundli_form.html", {"user": user}
    )


@router.post("/kundli", response_class=HTMLResponse)
def generate_kundli(
    request: Request,
    name: str = Form(...),
    dob: str = Form(...),
    birth_time: str = Form(...),
    birth_place: str = Form(...),
    calculation_mode: str = Form("modern"),
    house_system: str = Form("whole_sign"),
    session: Session = Depends(get_session)
):
    user = require_user(request, session)
    cost = int(get_config(session, "price_kundli", "50"))
    from app.account import get_or_create_profile, deduct_wallet
    prof = get_or_create_profile(session, user)
    if prof.wallet_balance < cost:
        return templates.TemplateResponse(
            request,
            "wallet.html",
            {
                "user": user,
                "prof": prof,
                "message": f"Insufficient credit balance. You need {cost} Credits to generate a custom Kundali, but you only have {prof.wallet_balance} Credits.",
                "error": True
            }
        )
    
    # parse date and time
    d = date.fromisoformat(dob)
    parts = birth_time.split(":")
    t = time(int(parts[0]), int(parts[1]))
    
    # Calculate chart
    chart = build_kundli(name, d, t, birth_place, calculation_mode, house_system)
    
    # Deduct wallet
    deduct_wallet(session, user.id, cost)
    
    # Save KundliRecord
    record = KundliRecord(
        user_id=user.id,
        name=name,
        date_of_birth=d,
        birth_time=birth_time,
        birth_place=birth_place,
        chart_json=chart_to_json(chart)
    )
    session.add(record)
    
    # Also save to SavedReport so it appears under Saved Reports
    session.add(
        SavedReport(
            user_id=user.id,
            report_type=ReportType.kundli,
            title=f"Kundli — {name}",
            html_content=kundli_report_html(chart),
            ref_id=record.id
        )
    )
    session.commit()
    session.refresh(record)
    
    return templates.TemplateResponse(
        request, "kundli_result.html", {
            "user": user, 
            "chart": chart, 
            "deduction": cost, 
            "balance": prof.wallet_balance
        }
    )


@router.get("/match", response_class=HTMLResponse)
def match_form(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    return templates.TemplateResponse(
        request, "match_form.html", {"user": user}
    )


@router.post("/match", response_class=HTMLResponse)
def generate_match(
    request: Request,
    boy_name: str = Form(...),
    boy_dob: str = Form(...),
    boy_time: str = Form("12:00"),
    boy_place: str = Form(""),
    girl_name: str = Form(...),
    girl_dob: str = Form(...),
    girl_time: str = Form("12:00"),
    girl_place: str = Form(""),
    session: Session = Depends(get_session)
):
    user = require_user(request, session)
    cost = int(get_config(session, "price_match", "50"))
    from app.account import get_or_create_profile, deduct_wallet
    prof = get_or_create_profile(session, user)
    if prof.wallet_balance < cost:
        return templates.TemplateResponse(
            request,
            "wallet.html",
            {
                "user": user,
                "prof": prof,
                "message": f"Insufficient credit balance. You need {cost} Credits to perform Kundli Matching, but you only have {prof.wallet_balance} Credits.",
                "error": True
            }
        )
    
    # parse dates and times
    bd = date.fromisoformat(boy_dob)
    bt_parts = boy_time.split(":")
    bt = time(int(bt_parts[0]), int(bt_parts[1]))
    
    gd = date.fromisoformat(girl_dob)
    gt_parts = girl_time.split(":")
    gt = time(int(gt_parts[0]), int(gt_parts[1]))
    
    # Calculate match
    result = match_score(
        boy_name=boy_name,
        boy_dob=bd,
        boy_time=bt,
        boy_place=boy_place,
        girl_name=girl_name,
        girl_dob=gd,
        girl_time=gt,
        girl_place=girl_place
    )
    
    # Deduct wallet
    deduct_wallet(session, user.id, cost)
    
    # Save KundliMatchRecord
    record = KundliMatchRecord(
        user_id=user.id,
        boy_name=boy_name,
        girl_name=girl_name,
        score_percent=result["percent"],
        report_json=json.dumps(result, cls=AstrologyJsonEncoder, ensure_ascii=False)
    )
    session.add(record)
    
    # Save to SavedReport so it appears under Saved Reports
    session.add(
        SavedReport(
            user_id=user.id,
            report_type=ReportType.match,
            title=f"Match — {boy_name} & {girl_name}",
            html_content=match_report_html(result),
            ref_id=record.id
        )
    )
    session.commit()
    session.refresh(record)
    
    return templates.TemplateResponse(
        request, "match_result.html", {
            "user": user, 
            "result": result, 
            "rec": record,
            "deduction": cost, 
            "balance": prof.wallet_balance
        }
    )


@router.get("/child-astro-report", response_class=HTMLResponse)
def child_astro_report_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    prof = None
    orders = []
    if user:
        from app.account import get_or_create_profile
        prof = get_or_create_profile(session, user)
        orders = session.exec(
            select(ChildAstroOrder)
            .where(ChildAstroOrder.user_id == user.id)
            .order_by(ChildAstroOrder.created_at.desc())
        ).all()
    cost = int(get_config(session, "price_child_astro", "100"))
    return templates.TemplateResponse(
        request,
        "child_astro_report.html",
        {
            "user": user,
            "prof": prof,
            "orders": orders,
            "cost": cost,
        },
    )


@router.post("/child-astro-report", response_class=HTMLResponse)
def submit_child_astro_report(
    request: Request,
    child_name: str = Form(...),
    child_gender: str = Form("boy"),
    date_of_birth: str = Form(...),
    birth_time: str = Form(...),
    birth_place: str = Form(...),
    country_of_residence: str = Form(...),
    parent_name: str = Form(...),
    parent_email: str = Form(...),
    special_notes: str = Form(""),
    session: Session = Depends(get_session),
):
    user = require_user(request, session)
    cost = int(get_config(session, "price_child_astro", "100"))
    from app.account import get_or_create_profile, deduct_wallet
    prof = get_or_create_profile(session, user)
    
    if prof.wallet_balance < cost:
        return templates.TemplateResponse(
            request,
            "wallet.html",
            {
                "user": user,
                "prof": prof,
                "message": f"Insufficient credit balance. You need {cost} Credits for the Child Astro Report, but you only have {prof.wallet_balance} Credits.",
                "error": True
            }
        )
    
    try:
        dob = date.fromisoformat(date_of_birth)
    except Exception:
        dob = date.today()

    deduct_wallet(session, user.id, cost)
    
    order = ChildAstroOrder(
        user_id=user.id,
        child_name=child_name.strip(),
        child_gender=child_gender.strip(),
        date_of_birth=dob,
        birth_time=birth_time.strip(),
        birth_place=birth_place.strip(),
        country_of_residence=country_of_residence.strip(),
        parent_name=parent_name.strip(),
        parent_email=parent_email.strip(),
        special_notes=special_notes.strip(),
        price_credits=cost,
        status="pending"
    )
    session.add(order)
    session.flush()
    
    summary_html = f"""
    <div style="font-family: sans-serif; padding: 20px; line-height: 1.6; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; background: #ffffff;">
        <div style="background: linear-gradient(135deg, #1a2b4c 0%, #2d4373 100%); color: #ffffff; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 20px;">📜 Child Astro Report (NRI Special)</h2>
            <p style="margin: 4px 0 0 0; opacity: 0.9; font-size: 13px;">Manual Analysis Request Confirmed</p>
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tr><td style="padding: 8px 0; color: #64748b; width: 140px;">Child Name:</td><td style="font-weight: 600; color: #0f172a;">{child_name}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Gender:</td><td style="font-weight: 600; color: #0f172a;">{child_gender.title()}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Date of Birth:</td><td style="font-weight: 600; color: #0f172a;">{dob.strftime('%d %B %Y')}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Time of Birth:</td><td style="font-weight: 600; color: #0f172a;">{birth_time}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Place of Birth:</td><td style="font-weight: 600; color: #0f172a;">{birth_place}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Country:</td><td style="font-weight: 600; color: #0f172a;">{country_of_residence}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Parent Contact:</td><td style="font-weight: 600; color: #0f172a;">{parent_name} ({parent_email})</td></tr>
        </table>
        <div style="background: #fff8e1; border-left: 4px solid #ff9800; padding: 14px; margin-top: 20px; border-radius: 4px; color: #78350f; font-size: 13px;">
            ⏳ <strong>Manual Analysis in Progress:</strong> Our senior Vedic astrologer team is reviewing the unique birth charts.<br/>
            Your comprehensive multi-page PDF report will be delivered directly to <strong>{parent_email}</strong> within <strong>72 hours</strong>.
        </div>
    </div>
    """
    
    session.add(
        SavedReport(
            user_id=user.id,
            report_type=ReportType.child_astro,
            title=f"Child Astro Report — {child_name}",
            html_content=summary_html,
            ref_id=order.id,
        )
    )
    
    session.add(
        InAppNotification(
            user_id=user.id,
            title="Child Astro Report Request Placed",
            body=f"Your order for {child_name} has been received. Guaranteed digital delivery within 72 hours to {parent_email}."
        )
    )
    session.commit()
    
    orders = session.exec(
        select(ChildAstroOrder)
        .where(ChildAstroOrder.user_id == user.id)
        .order_by(ChildAstroOrder.created_at.desc())
    ).all()
    
    return templates.TemplateResponse(
        request,
        "child_astro_report.html",
        {
            "user": user,
            "prof": prof,
            "orders": orders,
            "cost": cost,
            "success_message": f"Order successfully placed for {child_name}! Our team of expert astrologers has started analyzing the birth charts. Digital delivery guaranteed within 72 hours to {parent_email}.",
            "latest_order": order
        }
    )


@router.get("/temple-of-the-week", response_class=HTMLResponse)
def temple_of_the_week_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    temple = session.exec(select(TempleOfTheWeek).where(TempleOfTheWeek.is_active == True)).first()
    if not temple:
        temple = TempleOfTheWeek(
            name="Konark Sun Temple",
            location="Odisha",
            description="The Konark Sun Temple is a 13th-century CE monument dedicated to the Sun God Surya. Built as a colossal chariot with twelve pairs of stone-carved wheels drawn by seven horses, the temple's structural alignment serves as a precise astronomical sundial. It harmonizes Vedic architecture with astrological cosmic transits.",
            image_url="/static/images/temple_of_the_week.jpg"
        )
    return templates.TemplateResponse(
        request,
        "temple_of_the_week.html",
        {
            "user": user,
            "temple": temple
        }
    )


@router.get("/pitru-paksha", response_class=HTMLResponse)
def pitru_paksha_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    prof = None
    bookings = []
    if user:
        from app.account import get_or_create_profile
        prof = get_or_create_profile(session, user)
        bookings = session.exec(
            select(PitruPakshaBooking)
            .where(PitruPakshaBooking.user_id == user.id)
            .order_by(PitruPakshaBooking.created_at.desc())
        ).all()
    
    min_date = (date.today() + timedelta(days=3)).isoformat()
    return templates.TemplateResponse(
        request,
        "pitru_paksha.html",
        {
            "user": user,
            "prof": prof,
            "bookings": bookings,
            "min_date": min_date,
        },
    )


@router.post("/pitru-paksha", response_class=HTMLResponse)
async def submit_pitru_paksha_booking(
    request: Request,
    session: Session = Depends(get_session)
):
    user = current_user(request, session)
    min_date = (date.today() + timedelta(days=3)).isoformat()
    
    if not user:
        return templates.TemplateResponse(
            request,
            "pitru_paksha.html",
            {
                "user": None,
                "prof": None,
                "bookings": [],
                "min_date": min_date,
                "error_message": "User Registration Required: All devotees must be registered and signed in before booking and making a payment."
            },
            status_code=401
        )
    
    from app.account import get_or_create_profile
    prof = get_or_create_profile(session, user)
    
    form_data = await request.form()
    karta_name = str(form_data.get("karta_name", "")).strip()
    gotram = str(form_data.get("gotram", "")).strip()
    tithi = str(form_data.get("tithi", "")).strip()
    calendar_date_str = str(form_data.get("calendar_date", "")).strip()
    location = str(form_data.get("location", "")).strip()
    contact_number = str(form_data.get("contact_number", "")).strip()
    email = str(form_data.get("email", "")).strip()
    dakshina_raw = form_data.get("dakshina_amount", 0)
    payment_screenshot = form_data.get("payment_screenshot")
    
    # Extract ancestors list
    ancestor_names = form_data.getlist("ancestor_name[]")
    ancestor_rels = form_data.getlist("ancestor_rel[]")
    
    ancestor_pairs = []
    for n, r in zip(ancestor_names, ancestor_rels):
        n_clean = str(n).strip()
        r_clean = str(r).strip()
        if n_clean:
            ancestor_pairs.append(f"{n_clean} ({r_clean})")
            
    pitru_details = ", ".join(ancestor_pairs) if ancestor_pairs else "All Family Ancestors (Sarva Pitru)"
    
    # Helper to re-fetch bookings on return
    def get_user_bookings():
        return session.exec(
            select(PitruPakshaBooking)
            .where(PitruPakshaBooking.user_id == user.id)
            .order_by(PitruPakshaBooking.created_at.desc())
        ).all()

    # Validate basic required fields
    if not karta_name or not gotram or not tithi or not contact_number or not email:
        return templates.TemplateResponse(
            request,
            "pitru_paksha.html",
            {
                "user": user,
                "prof": prof,
                "bookings": get_user_bookings(),
                "min_date": min_date,
                "error_message": "Please fill in all mandatory fields (Karta Name, Gotram, Tithi, Location, Contact, Email)."
            },
            status_code=400
        )

    # Optional Calendar Date parsing if provided
    cal_date = None
    if calendar_date_str:
        try:
            cal_date = date.fromisoformat(calendar_date_str)
            if cal_date < date.today() + timedelta(days=3):
                return templates.TemplateResponse(
                    request,
                    "pitru_paksha.html",
                    {
                        "user": user,
                        "prof": prof,
                        "bookings": get_user_bookings(),
                        "min_date": min_date,
                        "error_message": "Puja date must be at least 3 days in advance."
                    },
                    status_code=400
                )
        except ValueError:
            cal_date = None

    # Parse Dakshina (Base is ₹2500 *Excluding any extra Purohit Dakshina)
    try:
        dakshina_amount = max(0, int(dakshina_raw))
    except Exception:
        dakshina_amount = 0
        
    base_puja_amount = 2500
    total_amount = base_puja_amount + dakshina_amount

    # Validate Payment Screenshot (strictly JPG/JPEG)
    if not payment_screenshot or not hasattr(payment_screenshot, "filename") or not payment_screenshot.filename:
        return templates.TemplateResponse(
            request,
            "pitru_paksha.html",
            {
                "user": user,
                "prof": prof,
                "bookings": get_user_bookings(),
                "min_date": min_date,
                "error_message": "Payment screenshot is required. Please attach your UPI transaction screenshot."
            },
            status_code=400
        )

    filename = payment_screenshot.filename.lower()
    if not (filename.endswith(".jpg") or filename.endswith(".jpeg")):
        return templates.TemplateResponse(
            request,
            "pitru_paksha.html",
            {
                "user": user,
                "prof": prof,
                "bookings": get_user_bookings(),
                "min_date": min_date,
                "error_message": "Invalid file format: Only .JPG and .JPEG image files are permitted for payment screenshots."
            },
            status_code=400
        )

    screenshot_bytes = await payment_screenshot.read()
    if len(screenshot_bytes) > 5 * 1024 * 1024:
        return templates.TemplateResponse(
            request,
            "pitru_paksha.html",
            {
                "user": user,
                "prof": prof,
                "bookings": get_user_bookings(),
                "min_date": min_date,
                "error_message": "Uploaded screenshot file is too large (maximum allowed is 5MB)."
            },
            status_code=400
        )

    # Validate JPEG Magic Bytes (\xff\xd8\xff)
    if not screenshot_bytes.startswith(b"\xff\xd8\xff"):
        return templates.TemplateResponse(
            request,
            "pitru_paksha.html",
            {
                "user": user,
                "prof": prof,
                "bookings": get_user_bookings(),
                "min_date": min_date,
                "error_message": "Corrupted or invalid image file. Please upload a genuine JPG payment screenshot."
            },
            status_code=400
        )

    # Save file safely to uploads/pitru_paksha/
    upload_dir = Path(settings.UPLOADS_DIR) / "pitru_paksha"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = f"pp_{uuid4().hex}.jpg"
    dest_path = (upload_dir / safe_filename).resolve()

    if not str(dest_path).startswith(str(upload_dir.resolve())):
        return templates.TemplateResponse(
            request,
            "pitru_paksha.html",
            {
                "user": user,
                "prof": prof,
                "bookings": get_user_bookings(),
                "min_date": min_date,
                "error_message": "Security error occurred while saving file."
            },
            status_code=400
        )

    with open(dest_path, "wb") as f:
        f.write(screenshot_bytes)

    screenshot_url = f"/uploads/pitru_paksha/{safe_filename}"

    # Create Booking Record
    booking = PitruPakshaBooking(
        user_id=user.id,
        karta_name=karta_name,
        gotram=gotram,
        tithi=tithi,
        calendar_date=cal_date,
        location=location,
        pitru_details=pitru_details,
        contact_number=contact_number,
        email=email,
        dakshina_amount=dakshina_amount,
        base_puja_amount=base_puja_amount,
        total_amount=total_amount,
        screenshot_path=screenshot_url,
        payment_status="pending",
        booking_status="confirmed",
    )
    session.add(booking)
    session.flush()

    # Create InAppNotification
    date_info = f"on {cal_date.strftime('%d %B %Y')}" if cal_date else f"on {tithi}"
    session.add(
        InAppNotification(
            user_id=user.id,
            title=f"Pitru Paksha Booking Confirmed (#PP-{booking.id})",
            body=f"Sacred Tarpan & Shraddha booking received for {karta_name} (Gotram: {gotram}) at {location} {date_info}. Payment screenshot under verification."
        )
    )

    # Create SavedReport record for user dashboard
    summary_html = f"""
    <div style="font-family: sans-serif; padding: 20px; line-height: 1.6; max-width: 620px; margin: 0 auto; border: 1px solid #fed7aa; border-radius: 12px; background: #ffffff;">
        <div style="background: linear-gradient(135deg, #2b1103 0%, #4a2108 100%); color: #ffffff; padding: 16px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
            <h2 style="margin: 0; font-size: 20px; color: #ffd89b;">🪔 Pitru Paksha Ritual Booking Confirmation</h2>
            <p style="margin: 4px 0 0 0; opacity: 0.9; font-size: 13px;">Booking ID: #PP-{booking.id}</p>
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tr><td style="padding: 8px 0; color: #64748b; width: 160px;">Karta Name:</td><td style="font-weight: 600; color: #0f172a;">{karta_name}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Gotram:</td><td style="font-weight: 600; color: #0f172a;">{gotram}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Auspicious Tithi:</td><td style="font-weight: 600; color: #0f172a;">{tithi}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Holy Tirtha Location:</td><td style="font-weight: 600; color: #0284c7;">📍 {location}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Pitru (Ancestors):</td><td style="font-weight: 600; color: #0f172a;">{pitru_details}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Contact / WhatsApp:</td><td style="font-weight: 600; color: #0f172a;">{contact_number}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Email:</td><td style="font-weight: 600; color: #0f172a;">{email}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Dakshina Base:</td><td style="font-weight: 600; color: #0f172a;">₹{base_puja_amount}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Extra Purohit Dakshina:</td><td style="font-weight: 600; color: #0f172a;">₹{dakshina_amount}</td></tr>
            <tr><td style="padding: 8px 0; color: #64748b;">Total Paid:</td><td style="font-weight: 700; color: #ea580c; font-size: 16px;">₹{total_amount}</td></tr>
        </table>
        <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 14px; margin-top: 20px; border-radius: 4px; color: #14532d; font-size: 13px;">
            🙏 <strong>Sacred Ritual Coordination:</strong> Our assigned Tirtha Purohit will perform the complete Vedic Tarpan & Pinda Daan vidhi with your Sankalp on {tithi}. Video and ritual blessings will be shared to {contact_number}.
        </div>
    </div>
    """

    session.add(
        SavedReport(
            user_id=user.id,
            report_type=ReportType.pitru_paksha,
            title=f"Pitru Paksha Ritual — {karta_name} ({location})",
            html_content=summary_html,
            ref_id=booking.id,
        )
    )

    session.commit()

    return templates.TemplateResponse(
        request,
        "pitru_paksha.html",
        {
            "user": user,
            "prof": prof,
            "bookings": get_user_bookings(),
            "min_date": min_date,
            "success_message": f"Sacred Pitru Paksha booking (#PP-{booking.id}) successfully confirmed for {karta_name}! Payment proof uploaded. Our Tirtha Purohit team will coordinate with you at {contact_number}."
        }
    )



