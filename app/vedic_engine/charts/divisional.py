def get_sign_and_part(longitude: float) -> tuple[int, float]:
    """Return the sign index (0-11) and the degrees within that sign (0-30)."""
    sign_idx = int(longitude // 30) % 12
    sign_deg = longitude % 30
    return sign_idx, sign_deg

def calculate_d1(lon: float) -> int:
    return int(lon // 30) % 12

def calculate_d2(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    is_odd = (sign_idx % 2) != 0
    if is_odd:
        # First 15 is Sun (Leo=4), Second 15 is Moon (Cancer=3)
        return 4 if deg < 15.0 else 3
    else:
        # First 15 is Moon (Cancer=3), Second 15 is Sun (Leo=4)
        return 3 if deg < 15.0 else 4

def calculate_d3(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg // 10.0) # 0, 1, 2
    if part == 0:
        return sign_idx
    elif part == 1:
        return (sign_idx + 4) % 12
    else:
        return (sign_idx + 8) % 12

def calculate_d4(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg // 7.5) # 0, 1, 2, 3
    return (sign_idx + part * 3) % 12

def calculate_d7(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / (30.0 / 7.0)) # 0 to 6
    is_odd = (sign_idx % 2) != 0
    start_sign = sign_idx if is_odd else (sign_idx + 6) % 12
    return (start_sign + part) % 12

def calculate_d9(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / (30.0 / 9.0)) # 0 to 8
    element = sign_idx % 4
    if element == 0:   # Fire (Aries, Leo, Sagittarius) -> Starts from Aries (0)
        start_sign = 0
    elif element == 1: # Earth (Taurus, Virgo, Capricorn) -> Starts from Capricorn (9)
        start_sign = 9
    elif element == 2: # Air (Gemini, Libra, Aquarius) -> Starts from Libra (6)
        start_sign = 6
    else:              # Water (Cancer, Scorpio, Pisces) -> Starts from Cancer (3)
        start_sign = 3
    return (start_sign + part) % 12

def calculate_d10(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / 3.0) # 0 to 9
    is_odd = (sign_idx % 2) != 0
    start_sign = sign_idx if is_odd else (sign_idx + 8) % 12
    return (start_sign + part) % 12

def calculate_d12(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / 2.5) # 0 to 11
    return (sign_idx + part) % 12

def calculate_d16(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / 1.875) # 0 to 15
    movability = sign_idx % 3
    if movability == 0:   # Movable -> Starts from Aries (0)
        start_sign = 0
    elif movability == 1: # Fixed -> Starts from Leo (4)
        start_sign = 4
    else:                 # Dual -> Starts from Sagittarius (8)
        start_sign = 8
    return (start_sign + part) % 12

def calculate_d20(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / 1.5) # 0 to 19
    movability = sign_idx % 3
    if movability == 0:   # Movable -> Starts from Aries (0)
        start_sign = 0
    elif movability == 1: # Fixed -> Starts from Sagittarius (8)
        start_sign = 8
    else:                 # Dual -> Starts from Leo (4)
        start_sign = 4
    return (start_sign + part) % 12

def calculate_d24(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / 1.25) # 0 to 23
    is_odd = (sign_idx % 2) != 0
    start_sign = 4 if is_odd else 3 # Odd starts Leo (4), Even starts Cancer (3)
    return (start_sign + part) % 12

def calculate_d27(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / (30.0 / 27.0)) # 0 to 26
    element = sign_idx % 4
    if element == 0:   # Fire -> Starts from Aries (0)
        start_sign = 0
    elif element == 1: # Earth -> Starts from Cancer (3)
        start_sign = 3
    elif element == 2: # Air -> Starts from Libra (6)
        start_sign = 6
    else:              # Water -> Starts from Capricorn (9)
        start_sign = 9
    return (start_sign + part) % 12

def calculate_d30(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    is_odd = (sign_idx % 2) != 0
    if is_odd:
        # Aries=0, Taurus=1, Gemini=2, Cancer=3, Leo=4, Virgo=5, Libra=6, Scorpio=7, Sag=8, Cap=9, Aqu=10, Pis=11
        if deg < 5.0:
            return 0  # Mars (Aries)
        elif deg < 10.0:
            return 10 # Saturn (Aquarius)
        elif deg < 18.0:
            return 8  # Jupiter (Sagittarius)
        elif deg < 25.0:
            return 2  # Mercury (Gemini)
        else:
            return 6  # Venus (Libra)
    else:
        if deg < 5.0:
            return 1  # Venus (Taurus)
        elif deg < 12.0:
            return 5  # Mercury (Virgo)
        elif deg < 20.0:
            return 11 # Jupiter (Pisces)
        elif deg < 25.0:
            return 9  # Saturn (Capricorn)
        else:
            return 7  # Mars (Scorpio)

def calculate_d40(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / 0.75) # 0 to 39
    is_odd = (sign_idx % 2) != 0
    start_sign = 0 if is_odd else 6 # Odd starts Aries (0), Even starts Libra (6)
    return (start_sign + part) % 12

def calculate_d45(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / (30.0 / 45.0)) # 0 to 44
    movability = sign_idx % 3
    if movability == 0:
        start_sign = 0 # Movable -> Aries
    elif movability == 1:
        start_sign = 4 # Fixed -> Leo
    else:
        start_sign = 8 # Dual -> Sagittarius
    return (start_sign + part) % 12

def calculate_d60(lon: float) -> int:
    sign_idx, deg = get_sign_and_part(lon)
    part = int(deg / 0.5) # 0 to 59
    return (sign_idx + part) % 12

DIVISION_CALCULATORS = {
    "D1": calculate_d1,
    "D2": calculate_d2,
    "D3": calculate_d3,
    "D4": calculate_d4,
    "D7": calculate_d7,
    "D9": calculate_d9,
    "D10": calculate_d10,
    "D12": calculate_d12,
    "D16": calculate_d16,
    "D20": calculate_d20,
    "D24": calculate_d24,
    "D27": calculate_d27,
    "D30": calculate_d30,
    "D40": calculate_d40,
    "D45": calculate_d45,
    "D60": calculate_d60
}

def get_divisional_charts(planets_sidereal: dict, lagna_sidereal: float) -> dict:
    """
    Calculate sign placements for all divisional charts D1 through D60
    for all planets and the Lagna.
    """
    divisional_data = {}
    for div_name, calc_fn in DIVISION_CALCULATORS.items():
        chart_placements = {}
        # Calculate planet divisional placements
        for p_name, p_data in planets_sidereal.items():
            chart_placements[p_name] = calc_fn(p_data["sidereal"])
        # Calculate Lagna divisional placement
        chart_placements["Lagna"] = calc_fn(lagna_sidereal)
        divisional_data[div_name] = chart_placements
    return divisional_data
