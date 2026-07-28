# Auspicious lists for Muhurta

VIVAH_NAKSHATRAS = ["Rohini", "Mrigashira", "Magha", "Uttara Phalguni", "Hasta", "Swati", "Anuradha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Uttara Bhadrapada", "Revati"]
VIVAH_TITHIS = [2, 3, 5, 7, 10, 11, 13]

GRIHA_NAKSHATRAS = ["Rohini", "Mrigashira", "Uttara Phalguni", "Hasta", "Chitra", "Anuradha", "Uttara Ashadha", "Uttara Bhadrapada", "Revati"]
GRIHA_TITHIS = [2, 3, 5, 7, 10, 11, 12, 13]

VEHICLE_NAKSHATRAS = ["Ashwini", "Rohini", "Punarvasu", "Pushya", "Hasta", "Chitra", "Swati", "Anuradha", "Shatabhisha", "Revati"]
VEHICLE_TITHIS = [1, 2, 3, 5, 7, 10, 11, 13, 15]

BUSINESS_NAKSHATRAS = ["Pushya", "Anuradha", "Hasta", "Revati", "Ashwini", "Rohini", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada"]
BUSINESS_TITHIS = [2, 3, 5, 7, 10, 11, 12, 13]

NAMING_NAKSHATRAS = ["Anuradha", "Mrigashira", "Hasta", "Pushya", "Rohini", "Swati", "Shravana", "Shatabhisha", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada", "Revati"]
NAMING_TITHIS = [1, 2, 3, 5, 7, 10, 11, 12, 13]

TRAVEL_NAKSHATRAS = ["Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Anuradha", "Shravana", "Dhanishta", "Revati"]
TRAVEL_TITHIS = [1, 2, 3, 5, 7, 10, 11, 12, 13]

INVESTMENT_NAKSHATRAS = ["Ashwini", "Rohini", "Pushya", "Hasta", "Anuradha", "Shravana", "Revati"]
INVESTMENT_TITHIS = [1, 2, 3, 5, 7, 10, 11, 12, 13]

INAUSPICIOUS_TITHIS = [4, 9, 14, 30] # Chaturthi, Navami, Chaturdashi, Amavasya

def get_activity_muhurta(activity: str, panchang: dict) -> dict:
    """
    Calculate Muhurta suitability score (0% to 100%) for a given activity
    based on the current day's Panchang elements.
    """
    tithi_name = panchang["tithi_details"]["name"]
    tithi_num = panchang["tithi_details"]["number"]
    # Map to 1-15 base tithi for Paksha-independent evaluation, keeping Amavasya (30) distinct
    tithi_base = tithi_num
    if tithi_num == 30:
        tithi_base = 30
    elif tithi_num > 15:
        tithi_base = tithi_num - 15

    nakshatra = panchang["nakshatra_details"]["name"]
    vara = panchang["vara_details"]["name"]

    score = 50.0
    positives = []
    negatives = []

    # Define detailed activity-specific rules
    rules = {
        "marriage": {
            "highly_ausp_naks": ["Rohini", "Mrigashira", "Anuradha", "Revati", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada", "Hasta"],
            "ausp_naks": ["Swati", "Magha", "Mula"],
            "highly_ausp_tithis": [2, 3, 5, 7, 10, 11, 13],
            "inausp_tithis": [4, 9, 14, 30, 8, 12],
            "favorable_varas": ["Monday", "Wednesday", "Thursday", "Friday"],
            "unfavorable_varas": ["Tuesday", "Saturday", "Sunday"],
            "vara_penalty": -15
        },
        "griha_pravesh": {
            "highly_ausp_naks": ["Rohini", "Mrigashira", "Chitra", "Anuradha", "Revati", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada"],
            "ausp_naks": ["Hasta", "Pushya"],
            "highly_ausp_tithis": [2, 3, 5, 7, 10, 11, 13],
            "inausp_tithis": [4, 9, 14, 30],
            "favorable_varas": ["Monday", "Wednesday", "Thursday", "Friday"],
            "unfavorable_varas": ["Tuesday"],
            "vara_penalty": -20,
            "neutral_varas": ["Saturday", "Sunday"],
            "neutral_vara_penalty": -5
        },
        "vehicle_purchase": {
            "highly_ausp_naks": ["Ashwini", "Rohini", "Punarvasu", "Pushya", "Hasta", "Chitra", "Swati", "Anuradha", "Shatabhisha", "Revati"],
            "ausp_naks": [],
            "highly_ausp_tithis": [1, 2, 3, 5, 7, 10, 11, 13, 15],
            "inausp_tithis": [4, 9, 14, 30],
            "favorable_varas": ["Sunday", "Monday", "Wednesday", "Thursday", "Friday", "Saturday"],
            "unfavorable_varas": ["Tuesday"],
            "vara_penalty": -15
        },
        "business_opening": {
            "highly_ausp_naks": ["Pushya", "Anuradha", "Hasta", "Revati", "Rohini", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada", "Ashwini"],
            "ausp_naks": ["Chitra", "Swati", "Shravana"],
            "highly_ausp_tithis": [2, 3, 5, 7, 10, 11, 12, 13, 15],
            "inausp_tithis": [4, 9, 14, 30],
            "favorable_varas": ["Monday", "Wednesday", "Thursday", "Friday"],
            "unfavorable_varas": ["Tuesday"],
            "vara_penalty": -15,
            "neutral_varas": ["Sunday", "Saturday"],
            "neutral_vara_penalty": 0
        },
        "naming_ceremony": {
            "highly_ausp_naks": ["Rohini", "Mrigashira", "Hasta", "Anuradha", "Revati", "Pushya", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada", "Shravana", "Shatabhisha", "Swati"],
            "ausp_naks": [],
            "highly_ausp_tithis": [1, 2, 3, 5, 7, 10, 11, 12, 13],
            "inausp_tithis": [4, 9, 14, 30],
            "favorable_varas": ["Monday", "Wednesday", "Thursday", "Friday"],
            "unfavorable_varas": ["Tuesday"],
            "vara_penalty": -10,
            "neutral_varas": ["Sunday", "Saturday"],
            "neutral_vara_penalty": 0
        },
        "travel": {
            "highly_ausp_naks": ["Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Anuradha", "Shravana", "Dhanishta", "Revati"],
            "ausp_naks": [],
            "highly_ausp_tithis": [1, 2, 3, 5, 7, 10, 11, 12, 13],
            "inausp_tithis": [4, 9, 14, 30],
            "favorable_varas": ["Monday", "Wednesday", "Thursday", "Friday"],
            "unfavorable_varas": ["Sunday", "Tuesday", "Saturday"],
            "vara_penalty": -10
        },
        "investment": {
            "highly_ausp_naks": ["Ashwini", "Rohini", "Pushya", "Hasta", "Anuradha", "Shravana", "Revati"],
            "ausp_naks": [],
            "highly_ausp_tithis": [1, 2, 3, 5, 7, 10, 11, 12, 13],
            "inausp_tithis": [4, 9, 14, 30],
            "favorable_varas": ["Monday", "Wednesday", "Thursday", "Friday"],
            "unfavorable_varas": ["Tuesday", "Saturday"],
            "vara_penalty": -10,
            "neutral_varas": ["Sunday"],
            "neutral_vara_penalty": 0
        }
    }

    act_rules = rules.get(activity, rules["investment"])

    # 1. Evaluate Nakshatra
    if nakshatra in act_rules["highly_ausp_naks"]:
        score += 30.0
        positives.append(f"Auspicious Nakshatra ({nakshatra}) for this activity.")
    elif nakshatra in act_rules.get("ausp_naks", []):
        score += 15.0
        positives.append(f"Moderately favorable Nakshatra ({nakshatra}).")
    else:
        score -= 10.0
        negatives.append(f"Neutral or unfavorable Nakshatra ({nakshatra}) for this activity.")

    # 2. Evaluate Tithi
    if tithi_base in act_rules["highly_ausp_tithis"]:
        score += 20.0
        positives.append(f"Auspicious Tithi ({tithi_name}).")
    elif tithi_base in act_rules["inausp_tithis"]:
        score -= 30.0
        negatives.append(f"Inauspicious Tithi ({tithi_name}) - typically avoided for important beginnings.")
    else:
        positives.append(f"Neutral Tithi ({tithi_name}).")

    # 3. Evaluate Weekday (Vara)
    if vara in act_rules["favorable_varas"]:
        score += 10.0
        positives.append(f"Favorable weekday ({vara}).")
    elif vara in act_rules.get("neutral_varas", []):
        penalty = act_rules.get("neutral_vara_penalty", 0)
        if penalty < 0:
            score += penalty
            negatives.append(f"Neutral weekday ({vara}).")
        else:
            positives.append(f"Neutral weekday ({vara}).")
    else:
        penalty = act_rules.get("vara_penalty", -10)
        score += penalty
        negatives.append(f"Weekday ({vara}) is less optimal for soft/initiating ceremonies.")

    # Keep score between 0 and 100
    final_score = max(0.0, min(100.0, score))

    # Grade assignment
    if final_score >= 80.0:
        grade = "Excellent"
    elif final_score >= 60.0:
        grade = "Good"
    elif final_score >= 40.0:
        grade = "Average"
    else:
        grade = "Challenging"
        
    return {
        "activity": activity,
        "score": final_score,
        "grade": grade,
        "positives": positives,
        "negatives": negatives
    }

def get_all_muhurtas(panchang: dict) -> dict:
    activities = ["marriage", "griha_pravesh", "vehicle_purchase", "business_opening", "naming_ceremony", "travel", "investment"]
    results = {}
    for act in activities:
        results[act] = get_activity_muhurta(act, panchang)
    return results
