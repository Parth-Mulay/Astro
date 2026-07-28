from datetime import datetime
import math
import logging
from skyfield.api import load
from skyfield.framelib import ecliptic_frame
from skyfield.nutationlib import fundamental_arguments
from app.vedic_engine.astronomy.ayanamsa import get_ayanamsa

# Cache Skyfield resources
eph = load('de421.bsp')
ts = load.timescale()
earth = eph['earth']

# Planetary mapping
PLANETS_MAP = {
    "Sun": eph['sun'],
    "Moon": eph['moon'],
    "Mars": eph['mars'],
    "Mercury": eph['mercury'],
    "Jupiter": eph['jupiter barycenter'],
    "Venus": eph['venus'],
    "Saturn": eph['saturn barycenter'],
}

def get_obliquity(T: float) -> float:
    """Calculate the obliquity of the ecliptic using the IAU 1980 formula."""
    return 23.4392911 - (46.8150 / 3600.0) * T - (0.00059 / 3600.0) * T**2 + (0.001813 / 3600.0) * T**3

def get_lst(t, lon_deg: float) -> float:
    """Calculate Local Sidereal Time in decimal hours."""
    return (t.gast + (lon_deg / 15.0)) % 24

def calculate_ascendant(lst_hours: float, lat_deg: float, obliquity_deg: float) -> float:
    """Calculate the Ascendant (Lagna) in degrees (apparent tropical)."""
    ramc = math.radians(lst_hours * 15.0)
    lat = math.radians(lat_deg)
    eps = math.radians(obliquity_deg)

    numerator = math.cos(ramc)
    denominator = -(math.sin(eps) * math.tan(lat) + math.cos(eps) * math.sin(ramc))

    asc_rad = math.atan2(numerator, denominator)
    return math.degrees(asc_rad) % 360

def calculate_mc(lst_hours: float, obliquity_deg: float) -> float:
    """Calculate the Midheaven (MC) in degrees (apparent tropical)."""
    ramc = math.radians(lst_hours * 15.0)
    eps = math.radians(obliquity_deg)

    mc_rad = math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps))
    return math.degrees(mc_rad) % 360

def get_planetary_positions(dt_utc: datetime, lat: float, lon: float, calc_mode: str = "modern") -> dict:
    """
    Get the high-precision geocentric coordinates of the planets and nodes,
    converted to sidereal longitudes using the selected Ayanamsa calculation mode.
    """
    # 1. Create skyfield time object
    t = ts.utc(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour, dt_utc.minute, dt_utc.second)
    
    # 2. Compute Ayanamsa & Obliquity
    ayanamsa = get_ayanamsa(t.tt, mode=calc_mode)
    T = (t.tt - 2451545.0) / 36525.0
    obliquity = get_obliquity(T)
    
    # 3. Local Sidereal Time, Lagna, and MC
    lst_hours = get_lst(t, lon)
    lagna_tropical = calculate_ascendant(lst_hours, lat, obliquity)
    lagna_sidereal = (lagna_tropical - ayanamsa) % 360
    
    mc_tropical = calculate_mc(lst_hours, obliquity)
    mc_sidereal = (mc_tropical - ayanamsa) % 360
    
    positions = {}
    
    # 4. Major Planets
    for p_name, p_body in PLANETS_MAP.items():
        try:
            astrometric = earth.at(t).observe(p_body)
            apparent = astrometric.apparent()
            lat_coord, lon_coord, distance = apparent.frame_latlon(ecliptic_frame)
            
            lon_deg = lon_coord.degrees % 360
            sid_deg = (lon_deg - ayanamsa) % 360
            sign_idx = int(sid_deg // 30) % 12
            
            # Calculate planet's daily velocity (radial/apparent speed in degrees/day)

            t_next = ts.utc(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + 1, dt_utc.minute, dt_utc.second)
            lat_next, lon_next, _ = earth.at(t_next).observe(p_body).apparent().frame_latlon(ecliptic_frame)
            speed_deg_hour = (lon_next.degrees - lon_deg)
            # Normalize wrap
            if speed_deg_hour > 180:
                speed_deg_hour -= 360
            elif speed_deg_hour < -180:
                speed_deg_hour += 360
            speed_deg_day = speed_deg_hour * 24.0
            
            is_retrograde = speed_deg_day < 0
            
            positions[p_name] = {
                "tropical": lon_deg,
                "sidereal": sid_deg,
                "sign_idx": sign_idx,
                "speed_deg_day": speed_deg_day,
                "is_retrograde": is_retrograde
            }
        except Exception as e:
            logging.error(f"Failed coordinates calculation for {p_name}: {e}")
            positions[p_name] = {"tropical": 0.0, "sidereal": 0.0, "sign_idx": 0, "speed_deg_day": 1.0, "is_retrograde": False}
            
    # 5. Nodes (Rahu / Ketu)
    # Rahu = Moon's ascending node. Calculated using Skyfield's Delaunay arguments
    try:
        args = fundamental_arguments(t.tdb)
        rahu_deg = math.degrees(args[4]) % 360
        rahu_sid = (rahu_deg - ayanamsa) % 360
        rahu_idx = int(rahu_sid // 30) % 12
        
        # Nodes are generally retrograde
        positions["Rahu"] = {
            "tropical": rahu_deg,
            "sidereal": rahu_sid,
            "sign_idx": rahu_idx,
            "speed_deg_day": -0.0529, # approx average motion of Rahu
            "is_retrograde": True
        }
    except Exception as e:
        logging.error(f"Rahu calculation failed: {e}")
        positions["Rahu"] = {"tropical": 0.0, "sidereal": 0.0, "sign_idx": 0, "speed_deg_day": -0.0529, "is_retrograde": True}
        
    ketu_sid = (positions["Rahu"]["sidereal"] + 180) % 360
    ketu_idx = int(ketu_sid // 30) % 12
    positions["Ketu"] = {
        "tropical": (positions["Rahu"]["tropical"] + 180) % 360,
        "sidereal": ketu_sid,
        "sign_idx": ketu_idx,
        "speed_deg_day": positions["Rahu"]["speed_deg_day"],
        "is_retrograde": True
    }

    
    return {
        "planets": positions,
        "lagna": lagna_sidereal,
        "mc": mc_sidereal,
        "ayanamsa": ayanamsa,
        "obliquity": obliquity,
        "lst": lst_hours,
        "jd": t.tt
    }
