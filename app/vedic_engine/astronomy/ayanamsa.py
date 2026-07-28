import math

def calculate_lahiri_ayanamsa(tt_jd: float) -> float:
    """
    Calculate the Lahiri Ayanamsa (Chitra Paksha Ayanamsa) in degrees.
    T is Julian centuries since J2000.0 (JD 2451545.0)
    """
    T = (tt_jd - 2451545.0) / 36525.0
    return 23.853056 + 1.396971 * T + 0.0003086 * T**2

def calculate_surya_siddhanta_ayanamsa(tt_jd: float) -> float:
    """
    Calculate Surya Siddhanta Ayanamsa (trepidation/libration) in degrees.
    Epoch: Kali Yuga starts Feb 18, 3102 BC (JD 588465.5).
    Surya Siddhanta Year: 365.258756 days.
    Libration limits: -27 to +27 degrees with a 7200-year cycle.
    """
    years_since_kali_yuga = (tt_jd - 588465.5) / 365.258756
    # One cycle is 7200 years. So the angle is years * 360 / 7200.
    angle_rad = math.radians((years_since_kali_yuga) * 360.0 / 7200.0)
    # The amplitude of oscillation is 27 degrees.
    return 27.0 * math.sin(angle_rad)

def get_ayanamsa(tt_jd: float, mode: str = "modern") -> float:
    if mode == "traditional":
        return calculate_surya_siddhanta_ayanamsa(tt_jd)
    return calculate_lahiri_ayanamsa(tt_jd)
