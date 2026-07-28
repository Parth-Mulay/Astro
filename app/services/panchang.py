from __future__ import annotations
from datetime import date, time
from app.vedic_engine.services.astrology_service import calculate_professional_kundli

def get_panchang(city: str = "New Delhi", on: date | None = None, calc_mode: str = "modern") -> dict:
    """
    Get the dynamically calculated astronomical Panchang for a given city and date.
    Maintains backward compatibility with callers.
    """
    on = on or date.today()
    chart = calculate_professional_kundli(
        name="Daily Panchang",
        dob=on,
        birth_time=time(6, 0),
        place=city,
        calc_mode=calc_mode,
        house_system="whole_sign"
    )
    return chart["panchang"]

def get_remedies(issue: str) -> list[dict]:
    base = [
        {"title": "Lal Kitab", "text": "Offer water to the Sun at sunrise; avoid lending on Tuesdays."},
        {"title": "Mantra", "text": "Chant Om Namah Shivaya 108 times on Mondays."},
        {"title": "Charity", "text": "Donate food grains on Thursdays for Jupiter strength."},
        {"title": "Gemstone", "text": "Consult a verified astrologer before wearing any stone."},
    ]
    if "love" in issue.lower() or "marriage" in issue.lower():
        base.insert(0, {"title": "Relationship", "text": "Light a ghee diya in the southwest corner on Fridays."})
    return base
