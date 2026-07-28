from datetime import datetime, timedelta

# Weekdays: Sunday=1, Monday=2, Tuesday=3, Wednesday=4, Thursday=5, Friday=6, Saturday=7
RAHU_PARTS = {1: 8, 2: 2, 3: 7, 4: 5, 5: 6, 6: 4, 7: 3}
YAMA_PARTS = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1, 6: 7, 7: 6}
GULIKA_PARTS = {1: 7, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1}

# Durmuhurta Muhurta Indices (1-based, out of 15 divisions of the daytime)
DURMUHURTA_MAP = {
    1: [14],
    2: [9, 12],
    3: [2, 12],
    4: [12],
    5: [6],
    6: [4, 9],
    7: [1]
}

# Chaldean order of planets for Horas
HORA_ORDER = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]
# First Hora planet for each weekday (Sunday=1, ..., Saturday=7)
WEEKDAY_HORA_START = {
    1: "Sun",
    2: "Moon",
    3: "Mars",
    4: "Mercury",
    5: "Jupiter",
    6: "Venus",
    7: "Saturn"
}

# Choghadiya orders (daytime)
CHOGHADIYA_ORDER = {
    1: ["Udveg", "Chara", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg"],     # Sun
    2: ["Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chara", "Labh", "Amrit"],     # Mon
    3: ["Rog", "Udveg", "Chara", "Labh", "Amrit", "Kaal", "Shubh", "Rog"],       # Tue
    4: ["Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chara", "Labh"],     # Wed
    5: ["Shubh", "Rog", "Udveg", "Chara", "Labh", "Amrit", "Kaal", "Shubh"],     # Thu
    6: ["Chara", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chara"],     # Fri
    7: ["Kaal", "Shubh", "Rog", "Udveg", "Chara", "Labh", "Amrit", "Kaal"]      # Sat
}

CHOGHADIYA_STATUS = {
    "Amrit": "highly_auspicious",
    "Shubh": "auspicious",
    "Labh": "auspicious",
    "Chara": "moderate",
    "Udveg": "inauspicious",
    "Kaal": "inauspicious",
    "Rog": "inauspicious"
}

def get_kalam_timings(sunrise: datetime, sunset: datetime, next_sunrise: datetime, weekday_num: int) -> dict:
    """
    Calculate Rahu Kalam, Gulika, Yamaganda, Durmuhurta, Horas, and Choghadiya.
    weekday_num: Sunday=1, Monday=2, ..., Saturday=7
    """
    day_duration = sunset - sunrise
    night_duration = next_sunrise - sunset
    
    # 1. Eight divisions for Rahu, Yama, Gulika
    part_dur = day_duration / 8
    
    def get_slot_times(part_num):
        start = sunrise + (part_num - 1) * part_dur
        end = sunrise + part_num * part_dur
        return start.strftime("%H:%M"), end.strftime("%H:%M")
        
    rahu_start, rahu_end = get_slot_times(RAHU_PARTS[weekday_num])
    yama_start, yama_end = get_slot_times(YAMA_PARTS[weekday_num])
    gulika_start, gulika_end = get_slot_times(GULIKA_PARTS[weekday_num])
    
    # 2. Durmuhurta: 15 divisions of daytime
    muhurta_dur = day_duration / 15
    durmuhurtas = []
    for m_idx in DURMUHURTA_MAP[weekday_num]:
        start = sunrise + (m_idx - 1) * muhurta_dur
        end = sunrise + m_idx * muhurta_dur
        durmuhurtas.append({
            "slot": m_idx,
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M")
        })
        
    # 3. Horas (12 day Horas, 12 night Horas)
    day_hora_dur = day_duration / 12
    night_hora_dur = night_duration / 12
    
    # Sequence starting lord
    start_lord = WEEKDAY_HORA_START[weekday_num]
    start_idx = HORA_ORDER.index(start_lord)
    
    horas = []
    
    # Daytime Horas
    for i in range(12):
        lord = HORA_ORDER[(start_idx + i) % 7]
        start = sunrise + i * day_hora_dur
        end = sunrise + (i + 1) * day_hora_dur
        horas.append({
            "period": "day",
            "number": i + 1,
            "lord": lord,
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M")
        })
        
    # Nighttime Horas
    start_idx_night = (start_idx + 12) % 7
    for i in range(12):
        lord = HORA_ORDER[(start_idx_night + i) % 7]
        start = sunset + i * night_hora_dur
        end = sunset + (i + 1) * night_hora_dur
        horas.append({
            "period": "night",
            "number": i + 1,
            "lord": lord,
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M")
        })
        
    # 4. Choghadiya (8 day divisions, 8 night divisions)
    day_chog_dur = day_duration / 8
    night_chog_dur = night_duration / 8
    
    # Daytime sequence
    day_seq = CHOGHADIYA_ORDER[weekday_num]
    
    choghadiyas = []
    for i in range(8):
        name = day_seq[i]
        start = sunrise + i * day_chog_dur
        end = sunrise + (i + 1) * day_chog_dur
        choghadiyas.append({
            "period": "day",
            "number": i + 1,
            "name": name,
            "status": CHOGHADIYA_STATUS[name],
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M")
        })
        
    # Nighttime sequence starts from the 5th Choghadiya of the day sequence
    night_seq = day_seq[4:] + day_seq[:4]
    for i in range(8):
        name = night_seq[i]
        start = sunset + i * night_chog_dur
        end = sunset + (i + 1) * night_chog_dur
        choghadiyas.append({
            "period": "night",
            "number": i + 1,
            "name": name,
            "status": CHOGHADIYA_STATUS[name],
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M")
        })
        
    return {
        "rahu_kalam": {"start": rahu_start, "end": rahu_end},
        "yamaganda": {"start": yama_start, "end": yama_end},
        "gulika_kalam": {"start": gulika_start, "end": gulika_end},
        "durmuhurta": durmuhurtas,
        "horas": horas,
        "choghadiya": choghadiyas
    }
