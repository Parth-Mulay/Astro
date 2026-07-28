from __future__ import annotations

import hashlib
from datetime import date, time

from app.services.kundli import build_kundli


def match_score(
    boy_name: str,
    boy_dob: date,
    boy_time: time,
    boy_place: str,
    girl_name: str,
    girl_dob: date,
    girl_time: time,
    girl_place: str,
) -> dict:
    boy = build_kundli(boy_name, boy_dob, boy_time, boy_place)
    girl = build_kundli(girl_name, girl_dob, girl_time, girl_place)

    raw = f"{boy['moon_sign']}:{girl['moon_sign']}:{boy['nakshatra']}:{girl['nakshatra']}"
    h = int(hashlib.sha256(raw.encode()).hexdigest(), 16)
    gunas = 18 + (h % 19)  # 18-36 scale like Ashtakoot inspiration
    percent = round(gunas / 36 * 100, 1)

    verdict = "Excellent" if percent >= 75 else "Good" if percent >= 60 else "Average" if percent >= 45 else "Challenging"
    return {
        "boy": boy,
        "girl": girl,
        "gunas": gunas,
        "max_gunas": 36,
        "percent": percent,
        "verdict": verdict,
        "mangal_dosha": (h % 3 == 0),
        "nadi": ["Adi", "Madhya", "Antya"][h % 3],
        "bhakoot": "Compatible" if percent >= 55 else "Needs remedies",
        "summary": f"Match score {percent}% ({verdict}). Moon signs {boy['moon_sign']} & {girl['moon_sign']}.",
    }
