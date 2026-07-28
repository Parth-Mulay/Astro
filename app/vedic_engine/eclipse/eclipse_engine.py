import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from skyfield.api import load
from skyfield import almanac, eclipselib
from skyfield.framelib import ecliptic_frame

# Cache Skyfield ephemeris
eph = load('de421.bsp')
ts = load.timescale()
earth = eph['earth']
moon = eph['moon']

def get_upcoming_eclipses(start_dt: datetime, search_days: int = 365, tz_name: str = "Asia/Kolkata") -> list:
    """
    Find all solar and lunar eclipses starting from start_dt for search_days.
    Returns details of peak, start, end, type, and visibility.
    """
    tz = ZoneInfo(tz_name)
    utc_tz = ZoneInfo("UTC")
    
    # 1. Setup search window
    local_start = start_dt
    local_end = start_dt + timedelta(days=search_days)
    
    utc_start = local_start.astimezone(utc_tz)
    utc_end = local_end.astimezone(utc_tz)
    
    t0 = ts.utc(utc_start.year, utc_start.month, utc_start.day, utc_start.hour, utc_start.minute, utc_start.second)
    t1 = ts.utc(utc_end.year, utc_end.month, utc_end.day, utc_end.hour, utc_end.minute, utc_end.second)
    
    eclipses = []
    
    # 2. Lunar Eclipses (using Skyfield built-in eclipselib)
    try:
        times, codes, details = eclipselib.lunar_eclipses(t0, t1, eph)
        for t, code in zip(times, codes):
            dt_utc = t.utc_datetime()
            dt_local = dt_utc.astimezone(tz)
            
            # Map lunar eclipse codes
            # 0: Penumbral, 1: Partial, 2: Total
            e_type = "Penumbral Lunar Eclipse"
            if code == 1:
                e_type = "Partial Lunar Eclipse"
            elif code == 2:
                e_type = "Total Lunar Eclipse"
                
            eclipses.append({
                "type": e_type,
                "peak_time": dt_local.strftime("%Y-%m-%d %H:%M:%S"),
                "start_time": (dt_local - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": (dt_local + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "visibility": "Visible in regions where Moon is above horizon during peak",
                "magnitude": round(float(details.get('fraction', 0.5)), 3)
            })
    except Exception as e:
        logging.error(f"Lunar eclipse calculation failed: {e}")
        
    # 3. Solar Eclipses (using Moon phase conjunction and ecliptic latitude)
    try:
        t_phases, y_phases = almanac.find_discrete(t0, t1, almanac.moon_phases(eph))
        for ti, yi in zip(t_phases, y_phases):
            if yi == 0: # New Moon (conjunction in longitude)
                # Check Moon's geocentric ecliptic latitude
                lat_coord, _, _ = earth.at(ti).observe(moon).apparent().frame_latlon(ecliptic_frame)
                lat_deg = abs(lat_coord.degrees)
                
                # Solar eclipse occurs if Moon is within ~1.5° of ecliptic plane at New Moon
                if lat_deg < 1.5:
                    dt_utc = ti.utc_datetime()
                    dt_local = dt_utc.astimezone(tz)
                    
                    e_type = "Partial Solar Eclipse"
                    if lat_deg < 0.25:
                        e_type = "Total/Annular Solar Eclipse"
                        
                    eclipses.append({
                        "type": e_type,
                        "peak_time": dt_local.strftime("%Y-%m-%d %H:%M:%S"),
                        "start_time": (dt_local - timedelta(hours=1, minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
                        "end_time": (dt_local + timedelta(hours=1, minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
                        "visibility": "Visible along the narrow path of shadow on Earth's surface",
                        "magnitude": round(1.0 - (lat_deg / 1.5), 3)
                    })
    except Exception as e:
        logging.error(f"Solar eclipse calculation failed: {e}")
        
    # Sort eclipses by peak time
    eclipses.sort(key=lambda x: x["peak_time"])
    return eclipses
