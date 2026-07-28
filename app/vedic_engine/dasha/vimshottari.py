from datetime import datetime, timedelta

# Lord name, duration in years
DASHA_LORDS = [
    ("Ketu", 7),
    ("Venus", 20),
    ("Sun", 6),
    ("Moon", 10),
    ("Mars", 7),
    ("Rahu", 18),
    ("Jupiter", 16),
    ("Saturn", 19),
    ("Mercury", 17)
]

def add_years(start_date: datetime, years: float) -> datetime:
    """Helper to add decimal years to a datetime."""
    # Approximate leap years (365.25 days per year)
    days = years * 365.25
    return start_date + timedelta(days=days)

def calculate_vimshottari(moon_sid: float, birth_dt: datetime) -> list:
    """
    Calculate the Vimshottari Mahadasha, Antardasha, and Pratyantar Dasha tree.
    Returns:
      A list of Mahadashas with Antardashas and Pratyantardashas nested.
    """
    # 1. Determine starting Nakshatra (0-26)
    nak_idx = int(moon_sid // (360.0 / 27.0))
    nak_num = nak_idx + 1
    
    # 2. Determine starting dasha lord
    start_lord_idx = (nak_num - 1) % 9
    
    # 3. Calculate fraction remaining of first dasha
    deg_in_nak = moon_sid % (360.0 / 27.0)
    frac_passed = deg_in_nak / (360.0 / 27.0)
    frac_remaining = 1.0 - frac_passed
    
    current_start = birth_dt
    dasha_tree = []
    
    # 4. Compute 9 Mahadashas to cover 120 years
    for i in range(9):
        idx = (start_lord_idx + i) % 9
        lord, years = DASHA_LORDS[idx]
        
        # For the first dasha, apply the fractional duration remaining
        actual_years = years * frac_remaining if i == 0 else years
        current_end = add_years(current_start, actual_years)
        
        mahadasha = {
            "lord": lord,
            "start": current_start.strftime("%Y-%m-%d"),
            "end": current_end.strftime("%Y-%m-%d"),
            "antardashas": []
        }
        
        # Compute 9 Antardashas (Bhuktis)
        ant_start = current_start
        for j in range(9):
            ant_idx = (idx + j) % 9
            sub_lord, sub_years = DASHA_LORDS[ant_idx]
            
            # Antardasha duration = Mahadasha_duration * (sub_years / 120.0)
            ant_years = actual_years * (sub_years / 120.0)
            ant_end = add_years(ant_start, ant_years)
            
            antardasha = {
                "lord": sub_lord,
                "start": ant_start.strftime("%Y-%m-%d"),
                "end": ant_end.strftime("%Y-%m-%d"),
                "pratyantardashas": []
            }
            
            # Compute 9 Pratyantar Dashas
            prat_start = ant_start
            for k in range(9):
                prat_idx = (ant_idx + k) % 9
                prat_lord, prat_years = DASHA_LORDS[prat_idx]
                
                # Pratyantar dasha duration = Antardasha_duration * (prat_years / 120.0)
                prat_val_years = ant_years * (prat_years / 120.0)
                prat_end = add_years(prat_start, prat_val_years)
                
                antardasha["pratyantardashas"].append({
                    "lord": prat_lord,
                    "start": prat_start.strftime("%Y-%m-%d"),
                    "end": prat_end.strftime("%Y-%m-%d")
                })
                prat_start = prat_end
                
            mahadasha["antardashas"].append(antardasha)
            ant_start = ant_end
            
        dasha_tree.append(mahadasha)
        current_start = current_end
        
    return dasha_tree
