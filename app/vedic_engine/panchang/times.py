import logging
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from skyfield.api import load, wgs84
from skyfield import almanac

# Cache Skyfield ephemeris
eph = load('de421.bsp')
ts = load.timescale()
moon = eph['moon']

def get_day_timings(local_date: date, lat: float, lon: float, tz_name: str) -> dict:
    """
    Calculate Sunrise, Sunset, Moonrise, Moonset, Brahma Muhurta,
    and Abhijit Muhurta for a given local date and location.
    """
    tz = ZoneInfo(tz_name)
    
    # 1. Define local start and end of the day
    local_start = datetime.combine(local_date, datetime.min.time(), tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    
    # Convert to UTC for Skyfield
    utc_start = local_start.astimezone(ZoneInfo("UTC"))
    utc_end = local_end.astimezone(ZoneInfo("UTC"))
    
    t0 = ts.utc(utc_start.year, utc_start.month, utc_start.day, utc_start.hour, utc_start.minute, utc_start.second)
    t1 = ts.utc(utc_end.year, utc_end.month, utc_end.day, utc_end.hour, utc_end.minute, utc_end.second)
    
    # Define observer location
    location = wgs84.latlon(lat, lon)
    
    # 2. Sunrise & Sunset
    sunrise_local = None
    sunset_local = None
    try:
        f_sun = almanac.sunrise_sunset(eph, location)
        t_sun, y_sun = almanac.find_discrete(t0, t1, f_sun)
        
        for ti, yi in zip(t_sun, y_sun):
            dt_utc = ti.utc_datetime()
            dt_local = dt_utc.astimezone(tz)
            if local_start <= dt_local < local_end:
                if yi: # True = Sunrise
                    sunrise_local = dt_local
                else:  # False = Sunset
                    sunset_local = dt_local
    except Exception as e:
        logging.error(f"Sunrise/Sunset calculation failed: {e}")
        
    # Default fallbacks if calculation fails (approximate for India)
    if not sunrise_local:
        sunrise_local = datetime.combine(local_date, datetime.min.time(), tzinfo=tz) + timedelta(hours=6)
    if not sunset_local:
        sunset_local = datetime.combine(local_date, datetime.min.time(), tzinfo=tz) + timedelta(hours=18, minutes=30)
        
    # 3. Moonrise & Moonset
    moonrise_local = None
    moonset_local = None
    try:
        f_moon = almanac.risings_and_settings(eph, moon, location)
        t_moon, y_moon = almanac.find_discrete(t0, t1, f_moon)
        
        for ti, yi in zip(t_moon, y_moon):
            dt_utc = ti.utc_datetime()
            dt_local = dt_utc.astimezone(tz)
            if local_start <= dt_local < local_end:
                if yi: # True = Moonrise
                    moonrise_local = dt_local
                else:  # False = Moonset
                    moonset_local = dt_local
    except Exception as e:
        logging.error(f"Moonrise/Moonset calculation failed: {e}")
        
    # 4. Brahma Muhurta (Starts 96 mins before Sunrise, ends 48 mins before Sunrise)
    brahma_start = sunrise_local - timedelta(minutes=96)
    brahma_end = sunrise_local - timedelta(minutes=48)
    
    # 5. Abhijit Muhurta (Centered around Solar Noon)
    # Solar Noon is the midpoint between Sunrise and Sunset
    day_length = sunset_local - sunrise_local
    solar_noon = sunrise_local + (day_length / 2)
    abhijit_start = solar_noon - timedelta(minutes=24)
    abhijit_end = solar_noon + timedelta(minutes=24)
    
    return {
        "sunrise": sunrise_local.strftime("%H:%M:%S"),
        "sunset": sunset_local.strftime("%H:%M:%S"),
        "moonrise": moonrise_local.strftime("%H:%M:%S") if moonrise_local else "—",
        "moonset": moonset_local.strftime("%H:%M:%S") if moonset_local else "—",
        "brahma_muhurta": {
            "start": brahma_start.strftime("%H:%M"),
            "end": brahma_end.strftime("%H:%M")
        },
        "abhijit_muhurta": {
            "start": abhijit_start.strftime("%H:%M"),
            "end": abhijit_end.strftime("%H:%M")
        },
        "raw": {
            "sunrise": sunrise_local,
            "sunset": sunset_local,
            "moonrise": moonrise_local,
            "moonset": moonset_local
        }
    }
