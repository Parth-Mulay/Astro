import math
from datetime import datetime

TITHIS = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Amavasya"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshta",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

YOGAS = [
    "Vishkumbha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
    "Sukarma", "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva",
    "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyan",
    "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla",
    "Brahma", "Indra", "Vaidhriti"
]

VARAS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

REPEATING_KARANAS = ["Bava", "Balava", "Kaulava", "Taitila", "Garija", "Vanija", "Vishti"]

def calculate_tithi(sun_sid: float, moon_sid: float) -> dict:
    diff = (moon_sid - sun_sid) % 360
    tithi_num = int(diff // 12) + 1
    tithi_num = min(tithi_num, 30)
    
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    name = TITHIS[tithi_num - 1]
    
    return {
        "number": tithi_num,
        "name": name,
        "paksha": paksha,
        "angle": diff
    }

def calculate_vara(dt_local: datetime) -> dict:
    # isoweekday: Monday=1, ..., Sunday=7
    weekday = dt_local.isoweekday()
    vara_idx = (weekday % 7) # Sunday=0, Monday=1, ..., Saturday=6
    
    # In Vedic calendar, the day starts at sunrise.
    # To keep it standard and consistent, we return the weekday.
    return {
        "number": vara_idx + 1,
        "name": VARAS[vara_idx]
    }

def calculate_nakshatra(moon_sid: float) -> dict:
    # 27 Nakshatras, each spans 13.333333 degrees
    nak_num = int(moon_sid // (360.0 / 27.0)) + 1
    nak_num = min(nak_num, 27)
    
    return {
        "number": nak_num,
        "name": NAKSHATRAS[nak_num - 1],
        "degree": moon_sid % (360.0 / 27.0)
    }

def calculate_yoga(sun_sid: float, moon_sid: float) -> dict:
    sum_lon = (sun_sid + moon_sid) % 360
    yoga_num = int(sum_lon // (360.0 / 27.0)) + 1
    yoga_num = min(yoga_num, 27)
    
    return {
        "number": yoga_num,
        "name": YOGAS[yoga_num - 1]
    }

def calculate_karana(sun_sid: float, moon_sid: float) -> dict:
    diff = (moon_sid - sun_sid) % 360
    # There are 60 Karanas in a lunar month (each tithi has 2 karanas, so 6 degrees each)
    karana_num = int(diff // 6) + 1
    karana_num = min(karana_num, 60)
    
    if karana_num == 1:
        name = "Kintughna"
    elif 2 <= karana_num <= 57:
        idx = (karana_num - 2) % 7
        name = REPEATING_KARANAS[idx]
    elif karana_num == 58:
        name = "Shakuni"
    elif karana_num == 59:
        name = "Chatushpada"
    else:
        name = "Naga"
        
    return {
        "number": karana_num,
        "name": name
    }

def get_panchang_elements(sun_sid: float, moon_sid: float, dt_local: datetime) -> dict:
    return {
        "tithi": calculate_tithi(sun_sid, moon_sid),
        "vara": calculate_vara(dt_local),
        "nakshatra": calculate_nakshatra(moon_sid),
        "yoga": calculate_yoga(sun_sid, moon_sid),
        "karana": calculate_karana(sun_sid, moon_sid)
    }
