from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from app.vedic_engine.astronomy.coords import get_planetary_positions

ZODIAC = [
    ("aries", "Aries", "♈"),
    ("taurus", "Taurus", "♉"),
    ("gemini", "Gemini", "♊"),
    ("cancer", "Cancer", "♋"),
    ("leo", "Leo", "♌"),
    ("virgo", "Virgo", "♍"),
    ("libra", "Libra", "♎"),
    ("scorpio", "Scorpio", "♏"),
    ("sagittarius", "Sagittarius", "♐"),
    ("capricorn", "Capricorn", "♑"),
    ("aquarius", "Aquarius", "♒"),
    ("pisces", "Pisces", "♓"),
]

ZODIAC_RASHI_MAP = {
    "aries": 0,
    "taurus": 1,
    "gemini": 2,
    "cancer": 3,
    "leo": 4,
    "virgo": 5,
    "libra": 6,
    "scorpio": 7,
    "sagittarius": 8,
    "capricorn": 9,
    "aquarius": 10,
    "pisces": 11,
}

RASHI_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

JUPITER_TRANSITS = {
    1: "With the benevolent Jupiter transiting your 1st house (Ascendant), you are embarking on a powerful phase of personal growth and self-renewal. Your confidence and optimism will be naturally high, drawing positive opportunities and helpful people toward you. This is an excellent day to start new projects, invest in self-improvement, and let your natural leadership shine.",
    2: "Jupiter transiting your 2nd house of wealth and family brings a highly favorable period for financial planning, family gatherings, and security. You may experience a sudden boost in your income or receive unexpected support from relatives. It is a wonderful day to resolve family matters and enjoy warm conversations over a meal.",
    3: "With Jupiter moving through your 3rd house, travel, short distance journeys, and communication are highlighted. Your courage and intellectual stamina are enhanced. Creative ideas flow easily, and networking with siblings, neighbors, or close friends will yield exciting and beneficial plans for the future.",
    4: "Jupiter's transit through your 4th house brings harmony and contentment to your domestic sphere. You may feel inspired to renovate your home or purchase household luxury items. Mother's advice or support will prove highly valuable today. Focus on emotional security and creating a peaceful sanctuary.",
    5: "The auspicious Jupiter in your 5th house of intellect, children, and romance lights up your creative spark. Love relationships will thrive with mutual warmth and understanding. If you are seeking to learn a new skill, write, or engage in speculation, the cosmic energies are highly supportive. Children will bring joy.",
    6: "Jupiter transiting your 6th house of health and service brings victory over rivals and a successful resolution to pending disputes. You will excel in your daily work routines. Any minor health concerns can be treated effectively today. It is a great time to organize your workplace and offer help to others.",
    7: "With Jupiter in your 7th house of partnerships, marital bonds and business collaborations are highly favored. There is a sense of mutual respect and harmony in your interactions. If you are negotiating a contract or seeking a partner, today's transit offers excellent prospects for success.",
    8: "Jupiter's transit in the 8th house stimulates deep research, interest in spiritual subjects, and sudden gains from inheritances or partner's finances. You are guided to look beneath the surface of things. Trust your intuition and use this energy to resolve pending financial or tax matters.",
    9: "With the expansive Jupiter in your 9th house of fortune, luck favors your endeavors. Spiritual practices, long-distance journeys, and interactions with mentors or father figures are highly beneficial. You feel a strong pull toward higher wisdom and philosophy. Luck score is exceptionally strong.",
    10: "Jupiter transiting your 10th house of career brings professional advancement, honor, and recognition. Your relationship with superiors or clients is highly positive. A promotion, a new project, or a positive career shift is on the horizon. Trust your execution and display your expertise.",
    11: "Jupiter in your 11th house of gains and wishes is one of the most auspicious transits. Your social circle expands, and friends will offer meaningful support. Incoming profits from multiple sources are indicated. This is a day for wish-fulfillment and planning long-term ambitions.",
    12: "With Jupiter in your 12th house, you are encouraged to seek solitude, engage in charity, and focus on inner spiritual growth. Expenditure on altruistic causes or travel brings peace of mind. Dreams could be vivid and highly intuitive. Prioritize rest and self-care."
}

SUN_TRANSITS = {
    1: "The Sun transiting your 1st house places you in the spotlight. You will feel a strong urge to assert your authority and lead. Superiors will take notice of your energy. Focus on professional discipline and avoid excessive pride.",
    2: "The Sun in your 2nd house highlights financial transactions and core values. It is a day to negotiate contracts, check budgets, and plan resource allocation. Speak clearly but avoid bluntness with clients.",
    3: "With the Sun transiting your 3rd house, your communication skills are sharp and persuasive. Short trips, meetings, and presentations are favored. Your active approach will help you clear pending tasks quickly.",
    4: "The Sun in your 4th house directs your focus to domestic stability and internal work structures. Professional responsibilities might require you to work from home or address workplace foundations. Maintain work-life balance.",
    5: "The Sun's transit through your 5th house brings creative energy and a desire for recognition in your work. Speculative projects, creative design, and presentations are favored. Showcase your talents with confidence.",
    6: "The Sun in your 6th house is an excellent placement for resolving workspace bottlenecks, managing logistics, and defeating competition. Your focus on detail is unmatched today. Complete tasks with precision.",
    7: "With the Sun in your 7th house, professional partnerships and contracts are in focus. Collaborative efforts are key. Listen to partner feedback and align on shared business goals to ensure progress.",
    8: "The Sun transiting your 8th house suggests a day for deep investigation, tax audits, or hidden resource management. Avoid risky investments. Focus on research and strategic plotting behind the scenes.",
    9: "The Sun in your 9th house brings clarity, optimism, and support from mentors. Publishing, research, legal affairs, and international relations are highly favored. Share your long-term vision.",
    10: "The Sun in your 10th house is the peak of professional authority (Dig Bala). Your leadership skills are highly respected. New responsibilities, promotions, or interactions with key executives are highly favored.",
    11: "The Sun transiting your 11th house of gains ensures a successful day for group projects and financial returns. Your efforts receive public appreciation. Leverage your network to advance your goals.",
    12: "The Sun in your 12th house suggests a day to work behind the scenes or complete pending administrative tasks. Focus on strategy, planning, and preparing for future launches. Avoid public confrontations."
}

VENUS_TRANSITS = {
    1: "Venus transiting your 1st house enhances your personal charm and attractiveness. Love and social connections are naturally drawn to you. It is a wonderful day to refresh your appearance, express affection, and enjoy a romantic outing.",
    2: "Venus in your 2nd house brings harmony to family relationships and financial discussions. Your speech is sweet and comforting. Expressing gratitude to your partner or family builds deep, lasting harmony.",
    3: "With Venus transiting your 3rd house, short romantic getaways, loving text messages, and creative communications are favored. Expressing your feelings in writing or through artistic medium will bring joy to your loved ones.",
    4: "Venus in your 4th house fills your home with peace, luxury, and warm emotions. It is a perfect day for family gatherings, home decoration, or cooking a special meal with your partner. Domestic bliss is highlighted.",
    5: "Venus transiting your 5th house of romance and intellect brings vibrant romantic energy. Love is playful, passionate, and deeply fulfilling. Creative projects, entertainment, and sharing hobbies with your partner are highly favored.",
    6: "Venus in the 6th house suggests standard daily tasks require a gentle touch. Focus on service, small compromises, and mutual support in relationships. Avoid letting minor disagreements escalate into arguments.",
    7: "With Venus in your 7th house of relationships, marital harmony and partnership bonds are exceptionally strong. You feel a deep connection with your partner. Sharing quality time and alignment of future plans brings joy.",
    8: "Venus transiting your 8th house deepens emotional intimacy and secrets in relationships. It is a day to share your deepest thoughts and build trust. Unexpected gifts or emotional breakthroughs are possible.",
    9: "Venus in your 9th house links love with spiritual search or travel. Sharing philosophical discussions, learning together, or traveling with your partner will enrich your bond and bring mutual joy.",
    10: "Venus in your 10th house brings harmony and pleasant interactions to your professional relationships. Your social skills help you build positive rapport. Balance professional demands with personal life.",
    11: "Venus transiting your 11th house of gains brings active social interactions and joy. You will enjoy spending time with friends and loved ones. Social gatherings and network collaborations bring pleasant moments.",
    12: "Venus in your 12th house suggests a quiet, private day for love and reflection. Enjoying cozy, private moments with your partner or practicing self-love in solitude will recharge your emotional battery."
}

WEEKLY_THEMES = [
    "Your weekly chart points toward expansion. Jupiter's aspect on your career sector promises new pathways. A mid-week conversation with a senior colleague could trigger a highly profitable idea. Maintain strict discipline over your spendings and secure your boundaries.",
    "A strong concentration of positive planetary transits in your creative houses opens doors to love and self-expression this week. Your communication style is both direct and charming. Be prepared for a significant breakthrough in ongoing partnership negotiations.",
    "The alignment of Venus and Mercury this week enhances your capacity to build harmony at home. Financial planning yields positive results, helping you manage unexpected expenses. Take some time mid-week for spiritual practices or writing down your goals.",
]

MONTHLY_THEMES = [
    "This month marks a defining transition as Mars enters a strong angle relative to your sun sign. Your drive and work ethic are highly pronounced, allowing you to wrap up long-term projects. Emotional healing in close relationships brings stability and trust.",
    "A favorable lunar cycle brings financial clarity and growth. Professional status rises as your efforts receive public appreciation. Focus on maintaining a healthy diet and establishing a consistent workout routine to keep your energy high.",
]

YEARLY_THEMES = [
    "A powerful year of consolidation and structural development. With major planetary shifts supporting your professional houses, study, skill advancement, and network building are highly favored. Choosing your allies wisely will yield significant benefits.",
    "This year highlights new beginnings, potential relocation, or educational achievements. Your creative energy is at its peak. Ensure regular spiritual discipline and keep clear budgets to anchor your rapid progress.",
]

def _seed(sign: str, period: str, anchor: date) -> int:
    raw = f"{sign}:{period}:{anchor.isoformat()}".encode()
    return int(hashlib.md5(raw).hexdigest(), 16)

def sun_sign_from_dob(dob: date) -> str:
    md = dob.month * 100 + dob.day
    if 321 <= md <= 419:
        return "aries"
    if 420 <= md <= 520:
        return "taurus"
    if 521 <= md <= 620:
        return "gemini"
    if 621 <= md <= 722:
        return "cancer"
    if 723 <= md <= 822:
        return "leo"
    if 823 <= md <= 922:
        return "virgo"
    if 923 <= md <= 1022:
        return "libra"
    if 1023 <= md <= 1121:
        return "scorpio"
    if 1122 <= md <= 1221:
        return "sagittarius"
    if md >= 1222 or md <= 119:
        return "capricorn"
    if 120 <= md <= 218:
        return "aquarius"
    return "pisces"

def get_horoscope(sign: str, period: str, on_date: date | None = None) -> dict:
    on_date = on_date or date.today()
    sign = sign.lower()
    z = next((z for z in ZODIAC if z[0] == sign), ZODIAC[0])
    sign_rashi_idx = ZODIAC_RASHI_MAP.get(z[0], 0)

    if period == "daily":
        anchor = on_date
        
        # 1. Fetch real planetary transit positions dynamically using Skyfield
        try:
            dt_noon = datetime(on_date.year, on_date.month, on_date.day, 12, 0, 0)
            transit_data = get_planetary_positions(dt_noon, 28.6139, 77.2090)
            
            # Helper to calculate relative house position of a transiting planet
            def get_house(planet_name: str) -> int:
                p_long = transit_data["planets"][planet_name]["sidereal"]
                p_rashi_idx = int(p_long // 30) % 12
                return (p_rashi_idx - sign_rashi_idx) % 12 + 1
            
            # Fetch houses
            jup_house = get_house("Jupiter")
            sun_house = get_house("Sun")
            ven_house = get_house("Venus")
            mars_house = get_house("Mars")
            mer_house = get_house("Mercury")
            moon_house = get_house("Moon")
            sat_house = get_house("Saturn")
            
            # 2. Build detailed predictions
            prediction = JUPITER_TRANSITS.get(jup_house, JUPITER_TRANSITS[1])
            love = VENUS_TRANSITS.get(ven_house, VENUS_TRANSITS[1])
            career = SUN_TRANSITS.get(sun_house, SUN_TRANSITS[1])
            
            # Health description based on Mars and Saturn transits
            if mars_house in [3, 6, 11] and sat_house in [3, 6, 11]:
                health = "With both Mars and Saturn transiting highly supportive houses relative to your sign, your physical vitality and immune system are exceptionally strong. Your energy levels are high, and you possess the stamina to complete challenging tasks. Outdoor activities and workouts are highly beneficial."
            elif mars_house in [1, 2, 4, 7, 8, 12] or sat_house in [1, 2, 4, 7, 8, 12]:
                health = "Mars or Saturn transiting your sign's sensitive houses indicates high energy but calls for caution. Channel your physical drive into structured exercise to prevent restlessness. Avoid rash physical movements, watch your diet (cool down with water), and prioritize good sleep to manage stress."
            else:
                health = "Your physical health is stable, but your mind is highly active. Regular physical breaks from intellectual work, stretching, and staying hydrated will maintain consistent stamina throughout the day."
                
            # Dynamic luck score based on Moon's transit relative to sign (Moon in 1,3,6,7,10,11 is favorable)
            if moon_house in [1, 3, 6, 7, 10, 11]:
                luck = 80 + (_seed(sign, "luck", anchor) % 16) # 80 to 95%
            else:
                luck = 60 + (_seed(sign, "luck", anchor) % 20) # 60 to 79%
                
        except Exception as e:
            # Fallback in case of calculation errors
            import logging
            logging.getLogger("application").error(f"Error calculating transit horoscope: {e}")
            prediction = "Creative ideas flow; share them with a trusted mentor or partner."
            love = "Family matters need patience; small gestures build harmony."
            career = "Travel or learning plans gain momentum; stay flexible with timing."
            health = "Moderate energy—prioritize rest if stressed."
            luck = 60 + (_seed(sign, "luck", anchor) % 41)

    else:
        # Weekly, Monthly, Yearly themes selection
        if period == "weekly":
            anchor = on_date - timedelta(days=on_date.weekday())
            pool = WEEKLY_THEMES
        elif period == "monthly":
            anchor = on_date.replace(day=1)
            pool = MONTHLY_THEMES
        else:
            anchor = on_date.replace(month=1, day=1)
            pool = YEARLY_THEMES

        idx = _seed(sign, period, anchor) % len(pool)
        luck = 60 + (_seed(sign, period + "luck", anchor) % 41)
        prediction = pool[idx]
        love = pool[(idx + 1) % len(pool)]
        career = pool[(idx + 2) % len(pool)]
        health = "Moderate energy—prioritize rest if stressed."

    return {
        "sign_slug": z[0],
        "sign_name": z[1],
        "symbol": z[2],
        "period": period,
        "date_label": anchor.strftime("%d %b %Y"),
        "prediction": prediction,
        "luck_score": luck,
        "love": love,
        "career": career,
        "health": health,
    }
