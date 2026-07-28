from __future__ import annotations

import json
import random
from datetime import date, time

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.db import get_session, get_config
from app.deps import current_user, require_user
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
def panchang_page(request: Request, city: str = "New Delhi", session: Session = Depends(get_session)):
    user = current_user(request, session)
    data = get_panchang(city)
    return templates.TemplateResponse(
        request, "panchang.html", {"user": user, "data": data, "city": city}
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
    user = require_user(request, session)
    if user.role.value == 'astrologer':
        return RedirectResponse(url="/astro", status_code=303)
        
    cost = int(get_config(session, "price_ask_ai", "25"))
    from app.account import get_or_create_profile
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
    return templates.TemplateResponse(request, "ask_ai.html", {"user": user, "prof": prof, "step": "form", "cost": cost})


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
    user = require_user(request, session)
    if user.role.value == 'astrologer':
        return RedirectResponse(url="/astro", status_code=303)
        
    cost = int(get_config(session, "price_ask_ai", "25"))
    from app.account import get_or_create_profile, deduct_wallet
    prof = get_or_create_profile(session, user)
    if prof.wallet_balance < cost:
        return RedirectResponse(url="/account/wallet", status_code=303)
        
    slug = classify_question(problem)
    category = session.exec(
        select(IssueCategory).where(IssueCategory.slug == slug)
    ).first()
    if not category:
        category = session.exec(select(IssueCategory)).first()
        
    d = date.fromisoformat(dob) if dob else None
    
    # Deduct wallet for Ask Me AI matchmaking form
    deduct_wallet(session, user.id, cost)
    
    intake = Intake(
        user_id=user.id,
        issue_category_id=category.id if category else 1,
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
    user = require_user(request, session)
    intake = session.get(Intake, intake_id)
    if not intake or intake.user_id != user.id:
        raise HTTPException(status_code=404, detail="Intake not found")
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


