from __future__ import annotations

import hashlib
from datetime import date, timedelta

ZODIAC = [
    ("aries", "Aries", "♈"),
    ("taurus", "Taurus", "♉"),
    ("gemini", "Gemini", "♊"),
    ("cancer", "Cancer", "♋"),
    ("leo", "Leo", "♌"),
    ("virgo", "Virgo", "♍"),
    ("libra", "Libra", "♎"),
    ("scorpio", "Scorpio", "♏"),
    ("sagittarius", "Sagittarius", "♐"),
    ("capricorn", "Capricorn", "♑"),
    ("aquarius", "Aquarius", "♒"),
    ("pisces", "Pisces", "♓"),
]

DAILY_THEMES = [
    "Focus on steady progress at work; avoid impulsive decisions before noon.",
    "Relationships improve when you listen more than you speak today.",
    "A financial opportunity may appear—verify details before committing.",
    "Health and routine matter; short walks and hydration help your energy.",
    "Creative ideas flow; share them with a trusted mentor or partner.",
    "Family matters need patience; small gestures build harmony.",
    "Travel or learning plans gain momentum; stay flexible with timing.",
    "Property or long-term investments favor research over speed today.",
]

WEEKLY_THEMES = [
    "Career visibility increases mid-week; prepare for important conversations.",
    "Love life stabilizes when you express needs clearly and kindly.",
    "Budget discipline pays off; unexpected expenses are manageable.",
    "Spiritual practice or meditation supports clarity on a major choice.",
]

MONTHLY_THEMES = [
    "This month favors structured goals in career and education.",
    "Emotional healing in relationships opens space for deeper trust.",
    "Financial planning and debt reduction bring long-term relief.",
    "Health routines started now can become sustainable habits.",
]

YEARLY_THEMES = [
    "A year of consolidation: build skills, savings, and supportive networks.",
    "Partnerships and collaborations define success—choose allies wisely.",
    "Relocation, study abroad, or new roles may appear in the second half.",
    "Remedies and disciplined spiritual practice amplify positive outcomes.",
]


def _seed(sign: str, period: str, anchor: date) -> int:
    raw = f"{sign}:{period}:{anchor.isoformat()}".encode()
    return int(hashlib.md5(raw).hexdigest(), 16)


def sun_sign_from_dob(dob: date) -> str:
    md = dob.month * 100 + dob.day
    if 321 <= md <= 419:
        return "aries"
    if 420 <= md <= 520:
        return "taurus"
    if 521 <= md <= 620:
        return "gemini"
    if 621 <= md <= 722:
        return "cancer"
    if 723 <= md <= 822:
        return "leo"
    if 823 <= md <= 922:
        return "virgo"
    if 923 <= md <= 1022:
        return "libra"
    if 1023 <= md <= 1121:
        return "scorpio"
    if 1122 <= md <= 1221:
        return "sagittarius"
    if md >= 1222 or md <= 119:
        return "capricorn"
    if 120 <= md <= 218:
        return "aquarius"
    return "pisces"


def get_horoscope(sign: str, period: str, on_date: date | None = None) -> dict:
    on_date = on_date or date.today()
    sign = sign.lower()
    z = next((z for z in ZODIAC if z[0] == sign), ZODIAC[0])

    if period == "daily":
        anchor = on_date
        pool = DAILY_THEMES
    elif period == "weekly":
        anchor = on_date - timedelta(days=on_date.weekday())
        pool = WEEKLY_THEMES
    elif period == "monthly":
        anchor = on_date.replace(day=1)
        pool = MONTHLY_THEMES
    else:
        anchor = on_date.replace(month=1, day=1)
        pool = YEARLY_THEMES

    idx = _seed(sign, period, anchor) % len(pool)
    luck = 60 + (_seed(sign, period + "luck", anchor) % 41)
    return {
        "sign_slug": z[0],
        "sign_name": z[1],
        "symbol": z[2],
        "period": period,
        "date_label": anchor.strftime("%d %b %Y"),
        "prediction": pool[idx],
        "luck_score": luck,
        "love": pool[(idx + 1) % len(pool)],
        "career": pool[(idx + 2) % len(pool)],
        "health": "Moderate energy—prioritize rest if stressed.",
    }
