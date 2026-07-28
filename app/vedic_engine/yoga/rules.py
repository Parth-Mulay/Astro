SIGN_LORDS = {
    0: "Mars",     # Aries
    1: "Venus",    # Taurus
    2: "Mercury",  # Gemini
    3: "Moon",     # Cancer
    4: "Sun",      # Leo
    5: "Mercury",  # Virgo
    6: "Venus",    # Libra
    7: "Mars",     # Scorpio
    8: "Jupiter",  # Sagittarius
    9: "Saturn",   # Capricorn
    10: "Saturn",  # Aquarius
    11: "Jupiter"  # Pisces
}

DEBILITATION_SIGNS = {
    "Sun": 6,       # Libra
    "Moon": 7,      # Scorpio
    "Mars": 3,      # Cancer
    "Mercury": 11,  # Pisces
    "Jupiter": 9,   # Capricorn
    "Venus": 5,     # Virgo
    "Saturn": 0     # Aries
}

EXALTATION_SIGNS = {
    "Sun": 0,       # Aries
    "Moon": 1,      # Taurus
    "Mars": 9,      # Capricorn
    "Mercury": 5,   # Virgo
    "Jupiter": 3,   # Cancer
    "Venus": 11,    # Pisces
    "Saturn": 6     # Libra
}

def get_house_lord(house_num: int, houses: dict) -> str:
    """Get the ruler planet of a specific house (1 to 12)."""
    sign_idx = houses[str(house_num)]["rashi_num"] - 1
    return SIGN_LORDS[sign_idx]

def get_planet_house(p_name: str, houses: dict) -> int:
    """Find the house number (1 to 12) where a planet is placed."""
    for h, h_data in houses.items():
        if p_name in h_data["planets"]:
            return int(h)
    return 1

def check_yogas(planets_positions: dict, houses: dict) -> list:
    """
    Scan the chart and check for standard Vedic Yogas.
    Returns:
      A list of dicts: [{"name": "Yoga Name", "status": True/False, "description": "..."}]
    """
    yogas = []
    
    # 1. Fetch placements
    moon_house = get_planet_house("Moon", houses)
    jupiter_house = get_planet_house("Jupiter", houses)
    sun_house = get_planet_house("Sun", houses)
    mercury_house = get_planet_house("Mercury", houses)
    mars_house = get_planet_house("Mars", houses)
    
    # --- A. Gajakesari Yoga ---
    gaja_rel = (jupiter_house - moon_house) % 12 + 1
    has_gajakesari = gaja_rel in [1, 4, 7, 10]
    yogas.append({
        "name": "Gajakesari Yoga",
        "status": has_gajakesari,
        "description": "Jupiter is in a Kendra (1st, 4th, 7th, or 10th house) from the Moon. Brings prosperity, wisdom, and leadership."
    })
    
    # --- B. Budhaditya Yoga ---
    has_budhaditya = (sun_house == mercury_house)
    yogas.append({
        "name": "Budhaditya Yoga",
        "status": has_budhaditya,
        "description": "Sun and Mercury are conjoined in the same house. Blesses the native with high intelligence, analytical power, and fame."
    })
    
    # --- C. Chandra Mangal Yoga ---
    has_chandra_mangal = (moon_house == mars_house)
    yogas.append({
        "name": "Chandra Mangal Yoga",
        "status": has_chandra_mangal,
        "description": "Moon and Mars are conjoined in the same house. Fosters financial success, courage, and business acumen."
    })
    
    # --- D. Neecha Bhanga Raja Yoga (Cancellation of Debilitation) ---
    has_neecha_bhanga = False
    details = ""
    # Find if any planet is debilitated
    for p_name, p_data in planets_positions.items():
        sign_idx = p_data["sign_idx"]
        if p_name in DEBILITATION_SIGNS and sign_idx == DEBILITATION_SIGNS[p_name]:
            # Planet is debilitated. Check if lord of that sign is in a Kendra from Lagna or Moon
            lord = SIGN_LORDS[sign_idx]
            lord_house = get_planet_house(lord, houses)
            if lord_house in [1, 4, 7, 10]:
                has_neecha_bhanga = True
                details = f"Debilitation of {p_name} is cancelled by its sign lord {lord} placed in Kendra."
                break
                
            # Check if Moon is in Kendra from Lagna
            if moon_house in [1, 4, 7, 10]:
                has_neecha_bhanga = True
                details = f"Debilitation of {p_name} is cancelled because the Moon is in a Kendra house."
                break
                
    yogas.append({
        "name": "Neecha Bhanga Raja Yoga",
        "status": has_neecha_bhanga,
        "description": f"Cancellation of a planet's debilitation, turning weakness into strength. {details}" if has_neecha_bhanga else "No debilitated planet's cancellation detected."
    })
    
    # --- E. Lakshmi Yoga ---
    # Lord of 9th in Kendra/Trikona, and Lord of 1st is strong (exalted or in own sign)
    lord_9 = get_house_lord(9, houses)
    lord_1 = get_house_lord(1, houses)
    lord_9_house = get_planet_house(lord_9, houses)
    
    lord_1_sign = planets_positions[lord_1]["sign_idx"] if lord_1 in planets_positions else 0
    lord_1_strong = (lord_1_sign == EXALTATION_SIGNS.get(lord_1, -1) or lord_1_sign in [k for k, v in SIGN_LORDS.items() if v == lord_1])
    
    has_lakshmi = (lord_9_house in [1, 4, 7, 10, 5, 9] and lord_1_strong)
    yogas.append({
        "name": "Lakshmi Yoga",
        "status": has_lakshmi,
        "description": "Lord of the 9th (fortune) is in a Kendra/Trikona house, and the Lagna lord is highly strong. Brings immense wealth, grace, and noble qualities."
    })
    
    # --- F. Vipareeta Raja Yoga ---
    # Lords of dusthanas (6, 8, 12) placed in dusthanas (6, 8, 12)
    lord_6 = get_house_lord(6, houses)
    lord_8 = get_house_lord(8, houses)
    lord_12 = get_house_lord(12, houses)
    
    l6_house = get_planet_house(lord_6, houses)
    l8_house = get_planet_house(lord_8, houses)
    l12_house = get_planet_house(lord_12, houses)
    
    has_vipareeta = (l6_house in [6, 8, 12] or l8_house in [6, 8, 12] or l12_house in [6, 8, 12])
    yogas.append({
        "name": "Vipareeta Raja Yoga",
        "status": has_vipareeta,
        "description": "A dusthana house lord is placed in another dusthana house (6th, 8th, 12th). Overcomes obstacles and grants sudden success from adversity."
    })
    
    # --- G. Panch Mahapurusha Yogas ---
    mahapurushas = []
    map_mp = {
        "Mars": ("Ruchaka Yoga", "courage and physical power"),
        "Mercury": ("Bhadra Yoga", "intellect, logic, and commercial success"),
        "Jupiter": ("Hamsa Yoga", "morality, wisdom, and spiritual progress"),
        "Venus": ("Malavya Yoga", "art, beauty, luxury, and happiness"),
        "Saturn": ("Sasa Yoga", "discipline, authority, and longevity")
    }
    
    for p_name, (y_name, y_desc) in map_mp.items():
        if p_name in planets_positions:
            p_house = get_planet_house(p_name, houses)
            p_sign = planets_positions[p_name]["sign_idx"]
            
            # Check Kendra & Strong (own sign or exalted)
            in_kendra = p_house in [1, 4, 7, 10]
            is_strong = (p_sign == EXALTATION_SIGNS.get(p_name, -1) or SIGN_LORDS.get(p_sign) == p_name)
            
            if in_kendra and is_strong:
                mahapurushas.append(y_name)
                
    has_mp = len(mahapurushas) > 0
    yogas.append({
        "name": "Panch Mahapurusha Yoga",
        "status": has_mp,
        "description": f"One of the five great planetary combinations detected: {', '.join(mahapurushas)}. Grants exceptional traits ruled by the respective planet." if has_mp else "No Panch Mahapurusha combinations detected."
    })
    
    # --- H. Dharma Karma Adhipati Yoga ---
    # Lord of 9 (Dharma) and Lord of 10 (Karma) are conjoined in the same house
    lord_10 = get_house_lord(10, houses)
    l9_house = get_planet_house(lord_9, houses)
    l10_house = get_planet_house(lord_10, houses)
    
    has_dharma_karma = (l9_house == l10_house)
    yogas.append({
        "name": "Dharma Karma Adhipati Yoga",
        "status": has_dharma_karma,
        "description": "Lords of the 9th (Dharma) and 10th (Karma) houses are conjoined. High career success, moral authority, and professional honor."
    })
    
    # --- I. Parivartana Yoga (Exchange of Signs) ---
    has_exchange = False
    exchanges = []
    # Check all pairs of houses (1 to 12)
    for h1 in range(1, 13):
        for h2 in range(h1 + 1, 13):
            lord1 = get_house_lord(h1, houses)
            lord2 = get_house_lord(h2, houses)
            
            h1_placed = get_planet_house(lord1, houses)
            h2_placed = get_planet_house(lord2, houses)
            
            # Mutual exchange
            if h1_placed == h2 and h2_placed == h1:
                has_exchange = True
                exchanges.append(f"House {h1} ({lord1}) exchange with House {h2} ({lord2})")
                
    yogas.append({
        "name": "Parivartana Yoga",
        "status": has_exchange,
        "description": f"Mutual exchange of signs between house lords: {', '.join(exchanges)}. Strengthens both houses involved." if has_exchange else "No house lord sign exchanges detected."
    })
    
    return yogas
