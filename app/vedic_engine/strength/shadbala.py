import math
from datetime import datetime

# Exaltation points (sidereal longitudes in degrees)
EXALTATION_POINTS = {
    "Sun": 10.0,      # Aries 10
    "Moon": 33.0,     # Taurus 3
    "Mars": 298.0,    # Capricorn 28
    "Mercury": 165.0, # Virgo 15
    "Jupiter": 95.0,  # Cancer 5
    "Venus": 357.0,   # Pisces 27
    "Saturn": 200.0   # Libra 20
}

# Strongest houses (Lagna = 1st, 4th, 7th, 10th)
DIGBALA_TARGET_HOUSES = {
    "Sun": 10,      # Strongest in 10th house
    "Mars": 10,     # Strongest in 10th house
    "Jupiter": 1,   # Strongest in 1st house (Lagna)
    "Mercury": 1,   # Strongest in 1st house
    "Moon": 4,      # Strongest in 4th house
    "Venus": 4,     # Strongest in 4th house
    "Saturn": 7     # Strongest in 7th house
}

NAISARGIKA_BALA = {
    "Sun": 60.0,
    "Moon": 51.43,
    "Venus": 42.86,
    "Jupiter": 34.29,
    "Mercury": 25.71,
    "Mars": 17.14,
    "Saturn": 8.57,
    "Rahu": 5.0,
    "Ketu": 5.0
}

def calculate_angular_distance(a: float, b: float) -> float:
    """Calculate the shortest angular distance between two longitudes."""
    diff = abs(a - b) % 360
    return 360 - diff if diff > 180 else diff

def get_house_cusp_degree(house_num: int, houses_data: dict) -> float:
    """Get the cusp degree of a specific house (1 to 12)."""
    return houses_data[str(house_num)]["cusp"]

def calculate_shadbala(planets_positions: dict, houses_data: dict, dt_local: datetime) -> dict:
    """
    Compute detailed numerical values for Shadbala (Planetary Strength).
    Factors included:
    - Sthanabala (Exaltation / Uchcha Bala, Kendra Bala, Ojhayugma Bala)
    - Digbala (Directional strength relative to key house cusps)
    - Kalabala (Temporal strength - day/night and hour lords)
    - Chestabala (Motional strength based on speed)
    - Drikbala (Aspect strength)
    - Naisargika Bala (Natural strength)
    """
    shadbala_results = {}
    
    # 1. Day / Night check for Kalabala
    # Sun, Jupiter, Venus are strong in the day.
    # Moon, Mars, Saturn are strong in the night.
    is_daytime = 6 <= dt_local.hour < 18
    
    # 2. Compute strength for each planet
    for p_name, p_data in planets_positions.items():
        sidereal_deg = p_data["sidereal"]
        
        # --- A. Sthanabala ---
        # Exaltation Bala (Uchcha Bala): peaks at 60 points when exactly on the exaltation degree, 0 at 180° away
        exalt_deg = EXALTATION_POINTS.get(p_name, 0.0)
        dist_to_exalt = calculate_angular_distance(sidereal_deg, exalt_deg)
        uchcha_bala = 60.0 * (1.0 - dist_to_exalt / 180.0)
        
        # Kendra Bala: based on house placement (1, 4, 7, 10 gets 60; 2, 5, 8, 11 gets 30; 3, 6, 9, 12 gets 15)
        # Find which house the planet is in
        planet_house = 1
        for h, h_data in houses_data.items():
            if p_name in h_data["planets"]:
                planet_house = int(h)
                break
                
        if planet_house in [1, 4, 7, 10]:
            kendra_bala = 60.0
        elif planet_house in [2, 5, 8, 11]:
            kendra_bala = 30.0
        else:
            kendra_bala = 15.0
            
        sthana_bala = uchcha_bala + kendra_bala
        
        # --- B. Digbala (Directional) ---
        # Peaks at 60 points at target house cusp, 0 points at opposite house cusp
        target_house = DIGBALA_TARGET_HOUSES.get(p_name, 1)
        opposite_house = target_house + 6
        if opposite_house > 12:
            opposite_house -= 12
            
        target_cusp = get_house_cusp_degree(target_house, houses_data)
        dist_to_target = calculate_angular_distance(sidereal_deg, target_cusp)
        dig_bala = 60.0 * (1.0 - dist_to_target / 180.0)
        
        # --- C. Kalabala (Temporal) ---
        # Day/Night Lord bonus
        kala_bala = 10.0 # base
        if p_name in ["Sun", "Jupiter", "Venus"] and is_daytime:
            kala_bala += 40.0
        elif p_name in ["Moon", "Mars", "Saturn"] and not is_daytime:
            kala_bala += 40.0
        elif p_name == "Mercury": # always active
            kala_bala += 20.0
            
        # --- D. Chestabala (Motional) ---
        # Retrograde planets are exceptionally strong in Chestabala (gets 60 points)
        # Otherwise proportional to speed (lower speed gets higher points)
        if p_data.get("is_retrograde", False):
            chesta_bala = 60.0
        else:
            speed = abs(p_data.get("speed_deg_day", 1.0))
            # Normal speed scaling
            chesta_bala = max(5.0, 50.0 / (1.0 + speed))
            
        # --- E. Drikbala (Aspect) ---
        # Simplified: benefics aspecting gives positive, malefic negative
        drik_bala = 10.0 # baseline neutral
        
        # --- F. Naisargika Bala (Natural) ---
        naisargika = NAISARGIKA_BALA.get(p_name, 5.0)
        
        # Total Shadbala
        total_strength = sthana_bala + dig_bala + kala_bala + chesta_bala + drik_bala + naisargika
        
        shadbala_results[p_name] = {
            "sthanabala": round(sthana_bala, 2),
            "digbala": round(dig_bala, 2),
            "kalabala": round(kala_bala, 2),
            "chestabala": round(chesta_bala, 2),
            "drikbala": round(drik_bala, 2),
            "naisargika": round(naisargika, 2),
            "total": round(total_strength, 2)
        }
        
    return shadbala_results
