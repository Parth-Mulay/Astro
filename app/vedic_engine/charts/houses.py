RASHIS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

def calculate_shortest_midpoint(a: float, b: float) -> float:
    """Calculate the angular midpoint between two longitudes along the shortest arc."""
    diff = (b - a) % 360
    if diff > 180:
        return (a + (diff - 360) / 2) % 360
    return (a + diff / 2) % 360

def build_houses(lagna: float, mc: float, planets_sidereal: dict, system: str = "whole_sign") -> dict:
    """
    Distribute planets into 12 houses according to the selected house system.
    Supported systems:
    - 'whole_sign': Each house corresponds exactly to one zodiac sign, starting with Lagna's sign.
    - 'equal': Each house is 30 degrees wide, starting from the exact Lagna degree.
    - 'sripati': House cusps calculated using trisection of quadrants between Lagna and MC.
    - 'bhava_chalit': Same boundaries as Sripati, representing planetary placement in houses.
    """
    lagna_sign_idx = int(lagna // 30) % 12
    houses = {}
    
    # 1. Whole Sign House System (Default)
    if system == "whole_sign":
        for h in range(1, 13):
            sign_idx = (lagna_sign_idx + h - 1) % 12
            planets_here = []
            for p_name, p_data in planets_sidereal.items():
                p_sign_idx = int(p_data["sidereal"] // 30) % 12
                if p_sign_idx == sign_idx:
                    planets_here.append(p_name)
                    
            houses[str(h)] = {
                "sign": RASHIS[sign_idx],
                "rashi_num": sign_idx + 1,
                "planets": planets_here,
                "cusp": sign_idx * 30.0,
                "boundary_start": sign_idx * 30.0,
                "boundary_end": ((sign_idx + 1) * 30.0) % 360
            }
            
    # 2. Equal House System
    elif system == "equal":
        for h in range(1, 13):
            cusp = (lagna + (h - 1) * 30) % 360
            start_bound = cusp
            end_bound = (cusp + 30) % 360
            
            planets_here = []
            for p_name, p_data in planets_sidereal.items():
                p_sid = p_data["sidereal"]
                # Check if planet is within the 30-degree boundary
                in_house = False
                if start_bound <= end_bound:
                    in_house = start_bound <= p_sid < end_bound
                else: # wraps 360
                    in_house = p_sid >= start_bound or p_sid < end_bound
                if in_house:
                    planets_here.append(p_name)
                    
            sign_idx = int(cusp // 30) % 12
            houses[str(h)] = {
                "sign": RASHIS[sign_idx],
                "rashi_num": sign_idx + 1,
                "planets": planets_here,
                "cusp": cusp,
                "boundary_start": start_bound,
                "boundary_end": end_bound
            }
            
    # 3. Sripati House System & Bhava Chalit
    else: # 'sripati' or 'bhava_chalit'
        ic = (mc + 180) % 360
        descendant = (lagna + 180) % 360
        
        # Calculate cusps for houses 10, 11, 12, 1, 2, 3
        # Sector 1 (MC to Lagna): divided into 3 equal parts
        arc1 = (lagna - mc) % 360
        step1 = arc1 / 3.0
        cusps = {
            10: mc,
            11: (mc + step1) % 360,
            12: (mc + 2 * step1) % 360,
            1: lagna
        }
        
        # Sector 2 (Lagna to IC): divided into 3 equal parts
        arc2 = (ic - lagna) % 360
        step2 = arc2 / 3.0
        cusps[2] = (lagna + step2) % 360
        cusps[3] = (lagna + 2 * step2) % 360
        
        # Houses 4, 5, 6, 7, 8, 9 are 180 degrees opposite
        for h in range(4, 10):
            opposite_h = h + 6
            if opposite_h > 12:
                opposite_h -= 12
            cusps[h] = (cusps[opposite_h] + 180) % 360
            
        # Calculate boundaries (Bhava Sandhis) as the midpoints between adjacent cusps
        boundaries = {}
        for h in range(1, 13):
            next_h = h + 1 if h < 12 else 1
            midpoint = calculate_shortest_midpoint(cusps[h], cusps[next_h])
            boundaries[h] = midpoint # Boundary between h and h+1
            
        # Distribute planets into houses based on these boundaries
        # House h starts at boundaries[h-1] and ends at boundaries[h]
        for h in range(1, 13):
            prev_h = h - 1 if h > 1 else 12
            start_bound = boundaries[prev_h]
            end_bound = boundaries[h]
            
            planets_here = []
            for p_name, p_data in planets_sidereal.items():
                p_sid = p_data["sidereal"]
                in_house = False
                if start_bound <= end_bound:
                    in_house = start_bound <= p_sid < end_bound
                else: # wraps 360
                    in_house = p_sid >= start_bound or p_sid < end_bound
                if in_house:
                    planets_here.append(p_name)
                    
            cusp = cusps[h]
            sign_idx = int(cusp // 30) % 12
            
            houses[str(h)] = {
                "sign": RASHIS[sign_idx],
                "rashi_num": sign_idx + 1,
                "planets": planets_here,
                "cusp": cusp,
                "boundary_start": start_bound,
                "boundary_end": end_bound
            }
            
    return houses
