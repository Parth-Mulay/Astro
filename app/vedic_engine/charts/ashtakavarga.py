# Benefic offsets for each planet (1-based relative houses)
# 1 means same sign, 2 means next, ..., 12 means previous.
# Order of reference bodies: [Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Lagna]
ASHTAKAVARGA_RULES = {
    "Sun": {
        "Sun": [1, 2, 4, 7, 8, 9, 10, 11],
        "Moon": [3, 6, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11],
        "Venus": [6, 7, 12],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna": [3, 4, 6, 10, 11, 12]
    },
    "Moon": {
        "Sun": [3, 6, 7, 8, 10, 11],
        "Moon": [1, 3, 6, 7, 10, 11],
        "Mars": [2, 3, 5, 6, 9, 10, 11],
        "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 4, 7, 8, 10, 11, 12],
        "Venus": [3, 4, 5, 7, 9, 10, 11],
        "Saturn": [3, 5, 6, 11],
        "Lagna": [3, 6, 10, 11]
    },
    "Mars": {
        "Sun": [3, 5, 6, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12],
        "Venus": [6, 8, 11, 12],
        "Saturn": [1, 4, 7, 8, 9, 10, 11],
        "Lagna": [1, 3, 6, 10, 11]
    },
    "Mercury": {
        "Sun": [5, 6, 9, 11, 12],
        "Moon": [2, 4, 6, 8, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna": [1, 2, 4, 6, 8, 10, 11]
    },
    "Jupiter": {
        "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "Moon": [2, 5, 7, 9, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
        "Venus": [2, 5, 6, 9, 10, 11],
        "Saturn": [3, 5, 6, 12],
        "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11]
    },
    "Venus": {
        "Sun": [8, 11, 12],
        "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars": [3, 5, 6, 9, 11, 12],
        "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn": [3, 4, 5, 8, 9, 10, 11],
        "Lagna": [1, 2, 3, 4, 5, 8, 9, 11]
    },
    "Saturn": {
        "Sun": [1, 2, 4, 7, 8, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [3, 5, 6, 10, 11, 12],
        "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12],
        "Venus": [6, 11, 12],
        "Saturn": [3, 5, 6, 11],
        "Lagna": [1, 3, 4, 6, 10, 11]
    }
}

ORDER_OF_BODIES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

def calculate_ashtakavarga(planets_sidereal: dict, lagna_sidereal: float) -> dict:
    """
    Calculate Bhinna Ashtakavarga (BAV) for the 7 classical planets
    and the Sarvashtakavarga (SAV) totals for the 12 signs/houses.
    Returns:
      {
        "bav": { "Sun": [points for sign 1-12], ... },
        "sav": [points for sign 1-12 (sum of BAVs)]
      }
    """
    # 1. Map sign placements (0-11) for all 8 reference bodies
    placements = {}
    for p_name in ORDER_OF_BODIES:
        placements[p_name] = int(planets_sidereal[p_name]["sidereal"] // 30) % 12
    placements["Lagna"] = int(lagna_sidereal // 30) % 12
    
    bav_data = {}
    sav_totals = [0] * 12
    
    # 2. Compute BAV for each of the 7 planets
    for p_name, rules in ASHTAKAVARGA_RULES.items():
        bav_points = [0] * 12
        
        # Check target signs (0 to 11)
        for target_sign in range(12):
            # Check contributions from each reference body
            for ref_name, benefic_houses in rules.items():
                ref_sign = placements[ref_name]
                # Calculate relative house (1-indexed)
                rel_house = (target_sign - ref_sign) % 12 + 1
                if rel_house in benefic_houses:
                    bav_points[target_sign] += 1
                    
        bav_data[p_name] = bav_points
        
        # Add to SAV totals
        for i in range(12):
            sav_totals[i] += bav_points[i]
            
    return {
        "bav": bav_data,
        "sav": sav_totals
    }
