from __future__ import annotations

import json
from datetime import date, time
from app.vedic_engine.services.astrology_service import calculate_professional_kundli

def build_kundli(
    name: str, 
    dob: date, 
    birth_time: time, 
    place: str, 
    calc_mode: str = "modern", 
    house_system: str = "whole_sign"
) -> dict:
    """
    Calculates a professional Vedic Astrology Kundli chart.
    Maintains backward compatibility with all outer routes.
    """
    return calculate_professional_kundli(
        name=name,
        dob=dob,
        birth_time=birth_time,
        place=place,
        calc_mode=calc_mode,
        house_system=house_system
    )

class AstrologyJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "tolist") and callable(obj.tolist):
            return obj.tolist()
        if hasattr(obj, "item") and callable(obj.item):
            return obj.item()
        from datetime import date, time, datetime
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        return super().default(obj)

def chart_to_json(chart: dict) -> str:
    return json.dumps(chart, cls=AstrologyJsonEncoder, ensure_ascii=False)
