import logging
import requests
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder

from app.vedic_engine.astronomy.coords import get_planetary_positions
from app.vedic_engine.charts.houses import build_houses
from app.vedic_engine.panchang.elements import get_panchang_elements
from app.vedic_engine.panchang.times import get_day_timings
from app.vedic_engine.panchang.kalam import get_kalam_timings
from app.vedic_engine.charts.divisional import get_divisional_charts
from app.vedic_engine.charts.ashtakavarga import calculate_ashtakavarga
from app.vedic_engine.dasha.vimshottari import calculate_vimshottari
from app.vedic_engine.strength.shadbala import calculate_shadbala
from app.vedic_engine.yoga.rules import check_yogas
from app.vedic_engine.transit.gochar import calculate_gochar
from app.vedic_engine.eclipse.eclipse_engine import get_upcoming_eclipses
from app.vedic_engine.muhurta.muhurta_engine import get_all_muhurtas

def get_lat_lon(place_name: str) -> tuple[float, float, str]:
    place_clean = place_name.strip()
    if not place_clean:
        return 28.6139, 77.2090, "New Delhi, India (Fallback)"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_clean, "format": "json", "limit": 1}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            display_name = data[0]["display_name"]
            return lat, lon, display_name
    except Exception as e:
        logging.warning(f"Geocoding failed for '{place_clean}': {e}")
        
    return 28.6139, 77.2090, f"{place_clean} (Fallback: New Delhi)"

def get_timezone_offset(lat: float, lon: float, dt_local: datetime) -> tuple[str, float, datetime]:
    tf = TimezoneFinder()
    try:
        tz_name = tf.timezone_at(lng=lon, lat=lat)
    except Exception:
        tz_name = None
        
    if not tz_name:
        tz_name = "Asia/Kolkata"
        
    try:
        tz = ZoneInfo(tz_name)
        dt_aware = dt_local.replace(tzinfo=tz)
        utcoffset = dt_aware.utcoffset()
        if utcoffset is not None:
            offset_hours = utcoffset.total_seconds() / 3600.0
            return tz_name, offset_hours, dt_aware
    except Exception as e:
        logging.warning(f"Timezone resolution failed: {e}")
        
    tz = ZoneInfo("Asia/Kolkata")
    dt_aware = dt_local.replace(tzinfo=tz)
    return "Asia/Kolkata", 5.5, dt_aware

def calculate_professional_kundli(
    name: str, 
    dob: date, 
    birth_time: time, 
    place: str, 
    calc_mode: str = "modern", 
    house_system: str = "whole_sign"
) -> dict:
    """
    Unified high-precision Vedic Astrology service. Calculates astronomical positions,
    Panchang, houses, divisional charts, dashas, Shadbala, yogas, transits, and eclipses.
    """
    # 1. Resolve coordinates & timezone offset
    lat, lon, resolved_place = get_lat_lon(place)
    dt_local = datetime.combine(dob, birth_time)
    tz_name, offset, dt_aware = get_timezone_offset(lat, lon, dt_local)
    dt_utc = dt_aware.astimezone(ZoneInfo("UTC"))
    
    # 2. Get high-precision planetary and Lagna positions
    astronomy_data = get_planetary_positions(dt_utc, lat, lon, calc_mode=calc_mode)
    planets_sid = astronomy_data["planets"]
    lagna_sid = astronomy_data["lagna"]
    mc_sid = astronomy_data["mc"]
    
    # 3. Calculate Panchang elements
    sun_sid = planets_sid["Sun"]["sidereal"]
    moon_sid = planets_sid["Moon"]["sidereal"]
    panchang_data = get_panchang_elements(sun_sid, moon_sid, dt_local)
    
    # 4. Calculate Sunrise/Sunset & Moonrise/Moonset
    timings_data = get_day_timings(dob, lat, lon, tz_name)
    
    # 5. Calculate day/night division timings (Rahu Kalam, Horas, Choghadiyas)
    # Get next day's sunrise for night hours
    next_day_timings = get_day_timings(dob + timedelta(days=1), lat, lon, tz_name)
    sunrise_dt = timings_data["raw"]["sunrise"]
    sunset_dt = timings_data["raw"]["sunset"]
    next_sunrise_dt = next_day_timings["raw"]["sunrise"]
    
    kalam_data = get_kalam_timings(sunrise_dt, sunset_dt, next_sunrise_dt, panchang_data["vara"]["number"])
    
    # Combine timings and kalam under a clean Panchang object
    complete_panchang = {
        "city": resolved_place,
        "date": dt_local.strftime("%A, %d %B %Y"),
        "tithi": panchang_data["tithi"]["name"],
        "tithi_details": panchang_data["tithi"],
        "vara": panchang_data["vara"]["name"],
        "vara_details": panchang_data["vara"],
        "nakshatra": panchang_data["nakshatra"]["name"],
        "nakshatra_details": panchang_data["nakshatra"],
        "yoga": panchang_data["yoga"]["name"],
        "yoga_details": panchang_data["yoga"],
        "karana": panchang_data["karana"]["name"],
        "karana_details": panchang_data["karana"],
        "sunrise": timings_data["sunrise"],
        "sunset": timings_data["sunset"],
        "moonrise": timings_data["moonrise"],
        "moonset": timings_data["moonset"],
        "brahma_muhurta": timings_data["brahma_muhurta"],
        "abhijit_muhurta": timings_data["abhijit_muhurta"],
        "abhijit": f"{timings_data['abhijit_muhurta']['start']} – {timings_data['abhijit_muhurta']['end']}",
        "rahukaal": f"{kalam_data['rahu_kalam']['start']} – {kalam_data['rahu_kalam']['end']}",

        "rahu_kalam": kalam_data["rahu_kalam"],
        "yamaganda": kalam_data["yamaganda"],
        "gulika_kalam": kalam_data["gulika_kalam"],
        "durmuhurta": kalam_data["durmuhurta"],
        "horas": kalam_data["horas"],
        "choghadiya": kalam_data["choghadiya"]
    }
    
    # 6. House System distribution
    houses_data = build_houses(lagna_sid, mc_sid, planets_sid, system=house_system)
    
    # 7. Divisional Charts D1 to D60
    vargas_data = get_divisional_charts(planets_sid, lagna_sid)
    vargas_houses = {}
    RASHIS_TEMP = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    for div_name, placements in vargas_data.items():
        div_lagna_idx = placements["Lagna"]
        div_houses = {}
        for h in range(1, 13):
            sign_idx = (div_lagna_idx + h - 1) % 12
            planets_here = []
            for p_name, p_sign_idx in placements.items():
                if p_name != "Lagna" and p_sign_idx == sign_idx:
                    planets_here.append(p_name)
            div_houses[str(h)] = {
                "sign": RASHIS_TEMP[sign_idx],
                "rashi_num": sign_idx + 1,
                "planets": planets_here
            }
        vargas_houses[div_name] = div_houses

    
    # 8. Ashtakavarga point counts
    ashtakavarga_data = calculate_ashtakavarga(planets_sid, lagna_sid)
    
    # 9. Vimshottari Dasha tree
    dasha_data = calculate_vimshottari(moon_sid, dt_local)
    
    # 10. Shadbala (Planetary Strength)
    shadbala_data = calculate_shadbala(planets_sid, houses_data, dt_local)
    
    # 11. Yogas Scan
    yogas_data = check_yogas(planets_sid, houses_data)
    
    # 12. Gochar (Transit) Comparison
    gochar_data = calculate_gochar(astronomy_data, lat, lon, calc_mode=calc_mode)
    
    # 13. Eclipse Forecast
    eclipses_data = get_upcoming_eclipses(dt_local, search_days=365, tz_name=tz_name)
    
    # 14. Muhurtas Suitability
    muhurtas_data = get_all_muhurtas(complete_panchang)
    
    # Simple mapping of planet sign names
    RASHIS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    sun_sign_idx = int(sun_sid // 30) % 12
    moon_sign_idx = int(moon_sid // 30) % 12
    lagna_sign_idx = int(lagna_sid // 30) % 12
    
    # Re-structure house planets into list for compatibility
    houses_comp = {}
    for h, data in houses_data.items():
        houses_comp[h] = {
            "sign": data["sign"],
            "rashi_num": data["rashi_num"],
            "planets": data["planets"]
        }
        
    chart = {
        "name": name,
        "dob": dob.isoformat(),
        "birth_time": birth_time.strftime("%H:%M"),
        "place": resolved_place,
        "latitude": lat,
        "longitude": lon,
        "timezone": tz_name,
        "calculation_mode": calc_mode,
        "house_system": house_system,
        
        "sun_sign": RASHIS[sun_sign_idx],
        "moon_sign": RASHIS[moon_sign_idx],
        "lagna": RASHIS[lagna_sign_idx],
        "nakshatra": panchang_data["nakshatra"]["name"],
        
        "houses": houses_comp,
        "houses_full": houses_data,
        "planets": planets_sid,
        
        "panchang": complete_panchang,
        "divisional_charts": vargas_data,
        "vargas_houses": vargas_houses,
        "ashtakavarga": ashtakavarga_data,

        "dashas": dasha_data,
        "shadbala": shadbala_data,
        "yogas": yogas_data,
        "gochar": gochar_data,
        "eclipses": eclipses_data,
        "muhurtas": muhurtas_data,
        
        "systems": {"vedic": True, "kp": True, "lal_kitab": True}
    }
    
    return chart
