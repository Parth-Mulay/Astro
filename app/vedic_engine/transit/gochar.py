from datetime import datetime
from app.vedic_engine.astronomy.coords import get_planetary_positions

RASHIS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

def calculate_angular_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 360
    return 360 - diff if diff > 180 else diff

def get_transit_aspects(transit_positions: dict, natal_positions: dict) -> list:
    """
    Find aspects from transit planets to natal planets.
    Vedic Aspects:
    - 7th aspect for all planets (100% strength within 6 degrees orb).
    - Mars special aspects: 4th, 8th.
    - Jupiter special aspects: 5th, 9th.
    - Saturn special aspects: 3rd, 10th.
    """
    aspects = []
    
    # Standard Vedic aspect angles
    special_aspects_offset = {
        "Mars": [4, 8],
        "Jupiter": [5, 9],
        "Saturn": [3, 10]
    }
    
    for tp_name, tp_data in transit_positions["planets"].items():
        tp_sid = tp_data["sidereal"]
        tp_sign_idx = int(tp_sid // 30) % 12
        
        # Check against each natal planet
        for np_name, np_data in natal_positions["planets"].items():
            np_sid = np_data["sidereal"]
            np_sign_idx = int(np_sid // 30) % 12
            
            # 1. 7th Aspect (Opposition / same house count 7)
            # relative sign difference (1-indexed house count)
            house_diff = (np_sign_idx - tp_sign_idx) % 12 + 1
            
            if house_diff == 7:
                aspects.append({
                    "from": tp_name,
                    "to": np_name,
                    "aspect_type": "7th Aspect",
                    "description": f"Transit {tp_name} aspects Natal {np_name} with standard 7th house aspect."
                })
                
            # 2. Special Aspects
            if tp_name in special_aspects_offset:
                offsets = special_aspects_offset[tp_name]
                if house_diff in offsets:
                    aspects.append({
                        "from": tp_name,
                        "to": np_name,
                        "aspect_type": f"Special {house_diff}th Aspect",
                        "description": f"Transit {tp_name} casts special {house_diff}th house aspect on Natal {np_name}."
                    })
                    
            # 3. Conjunction (same house / sign)
            if house_diff == 1:
                aspects.append({
                    "from": tp_name,
                    "to": np_name,
                    "aspect_type": "Conjunction",
                    "description": f"Transit {tp_name} is conjoined with Natal {np_name} in {RASHIS[tp_sign_idx]}."
                })
                
    return aspects

def calculate_gochar(natal_chart_positions: dict, lat: float, lon: float, calc_mode: str = "modern") -> dict:
    """
    Compare natal positions with current transit positions.
    Transit placements are calculated relative to the natal Moon and natal Lagna.
    """
    # 1. Get current UTC time for transit positions
    dt_now_utc = datetime.utcnow()
    transit_data = get_planetary_positions(dt_now_utc, lat, lon, calc_mode=calc_mode)
    
    # Extract natal Moon and Lagna sign indices
    natal_moon_sid = natal_chart_positions["planets"]["Moon"]["sidereal"]
    natal_moon_sign_idx = int(natal_moon_sid // 30) % 12
    natal_lagna_sid = natal_chart_positions["lagna"]
    natal_lagna_sign_idx = int(natal_lagna_sid // 30) % 12
    
    transit_details = {}
    
    # 2. Process each transit planet
    for p_name, p_data in transit_data["planets"].items():
        tp_sid = p_data["sidereal"]
        tp_sign_idx = int(tp_sid // 30) % 12
        
        # Calculate transit house relative to Moon (Gochar)
        moon_rel_house = (tp_sign_idx - natal_moon_sign_idx) % 12 + 1
        
        # Calculate transit house relative to Lagna
        lagna_rel_house = (tp_sign_idx - natal_lagna_sign_idx) % 12 + 1
        
        transit_details[p_name] = {
            "sidereal": tp_sid,
            "sign": RASHIS[tp_sign_idx],
            "house_relative_moon": moon_rel_house,
            "house_relative_lagna": lagna_rel_house,
            "is_retrograde": p_data["is_retrograde"]
        }
        
    # 3. Find aspects from transit to natal
    aspects = get_transit_aspects(transit_data, natal_chart_positions)
    
    return {
        "transit_time": dt_now_utc.isoformat(),
        "placements": transit_details,
        "aspects": aspects
    }
