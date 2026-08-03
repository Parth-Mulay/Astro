from pathlib import Path
from fastapi.templating import Jinja2Templates
import re
import secrets
from app.settings import settings

APP_DIR = Path(__file__).resolve().parent.parent

class CSRFJinja2Templates(Jinja2Templates):
    def TemplateResponse(
        self,
        request,
        name: str,
        context: dict = None,
        *args,
        **kwargs
    ):
        if context is None:
            context = {}
        context["request"] = request
        
        response = super().TemplateResponse(request, name, context, *args, **kwargs)
        
        cookie_token = getattr(request.state, "csrf_token", None)
        generated_token = None
        if not cookie_token:
            cookie_token = request.cookies.get("csrf_token")
            if not cookie_token:
                generated_token = secrets.token_urlsafe(32)
                cookie_token = generated_token
            
        try:
            body_content = response.body.decode("utf-8")
            
            def form_replacer(match):
                form_tag = match.group(1)
                next_500 = body_content[match.start():match.start()+500]
                if 'name="csrf_token"' in form_tag or 'name="csrf_token"' in next_500:
                    return form_tag
                return f'{form_tag}<input type="hidden" name="csrf_token" value="{cookie_token}">'
                
            body_content = re.sub(
                r'(<form[^>]*method=["\']post["\'][^>]*>)',
                form_replacer,
                body_content,
                flags=re.IGNORECASE
            )
            
            response.body = body_content.encode("utf-8")
            response.headers["content-length"] = str(len(response.body))
            
            if generated_token:
                response.set_cookie(
                    "csrf_token",
                    generated_token,
                    httponly=True,
                    secure=settings.SECURE_COOKIES,
                    samesite="lax"
                )
        except Exception as e:
            import logging
            logging.getLogger("application").error(f"Error injecting CSRF token in templates: {e}")
            
        return response

templates = CSRFJinja2Templates(directory=APP_DIR / "templates")

TRANSLATIONS = {
    "en": {
        "home": "Home",
        "horoscope": "Horoscope",
        "free_kundli": "Free Kundli",
        "kundli_matching": "Kundli Matching",
        "panchang": "Panchang",
        "astrologers": "Astrologers",
        "talk_to_astrologer": "Talk to Astrologer",
        "smart_match": "Smart Match",
        "wallet": "Wallet",
        "recharge": "Recharge",
        "my_account": "My Account",
        "logout": "Logout",
        "sign_in": "Sign In",
        "sign_up": "Sign Up",
        "services": "Services",
        "daily_kundli": "Daily Kundli",
        
        # Planets
        "sun": "Sun",
        "moon": "Moon",
        "mars": "Mars",
        "mercury": "Mercury",
        "jupiter": "Jupiter",
        "venus": "Venus",
        "saturn": "Saturn",
        "rahu": "Rahu",
        "ketu": "Ketu",
        
        # Signs
        "aries": "Aries",
        "taurus": "Taurus",
        "gemini": "Gemini",
        "cancer": "Cancer",
        "leo": "Leo",
        "virgo": "Virgo",
        "libra": "Libra",
        "scorpio": "Scorpio",
        "sagittarius": "Sagittarius",
        "capricorn": "Capricorn",
        "aquarius": "Aquarius",
        "pisces": "Pisces",

        # Form / Fields
        "name": "Name",
        "dob": "Date of Birth",
        "birth_time": "Time of Birth",
        "birth_place": "Place of Birth",
        "generate": "Generate Kundli",
        "match_now": "Match Now",
        "boy_details": "Boy's Details",
        "girl_details": "Girl's Details",
        "boy_name": "Boy's Name",
        "girl_name": "Girl's Name",
        "enter_details": "Enter birth details",

        # Details
        "lagna": "Lagna",
        "nakshatra": "Nakshatra",
        "sun_sign": "Sun Sign",
        "moon_sign": "Moon Sign",
        "place": "Place",
        "time": "Time",
        "date": "Date",

        # Panchang terms
        "tithi": "Tithi",
        "nakshatra_panchang": "Nakshatra",
        "yoga": "Yoga",
        "karana": "Karana",
        "rahu_kaal": "Rahu Kaal",
        "gulika_kaal": "Gulika Kaal",
        "yamaganda": "Yamaganda",
        "sunrise": "Sunrise",
        "sunset": "Sunset",
        "panchang_for": "Panchang for",
        "today_panchang": "Today's Panchang",
        "city": "City",
        "update": "Update",
        
        # Suggestions and labels
        "buying_new_home": "Buying New Home",
        "relationships_&_love": "Relationships & Love",
        "career_/_job": "Career / Job",
        "wealth_&_finance": "Wealth & Finance",
        "how_to_choose_best_time_to_buy_home_or_flat": "How to choose best time to buy home or flat",
        "suggest_love_marriage_relationship_advice": "Suggest love marriage relationship advice",
        "will_i_get_career_growth_or_promotion": "Will I get career growth or promotion",
        "how_to_strengthen_wealth_and_income": "How to strengthen wealth and income",
        
        # Service page descriptions
        "daily_horoscope_desc": "Get your detailed daily, weekly, monthly, and yearly predictions.",
        "free_kundli_desc": "Generate your Vedic birth chart (Kundli) with 12 houses and planetary details.",
        "kundli_matching_desc": "Check horoscope compatibility (Gun Milan score %) for marriage.",
        "panchang_desc": "Check daily auspicious times, tithi, nakshatra, and Rahu Kaal.",
        "astrologers_desc": "Talk to verified expert astrologers for career, love, health, and marriage advice.",
        "tarot_desc": "Draw 3 cards to get guidance on your past, present, and future.",
        "remedies_desc": "Find simple Lal Kitab remedies and solutions for your life problems.",

        # Remedies / General UI
        "concern": "Concern",
        "general": "General",
        "marriage": "Love / Marriage",
        "finance": "Finance",
        "lal_kitab_&_vedic_remedies": "Lal Kitab & Vedic Remedies",
        "general_guidance_—_for_personalized_remedies,_consult_a_matched_astrologer.": "General guidance — for personalized remedies, consult a matched astrologer.",
        "get_matched_astrologer": "Get Matched Astrologer",
        
        # Astrologer Details
        "verified": "Verified",
        "yrs": "yrs",
        "chat": "Chat",
        "call": "Call",
        "new": "New",
        "verified_specialists": "Verified specialists — use Smart Match for problem-based top 3 recommendations.",
        "smart_match_top_3": "Smart Match — Top 3 for my issue",
        "consult_expert_astrologers": "Consult Expert Astrologers",
        "verified_specialists_intro": "Verified specialists — ranked by your issue, language, budget & availability (like AstroSage, but problem-first).",
        
        # Remedies Content
        "mantra": "Mantra",
        "charity": "Charity",
        "gemstone": "Gemstone",
        "relationship": "Relationship",
        "offer_water_to_the_sun_at_sunrise;_avoid_lending_on_tuesdays.": "Offer water to the Sun at sunrise; avoid lending on Tuesdays.",
        "chant_om_namah_shivaya_108_times_on_mondays.": "Chant Om Namah Shivaya 108 times on Mondays.",
        "donate_food_grains_on_thursdays_for_jupiter_strength.": "Donate food grains on Thursdays for Jupiter strength.",
        "consult_a_verified_astrologer_before_wearing_any_stone.": "Consult a verified astrologer before wearing any stone.",
        "light_a_ghee_diya_in_the_southwest_corner_on_fridays.": "Light a ghee diya in the southwest corner on Fridays.",

        # Horoscope / Timings
        "daily": "Daily",
        "weekly": "Weekly",
        "monthly": "Monthly",
        "yearly": "Yearly",
        "luck_score": "Luck score",
        "love": "Love",
        "career": "Career",
        "health": "Health",
        "choose_your_sign": "Choose your sign",
        "result": "Result",
        "new_kundli": "New Kundli",
        "my_saved_charts": "My Saved Charts",
        "new_match": "New Match",
        "view_remedies": "View Remedies",
        "talk_to_marriage_specialist": "Talk to Marriage Specialist",
        "boy": "Boy",
        "girl": "Girl",
        "birth_chart_lagna": "Birth Chart (Lagna)",
        "planetary_positions": "Planetary Positions",
        "birth_charts_comparison": "Birth Charts Comparison",
        "kundli_matching_result": "Kundli Matching Result",
        "mangal_dosha": "Mangal Dosha",
        "gunas": "Gunas",
        "nadi": "Nadi",
        "bhakoot": "Bhakoot",
        "transit_kundli_gochar": "Transit Kundli (Gochar)",
        "today_panchang_gochar_kundli": "Today's Panchang & Gochar Kundli",
        "real_time_planetary_transits": "Real-time planetary transits and auspicious daily timings.",
        "view_detailed_panchang": "View Detailed Panchang",
        "scroll_to_browse": "Scroll to browse · Book via Smart Match for personalized top 3",
        "start_smart_match": "Start Smart Match",
        "pick_problem_category": "Pick problem category",
        "short_intake": "Short intake (language, budget, urgency)",
        "get_top_3_with_match_score": "Get top 3 with match score & reasons",
        "book_chat_or_call": "Book chat or call",
        "rate_session": "Rate session — system learns",
        "start_intake_now": "Start intake now",
        "sign_in_to_start": "Sign in to start",
        "popular_concerns": "Popular concerns",

        # Horoscope themes
        "focus_on_steady_progress_at_work;_avoid_impulsive_decisions_before_noon.": "Focus on steady progress at work; avoid impulsive decisions before noon.",
        "relationships_improve when you listen more than you speak today.": "Relationships improve when you listen more than you speak today.",
        "a_financial_opportunity_may_appear—verify_details_before_committing.": "A financial opportunity may appear—verify details before committing.",
        "health_and_routine_matter;_short_walks_and_hydration_help_your_energy.": "Health and routine matter; short walks and hydration help your energy.",
        "creative_ideas_flow;_share_them_with_a_trusted_mentor_or_partner.": "Creative ideas flow; share them with a trusted mentor or partner.",
        "family_matters_need_patience;_small_gestures_build_harmony.": "Family matters need patience; small gestures build harmony.",
        "travel_or_learning_plans_gain_momentum;_stay_flexible_with_timing.": "Travel or learning plans gain momentum; stay flexible with timing.",
        "property_or_long-term_investments_favor_research_over_speed_today.": "Property or long-term investments favor research over speed today.",
        "career_visibility_increases_mid-week;_prepare_for_important_conversations.": "Career visibility increases mid-week; prepare for important conversations.",
        "love_life_stabilizes_when_you_express_needs_clearly_and_kindly.": "Love life stabilizes when you express needs clearly and kindly.",
        "budget_discipline_pays_off;_unexpected_expenses_are_manageable.": "Budget discipline pays off; unexpected expenses are manageable.",
        "spiritual_practice_or_meditation_supports_clarity_on_a_major_choice.": "Spiritual practice or meditation supports clarity on a major choice.",
        "this_month_favors_structured_goals_in_career_and_education.": "This month favors structured goals in career and education.",
        "emotional_healing_in_relationships_opens_space_for_deeper_trust.": "Emotional healing in relationships opens space for deeper trust.",
        "financial_planning_and_debt_reduction_bring_long-term_relief.": "Financial planning and debt reduction bring long-term relief.",
        "health_routines_started_now_can_become_sustainable_habits.": "Health routines started now can become sustainable habits.",
        "a_year_of_consolidation:_build_skills,_savings,_and_supportive_networks.": "A year of consolidation: build skills, savings, and supportive networks.",
        "partnerships_and_collaborations_define_success—choose_allies_wisely.": "Partnerships and collaborations define success—choose allies wisely.",
        "relocation,_study_abroad,_or_new_roles_may_appear_in_the_second_half.": "Relocation, study abroad, or new roles may appear in the second half.",
        "remedies_and_disciplined_spiritual_practice_amplify_positive_outcomes.": "Remedies and disciplined spiritual practice amplify positive outcomes.",
        "moderate_energy—prioritize_rest_if_stressed.": "Moderate energy—prioritize rest if stressed."
    },
    "hi": {
        # Login and Signup portal translations
        "sign_in": "साइन इन करें",
        "sign_up": "साइन अप करें",
        "join_astromatch": "एस्ट्रोमैच में शामिल हों",
        "select_your_profile_type_to_register_and_get_started.": "पंजीकरण करने और शुरू करने के लिए अपने प्रोफ़ाइल प्रकार का चयन करें।",
        "seek_guidance_(client)": "मार्गदर्शन प्राप्त करें (क्लाइंट)",
        "provide_guidance_(jyotishi)": "मार्गदर्शन प्रदान करें (ज्योतिषी)",
        "email_address": "ईमेल पता",
        "name@example.com": "name@example.com",
        "password": "पासवर्ड",
        "at_least_6_characters": "कम से कम 6 वर्ण",
        "sign_up_—_get_500_welcome_credits": "साइन अप करें — 500 स्वागत क्रेडिट प्राप्त करें",
        "public_display_name": "सार्वजनिक नाम",
        "e.g._acharya_sharma": "जैसे, आचार्य शर्मा",
        "years_of_experience": "अनुभव के वर्ष",
        "primary_language": "प्राथमिक भाषा",
        "e.g._hindi,_english": "जैसे, हिंदी, अंग्रेजी",
        "consultation_rate_(credits_/_session)": "परामर्श दर (क्रेडिट / सत्र)",
        "short_bio_/_qualifications": "संक्षिप्त विवरण / योग्यताएं",
        "briefly_describe_your_specialization,_line_of_lineage,_or_certifications.": "अपनी विशेषज्ञता, वंश या प्रमाणपत्रों का संक्षेप में वर्णन करें।",
        "register_as_jyotishi": "ज्योतिषी के रूप में पंजीकरण करें",
        "already_have_an_account?": "पहले से ही एक खाता है?",
        "sign_in_here": "यहाँ साइन इन करें",
        "sign_in_portal": "साइन इन पोर्टल",
        "choose your portal to sign in.": "साइन इन करने के लिए अपना पोर्टल चुनें।",
        "choose_your_portal_to_sign_in.": "साइन इन करने के लिए अपना पोर्टल चुनें।",
        "client_login": "क्लाइंट लॉगिन",
        "jyotishi_login": "ज्योतिषी लॉगिन",
        "enter_password": "पासवर्ड दर्ज करें",
        "sign_in_as_client": "क्लाइंट के रूप में साइन इन करें",
        "sign_in_as_jyotishi": "ज्योतिषी के रूप में साइन इन करें",
        "new_user?": "नए उपयोगकर्ता?",
        "sign_up_here": "यहाँ साइन अप करें",

        # Divisional Charts, Gochar, Eclipses translations
        "select_chart": "चार्ट चुनें",
        "birth_chart_(d1)": "जन्म कुंडली (D1)",
        "birth_chart_d1": "जन्म कुंडली (D1)",
        "navamsa_chart_(d9)": "नवांश कुंडली (D9)",
        "navamsa_chart_d9": "नवांश कुंडली (D9)",
        "dasamsa_chart_(d10)": "दशमांश कुंडली (D10)",
        "dasamsa_chart_d10": "दशमांश कुंडली (D10)",
        "click_on_any_mahadasha_to_view_its_antardasha_periods.": "इसके अंतर्दशा काल को देखने के लिए किसी भी महादशा पर क्लिक करें।",
        "real-time_gochar_placements": "वास्तविक समय गोचर स्थिति",
        "planet": "ग्रह",
        "transit_sign": "गोचर राशि",
        "house_(from_moon)": "भाव (चन्द्र से)",
        "house_(from_lagna)": "भाव (लग्न से)",
        "transit_vedic_aspects": "गोचर वैदिक दृष्टि",
        "gochar_(transit)": "गोचर (ट्रांजिट)",
        "eclipse_type": "ग्रहण का प्रकार",
        "magnitude": "तीव्रता",
        "no_primary_transit_aspects_on_natal_chart_at_this_moment.": "इस समय जन्म कुंडली पर कोई प्राथमिक गोचर दृष्टि नहीं है।",

        # Homepage Lower Section translations
        "vedic_astrology_services": "वैदिक ज्योतिष सेवाएं",
        "detailed_horoscope": "विस्तृत राशिफल",
        "daily_panchang": "दैनिक पंचांग",
        "ask_me_(consult)": "मुझसे पूछें (परामर्श)",
        "why_astromatch_(authentic_jyotish_guidance)": "एस्ट्रोमैच क्यों (सच्चा ज्योतिषीय मार्गदर्शन)",
        "aligning_destinies": "भाग्य संरेखण",
        "structured_background_details": "संरचित पृष्ठभूमि विवरण",
        "astrologers_get_full_details_before_starting_chat": "चैट शुरू करने से पहले ज्योतिषियों को पूरा विवरण मिलता है",
        "specialty-based_recommendation": "विशेषता-आधारित अनुशंसा",
        "specialty,_language,_rating,_budget…": "विशेषता, भाषा, रेटिंग, बजट…",
        "credit_points_system": "क्रेडिट पॉइंट प्रणाली",
        "simple,_transparent_credit_usage_for_consultations_&_premium_features": "परामर्श और प्रीमियम सुविधाओं के लिए सरल, पारदर्शी क्रेडिट उपयोग",
        "direct_interaction": "सीधा संवाद",
        "no_automated_bot_answers,_direct_chat_with_qualified_jyotishis": "कोई स्वचालित बॉट उत्तर नहीं, योग्य ज्योतिषियों के साथ सीधी चैट",

        # Services Page translations
        "explore_our_comprehensive_vedic_astrology_services_and_tools.": "हमारे व्यापक वैदिक ज्योतिष सेवाओं और उपकरणों का अन्वेषण करें।",
        "view_a_detailed_sample_birth_chart_demonstrating_lagna_rashi,_planetary_transits,_and_vimshottari_dashas.": "लग्न राशि, ग्रह गोचर और विंशोत्तरी दशा को दर्शाने वाला एक विस्तृत नमूना जन्म चार्ट देखें।",
        "costs_50_credits": "लागत 50 क्रेडिट",
        "view_sample_chart": "सैंपल चार्ट देखें",
        "read_detailed_rashi_bhavishya_daily,_weekly,_monthly,_and_yearly_reports_calculated_by_planetary_positions.": "ग्रहों की स्थिति द्वारा गणना की गई दैनिक, साप्ताहिक, मासिक और वार्षिक विस्तृत राशि भविष्य रिपोर्ट पढ़ें।",
        "costs_20_credits": "लागत 20 क्रेडिट",
        "read_horoscope": "राशिफल पढ़ें",
        "check_panchang": "पंचांग जांचें",
        "browse_astrologers": "ज्योतिषियों को ब्राउज़ करें",
        "match_to_the_top_3_experts_specialized_in_your_specific_problem_category.": "अपनी विशिष्ट समस्या श्रेणी में विशेषज्ञता रखने वाले शीर्ष 3 विशेषज्ञों से मिलें।",
        "talk_now": "अभी बात करें",
        "lal_kitab_remedies": "लाल किताब उपाय",
        "get_remedies": "उपाय प्राप्त करें",
        "tarot_card_reading": "टैरो कार्ड रीडिंग",
        "draw_cards": "कार्ड ड्रा करें",

        # Flow Intake Form translations
        "intake": "परामर्श जानकारी",
        "problem": "समस्या",
        "tell_us_what_you_need": "हमें बताएं कि आपको क्या चाहिए",
        "short_form_—_only_fields_that_improve_matching_(like_premium_consult_apps).": "संक्षिप्त फॉर्म — केवल वे फ़ील्ड जो मिलान में सुधार करते हैं।",
        "selected:": "चयनित:",
        "we_will_filter_verified_specialists_for_this_topic.": "हम इस विषय के लिए सत्यापित विशेषज्ञों को फ़िल्टर करेंगे।",
        "issue_category": "समस्या श्रेणी",
        "sub-issue_(optional)": "उप-समस्या (वैकल्पिक)",
        "e.g._marriage_delay,_job_switch": "जैसे, विवाह में देरी, नौकरी बदलना",
        "consultation_type": "परामर्श का प्रकार",
        "budget_min_(₹)": "न्यूनतम बजट (₹)",
        "budget_max_(₹)": "अधिकतम बजट (₹)",
        "leave_0_to_ignore_budget_filter": "बजट फ़ील्ड को अनदेखा करने के लिए 0 छोड़ें",
        "urgency": "तात्कालिकता",
        "low_(within_72h)": "कम (72 घंटे के भीतर)",
        "normal_(within_24h)": "सामान्य (24 घंटे के भीतर)",
        "high_(within_6h)": "उच्च (6 घंटे के भीतर)",
        "your_goal": "आपका लक्ष्य",
        "prediction_/_advice_/_remedies": "भविष्यवाणी / सलाह / उपाय",
        "get_top_3_recommendations": "शीर्ष 3 अनुशंसाएं प्राप्त करें",

        # Intake & Recommendation form translations
        "personal_&_birth_details": "व्यक्तिगत और जन्म विवरण",
        "full_name": "पूरा नाम",
        "full_name:": "पूरा नाम:",
        "enter_your_full_name": "अपना पूरा नाम दर्ज करें",
        "date_of_birth": "जन्म तिथि",
        "day_of_birth": "जन्म का दिन",
        "--_select_day_--": "-- दिन चुनें --",
        "time_of_birth": "जन्म समय",
        "place_of_birth": "जन्म स्थान",
        "city,_country": "शहर, देश",
        "current_location_&_residential_info": "वर्तमान स्थान और आवासीय जानकारी",
        "current_residential_address": "वर्तमान आवासीय पता",
        "street,_city,_state,_zip_code": "गली, शहर, राज्य, पिन कोड",
        "current_location": "वर्तमान स्थान",
        "current_city/town": "वर्तमान शहर/कस्बा",
        "consultation_focus": "परामर्श का उद्देश्य",
        "problem_or_reason_for_consultation": "परामर्श की समस्या या कारण",
        "describe_your_concern_in_detail_(e.g.,_career_transition,_marriage_compatibility,_health_challenges,_family_issues)_so_the_jyotishi_can_review_your_chart_appropriately.": "अपनी चिंता का विस्तार से वर्णन करें (जैसे, करियर में बदलाव, विवाह अनुकूलता, स्वास्थ्य चुनौतियाँ, पारिवारिक मुद्दे) ताकि ज्योतिषी आपकी कुंडली की उचित समीक्षा कर सकें।",
        "preferred_astrology_system": "पसंदीदा ज्योतिष प्रणाली",
        "moon-based_jyotish_(vedic_rashi_system)": "चंद्र-आधारित ज्योतिष (वैदिक राशि प्रणाली)",
        "sun-based_jyotish_(western_solar_system)": "सूर्य-आधारित ज्योतिष (पश्चिमी सौर प्रणाली)",
        "submit_details_&_match_jyotishis": "विवरण सबमिट करें और ज्योतिषियों से मिलें",
        "match_recommendations": "मिलान अनुशंसाएं",
        "our_jyotish_system_has_analyzed_your_problem_and_identified_the_best_qualified_astrologers_for_your_concerns.": "हमारी ज्योतिष प्रणाली ने आपकी समस्या का विश्लेषण किया है और आपकी चिंताओं के लिए सबसे योग्य ज्योतिषियों की पहचान की है।",
        "consultation_overview": "परामर्श अवलोकन",
        "birth_details": "जन्म विवरण",
        "address": "पता",
        "jyotish_system": "ज्योतिष प्रणाली",
        "concern_category": "चिंता की श्रेणी",
        "problem_described": "वर्णित समस्या",
        "select_your_preferred_jyotishi": "अपने पसंदीदा ज्योतिषी का चयन करें",
        "language": "भाषा",
        "rate": "दर",
        "credits_/_session": "क्रेडिट / सत्र",
        "form_details_will_be_sent_directly_to": "विवरण सीधे भेजा जाएगा",
        "years_exp": "वर्षों का अनुभव",
        "years_exp_exp": "वर्षों का अनुभव",
        "years_exp_years": "वर्षों का अनुभव",

        # General Panchang / Kundli and Location translations
        "new_delhi": "नई दिल्ली",
        "delhi": "दिल्ली",
        "india": "भारत",
        "sample_kundali": "सैंपल कुंडली",
        "sample_kundli": "सैंपल कुंडली",
        "astrologer_login": "ज्योतिषी लॉगिन",
        "ask_me": "पूछें",
        "credits": "क्रेडिट",
        "tarot": "टैरो",
        "lal_kitab": "लाल किताब",
        
        # Banner & Header texts
        "transit_kundli_(gochar)": "गोचर कुंडली (ट्रांजिट)",
        "transit_kundli_gochar": "गोचर कुंडली (ट्रांजिट)",
        "direct_jyotish_consultation_&_guidance": "प्रत्यक्ष ज्योतिष परामर्श और मार्गदर्शन",
        "consult_the_right_astrologer_for_your_problem": "अपनी समस्या के लिए सही ज्योतिषी से परामर्श करें",
        "submit_structured_consultation_details_→_match_with_qualified_jyotishis_→_directly_send_details_&_connect.": "संरचित विवरण सबमिट करें → योग्य ज्योतिषियों से मिलें → विवरण सीधे भेजें और जुड़ें।",
        "ask_me_—_consultation_form": "मुझसे पूछें — परामर्श फॉर्म",
        "sign_in_&_consult": "लॉग इन करें और परामर्श लें",
        "consultations_are_debited_from_your_credit_points_balance.": "परामर्श आपके क्रेडिट पॉइंट बैलेंस से काटे जाएंगे।",
        "today's_panchang_&_gochar_kundli": "आज का पंचांग और गोचर कुंडली",
        "real-time_planetary_transits_and_auspicious_daily_timings.": "वास्तविक समय के ग्रह गोचर और शुभ दैनिक समय।",

        # Tithis
        "pratipada": "प्रतिपदा",
        "dwitiya": "द्वितीया",
        "tritiya": "तृतीया",
        "chaturthi": "चतुर्थी",
        "panchami": "पंचमी",
        "shashthi": "षष्ठी",
        "saptami": "सप्तमी",
        "ashtami": "अष्टमी",
        "navami": "नवमी",
        "dashami": "दशमी",
        "ekadashi": "एकादशी",
        "dwadashi": "द्वादशी",
        "trayodashi": "त्रयोदशी",
        "chaturdashi": "चतुर्दशी",
        "purnima": "पूर्णिमा",
        "amavasya": "अमावस्या",
        "shukla": "शुक्ल",
        "krishna": "कृष्ण",
        
        # Nakshatras
        "ashwini": "अश्विनी",
        "bharani": "भरणी",
        "krittika": "कृत्तिका",
        "rohini": "रोहिणी",
        "mrigashira": "मृगशिरा",
        "ardra": "आर्द्रा",
        "punarvasu": "पुनर्वसु",
        "pushya": "पुष्य",
        "ashlesha": "अश्लेषा",
        "magha": "मघा",
        "purva_phalguni": "पूर्वा फाल्गुनी",
        "uttara_phalguni": "उत्तरा फाल्गुनी",
        "hasta": "हस्त",
        "chitra": "चित्रा",
        "swati": "स्वाति",
        "vishakha": "विशाखा",
        "anuradha": "अनुराधा",
        "jyeshta": "ज्येष्ठा",
        "mula": "मूल",
        "purva_ashadha": "पूर्वाषाढ़ा",
        "uttara_ashadha": "उत्तराषाढ़ा",
        "shravana": "श्रवण",
        "dhanishta": "धनिष्ठा",
        "shatabhisha": "शतभिषा",
        "purva_bhadrapada": "पूर्वा भाद्रपद",
        "uttara_bhadrapada": "उत्तरा भाद्रपद",
        "revati": "रेवती",

        # Yogas
        "vishkumbha": "विष्कुंभ",
        "priti": "प्रीति",
        "ayushman": "आयुष्मान",
        "saubhagya": "सौभाग्य",
        "shobhana": "शोभन",
        "atiganda": "अतिगण्ड",
        "sukarma": "सुकर्मा",
        "dhriti": "धृति",
        "shula": "शूल",
        "ganda": "गण्ड",
        "vriddhi": "वृद्धि",
        "dhruva": "ध्रुव",
        "vyaghata": "व्याघात",
        "harshana": "हर्षण",
        "vajra": "वज्र",
        "siddhi": "सिद्धि",
        "vyatipata": "व्यतिपात",
        "variyan": "वरीयान",
        "parigha": "परिघ",
        "shiva": "शिव",
        "siddha": "सिद्ध",
        "sadhya": "साध्य",
        "shubha": "शुभ",
        "shukla": "शुक्ल",
        "brahma": "ब्रह्म",
        "indra": "इन्द्र",
        "vaidhriti": "वैधृति",

        # Karanas
        "kintughna": "किंतुघ्न",
        "bava": "बव",
        "balava": "बालव",
        "kaulava": "कौलव",
        "taitila": "तैतिल",
        "garija": "गरिज",
        "vanija": "वणिज",
        "vishti": "विष्टि",
        "shakuni": "शकुनि",
        "chatushpada": "चतुष्पद",
        "naga": "नाग",

        "home": "होम",
        "horoscope": "राशिफल",
        "free_kundli": "फ्री कुंडली",
        "kundli_matching": "कुंडली मिलान",
        "panchang": "पंचांग",
        "astrologers": "ज्योतिषी",
        "talk_to_astrologer": "ज्योतिषी से बात करें",
        "smart_match": "स्मार्ट मैच",
        "wallet": "वॉलेट",
        "recharge": "रिचार्ज",
        "my_account": "मेरा खाता",
        "logout": "लॉगआउट",
        "sign_in": "लॉग इन करें",
        "sign_up": "साइन अप करें",
        "services": "सेवाएं",
        "daily_kundli": "दैनिक कुंडली",
        
        # New Professional Vedic translations
        "calculation_mode": "गणना विधि",
        "house_system": "भाव प्रणाली",
        "modern_astronomical_(jpl/iau)": "आधुनिक खगोलीय (JPL/IAU)",
        "traditional_siddhantic_(surya_siddhanta)": "पारंपरिक सिद्धांत (सूर्य सिद्धांत)",
        "whole_sign_(rashi_chart)": "संपूर्ण राशि (राशि चक्र)",
        "equal_house": "समान भाव",
        "sripati_system": "श्रीपति प्रणाली",
        "bhava_chalit": "भाव चलित",
        "panchang_&_muhurtas": "पंचांग और मुहूर्त",
        "divisional_charts": "वर्ग कुण्डलियाँ",
        "vimshottari_dasha": "विंशोत्तरी दशा",
        "planetary_strength_&_yogas": "ग्रह बल और योग",
        "ashtakavarga_matrix": "अष्टकवर्ग चक्र",
        "gochar_&_transits": "गोचर और संक्रमण",
        "upcoming_eclipses": "आगामी ग्रहण",
        "muhurta_suitability": "मुहूर्त उपयुक्तता",
        "upcoming": "आगामी",
        "coming_soon": "जल्द आ रहा है",
        
        # Suggestion Bot translations
        "ask_astro_ai": "एस्ट्रो AI से पूछें",
        "ask_astro_ai_bot": "पूछें एस्ट्रो AI बॉट",

        "ai_astrological_match_assistant": "AI ज्योतिषीय मिलान सहायक",
        "buying_new_home": "नया घर खरीदना",
        "relationships_&_love": "संबंध और प्रेम",
        "career_/_job": "करियर / नौकरी",
        "wealth_&_finance": "धन और वित्त",
        "recommended_specialists": "अनुशंसित विशेषज्ञ",
        "consult": "परामर्श करें",
        "yrs_experience": "वर्षों का अनुभव",
        "ask_about_marriage,_job,_finance...": "शादी, नौकरी, वित्त के बारे में पूछें...",
        "ask": "पूछें",
        "how_to_choose_best_time_to_buy_home_or_flat": "घर या फ्लैट खरीदने के लिए सबसे अच्छा समय कैसे चुनें",
        "suggest_love_marriage_relationship_advice": "प्रेम विवाह संबंध सलाह सुझाएं",
        "will_i_get_career_growth_or_promotion": "क्या मुझे करियर वृद्धि या पदोन्नति मिलेगी",
        "how_to_strengthen_wealth_and_income": "धन और आय को कैसे मजबूत करें",
        "hello!_i_am_your_astrobot_assistant._ask_me_anything_about_love_relationships,_career,_finance,_property_purchases,_health,_or_remedies._i_will_give_you_vedic_guidance_and_suggest_the_best_matched_astrologer_list!": "नमस्ते! मैं आपका एस्ट्रोबॉट सहायक हूं। मुझसे प्रेम संबंधों, करियर, वित्त, संपत्ति की खरीद, स्वास्थ्य या उपायों के बारे में कुछ भी पूछें। मैं आपको वैदिक मार्गदर्शन दूंगा और सर्वश्रेष्ठ मिलान वाले ज्योतिषी की सूची सुझाऊंगा!",

        "brahma_muhurta": "ब्रह्म मुहूर्त",
        "abhijit_muhurta": "अभिजित मुहूर्त",
        "rahu_kalam": "राहु काल",
        "gulika_kalam": "गुलीक काल",
        "yamaganda": "यमगण्ड",
        "durmuhurta": "दुर्मुहूर्त",
        "horas": "होरा",
        "choghadiya": "चौघड़िया",
        "exaltation": "उच्च",
        "debilitation": "नीच",
        "retrograde": "वक्री",
        "direct": "मार्गी",
        "speed": "गति",
        "points": "अंक",
        "active_yogas": "सक्रिय योग",
        "aspects": "दृष्टि",
        "conjunction": "युति",
        "solar_eclipse": "सूर्य ग्रहण",
        "lunar_eclipse": "चंद्र ग्रहण",
        "suitability": "उपयुक्तता",
        "auspicious": "शुभ",
        "inauspicious": "अशुभ",
        "moderate": "मध्यम",
        "excellent": "उत्कृष्ट",
        "good": "अच्छा",
        "average": "सामान्य",
        "challenging": "चुनौतीपूर्ण",
        "house": "भाव",
        "sign": "राशि",
        "planets": "ग्रह",
        "value": "मूल्य",
        "description": "विवरण",
        "status": "स्थिति",
        "score": "स्कोर",
        "grade": "श्रेणी",
        "positives": "सकारात्मक पहलू",
        "negatives": "नकारात्मक पहलू",
        "upcoming_solar_&_lunar_eclipses": "आगामी सूर्य और चंद्र ग्रहण",
        "peak_time": "शिखर समय",
        "start_time": "प्रारंभ समय",
        "end_time": "समाप्ति समय",
        "visibility": "दृश्यता",


        # Planets
        "sun": "सूर्य",
        "moon": "चंद्र",
        "mars": "मंगल",
        "mercury": "बुध",
        "jupiter": "बृहस्पति",
        "venus": "शुक्र",
        "saturn": "शनि",
        "rahu": "राहु",
        "ketu": "केतु",

        # Signs
        "aries": "मेष",
        "taurus": "वृषभ",
        "gemini": "मिथुन",
        "cancer": "कर्क",
        "leo": "सिंह",
        "virgo": "कन्या",
        "libra": "तुला",
        "scorpio": "वृश्चिक",
        "sagittarius": "धनु",
        "capricorn": "मकर",
        "aquarius": "कुंभ",
        "pisces": "मीन",

        # Form / Fields
        "name": "नाम",
        "dob": "जन्म तिथि",
        "birth_time": "जन्म समय",
        "birth_place": "जन्म स्थान",
        "generate": "कुंडली बनाएं",
        "match_now": "मिलान करें",
        "boy_details": "लड़के का विवरण",
        "girl_details": "लड़की का विवरण",
        "boy_name": "लड़के का नाम",
        "girl_name": "लड़की का नाम",
        "enter_details": "जन्म विवरण दर्ज करें",

        # Details
        "lagna": "लग्न",
        "nakshatra": "नक्षत्र",
        "sun_sign": "सूर्य राशि",
        "moon_sign": "चन्द्र राशि",
        "place": "स्थान",
        "time": "समय",
        "date": "तिथि",

        # Panchang terms
        "tithi": "तिथि",
        "nakshatra_panchang": "नक्षत्र",
        "yoga": "योग",
        "karana": "करण",
        "rahu_kaal": "राहु काल",
        "gulika_kaal": "गुलीक काल",
        "yamaganda": "यमगण्ड",
        "sunrise": "सूर्योदय",
        "sunset": "सूर्यास्त",
        "panchang_for": "पंचांग के लिए",
        "today_panchang": "आज का पंचांग",
        "city": "शहर",
        "update": "अपडेट करें",

        # Suggestions and labels
        "buying_new_home": "नया घर खरीदना",
        "relationships_&_love": "संबंध और प्रेम",
        "career_/_job": "करियर / नौकरी",
        "wealth_&_finance": "धन और वित्त",
        "how_to_choose_best_time_to_buy_home_or_flat": "नया घर या फ्लैट खरीदने का सबसे अच्छा समय कैसे चुनें",
        "suggest_love_marriage_relationship_advice": "प्रेम विवाह और संबंध सुधारने के उपाय",
        "will_i_get_career_growth_or_promotion": "क्या मुझे करियर में तरक्की या प्रमोशन मिलेगा",
        "how_to_strengthen_wealth_and_income": "धन और आय बढ़ाने के उपाय",

        # Service page descriptions
        "daily_horoscope_desc": "दैनिक, साप्ताहिक, मासिक और वार्षिक भविष्यफल विस्तार से जानें।",
        "free_kundli_desc": "12 भावों और ग्रहों के विवरण के साथ अपनी वैदिक जन्म कुंडली बनाएं।",
        "kundli_matching_desc": "विवाह के लिए कुंडली अनुकूलता (गुण मिलान प्रतिशत) की जांच करें।",
        "panchang_desc": "दैनिक शुभ समय, तिथि, नक्षत्र और राहु काल की जांच करें।",
        "astrologers_desc": "करियर, प्रेम, स्वास्थ्य और विवाह की सलाह के लिए सत्यापित विशेषज्ञों से बात करें।",
        "tarot_desc": "अतीत, वर्तमान और भविष्य के मार्गदर्शन के लिए 3 कार्ड चुनें।",
        "remedies_desc": "अपने जीवन की समस्याओं के लिए सरल लाल किताब उपाय खोजें।",

        # Remedies / General UI
        "concern": "चिंता",
        "general": "सामान्य",
        "marriage": "प्रेम / विवाह",
        "finance": "वित्त / धन",
        "lal_kitab_&_vedic_remedies": "लाल किताब और वैदिक उपाय",
        "general_guidance_—_for_personalized_remedies,_consult_a_matched_astrologer.": "सामान्य मार्गदर्शन — व्यक्तिगत उपायों के लिए, एक योग्य ज्योतिषी से परामर्श करें।",
        "get_matched_astrologer": "योग्य ज्योतिषी से मिलें",
        
        # Astrologer Details
        "verified": "सत्यापित",
        "yrs": "वर्ष",
        "chat": "चैट",
        "call": "कॉल",
        "new": "नया",
        "verified_specialists": "सत्यापित विशेषज्ञ — समस्या आधारित ज्योतिष परामर्श लें।",
        "smart_match_top_3": "स्मार्ट मैच — मेरी समस्या के लिए शीर्ष 3",
        "consult_expert_astrologers": "विशेषज्ञ ज्योतिषियों से परामर्श करें",
        "verified_specialists_intro": "सत्यापित विशेषज्ञ — आपकी समस्या, भाषा, बजट और उपलब्धता के अनुसार सर्वश्रेष्ठ (एस्ट्रोसेज जैसा, लेकिन समस्या-प्रथम)।",
        
        # Remedies Content
        "mantra": "मंत्र",
        "charity": "दान",
        "gemstone": "रत्न",
        "relationship": "संबंध",
        "offer_water_to_the_sun_at_sunrise;_avoid_lending_on_tuesdays.": "सूर्योदय के समय सूर्य को जल अर्पित करें; मंगलवार को उधार देने से बचें।",
        "chant_om_namah_shivaya_108_times_on_mondays.": "सोमवार को 108 बार ओम नमः शिवाय का जाप करें।",
        "donate_food_grains_on_thursdays_for_jupiter_strength.": "बृहस्पति की शक्ति के लिए गुरुवार को खाद्यान्न दान करें।",
        "consult_a_verified_astrologer_before_wearing_any_stone.": "कोई भी रत्न धारण करने से पहले प्रमाणित ज्योतिषी से सलाह लें।",
        "light_a_ghee_diya_in_the_southwest_corner_on_fridays.": "शुक्रवार को दक्षिण-पश्चिम कोने में घी का दीया जलाएं।",

        # Horoscope / Timings
        "daily": "दैनिक",
        "weekly": "साप्ताहिक",
        "monthly": "मासिक",
        "yearly": "वार्षिक",
        "luck_score": "भाग्य स्कोर",
        "love": "प्रेम",
        "career": "करियर",
        "health": "स्वास्थ्य",
        "choose_your_sign": "अपनी राशि चुनें",
        "result": "परिणाम",
        "new_kundli": "नई कुंडली",
        "my_saved_charts": "मेरी सहेजी गई कुंडली",
        "new_match": "नया मिलान",
        "view_remedies": "उपाय देखें",
        "talk_to_marriage_specialist": "विवाह विशेषज्ञ से बात करें",
        "boy": "लड़का",
        "girl": "लड़की",
        "birth_chart_lagna": "जन्म कुंडली (लग्न)",
        "planetary_positions": "ग्रहों की स्थिति",
        "birth_charts_comparison": "जन्म कुंडली तुलना",
        "kundli_matching_result": "कुंडली मिलान परिणाम",
        "mangal_dosha": "मंगल दोष",
        "gunas": "गुण",
        "nadi": "नाड़ी",
        "bhakoot": "भकूट",
        "transit_kundli_gochar": "गोचर कुंडली (ट्रांजिट)",
        "today_panchang_gochar_kundli": "आज का पंचांग और गोचर कुंडली",
        "real_time_planetary_transits": "वास्तविक समय के ग्रह गोचर और शुभ दैनिक समय।",
        "view_detailed_panchang": "विस्तृत पंचांग देखें",
        "scroll_to_browse": "ब्राउज़ करने के लिए स्क्रॉल करें · व्यक्तिगत शीर्ष 3 के लिए स्मार्ट मैच के माध्यम से बुक करें",
        "start_smart_match": "स्मार्ट मैच शुरू करें",
        "pick_problem_category": "समस्या श्रेणी चुनें",
        "short_intake": "संक्षिप्त विवरण दर्ज करें (भाषा, बजट, तात्कालिकता)",
        "get_top_3_with_match_score": "मैच स्कोर और कारणों के साथ शीर्ष 3 ज्योतिषी प्राप्त करें",
        "book_chat_or_call": "चैट या कॉल बुक करें",
        "rate_session": "सत्र को रेट करें — सिस्टम सीखता है",
        "start_intake_now": "अभी शुरू करें",
        "sign_in_to_start": "शुरू करने के लिए लॉग इन करें",
        "popular_concerns": "लोकप्रिय चिंताएं",

        # Horoscope themes
        "focus_on_steady_progress_at_work;_avoid_impulsive_decisions_before_noon.": "काम पर निरंतर प्रगति पर ध्यान दें; दोपहर से पहले जल्दबाजी में निर्णय लेने से बचें।",
        "relationships_improve_when_you_listen_more_than_you_speak_today.": "जब आप आज बोलने से ज्यादा सुनेंगे तो रिश्तों में सुधार होगा।",
        "a_financial_opportunity_may_appear—verify_details_before_committing.": "एक वित्तीय अवसर प्रकट हो सकता है—प्रतिबद्ध होने से पहले विवरण सत्यापित करें।",
        "health_and_routine_matter;_short_walks_and_hydration_help_your_energy.": "स्वास्थ्य और दिनचर्या मायने रखती है; छोटी सैर और पानी पीना आपकी ऊर्जा में मदद करता है।",
        "creative_ideas_flow;_share_them_with_a_trusted_mentor_or_partner.": "रचनात्मक विचार प्रवाहित होते हैं; उन्हें किसी विश्वसनीय गुरु या साथी के साथ साझा करें।",
        "family_matters_need_patience;_small_gestures_build_harmony.": "पारिवारिक मामलों में धैर्य की आवश्यकता होती है; छोटे इशारे सद्भाव बनाते हैं।",
        "travel_or_learning_plans_gain_momentum;_stay_flexible_with_timing.": "यात्रा या सीखने की योजनाएँ गति पकड़ती हैं; समय के साथ लचीले रहें।",
        "property_or_long-term_investments_favor_research_over_speed_today.": "संपत्ति या दीर्घकालिक निवेश आज गति से अधिक शोध का पक्ष लेते हैं।",
        "career_visibility_increases_mid-week;_prepare_for_important_conversations.": "सप्ताह के मध्य में करियर की दृश्यता बढ़ती है; महत्वपूर्ण बातचीत के लिए तैयारी करें।",
        "love_life_stabilizes_when_you_express_needs_clearly_and_kindly.": "जब आप स्पष्ट रूप से और दयालुता से आवश्यकताओं को व्यक्त करते हैं तो प्रेम जीवन स्थिर हो जाता है।",
        "budget_discipline_pays_off;_unexpected_expenses_are_manageable.": "बजट अनुशासन रंग लाता है; अप्रत्याशित खर्चे प्रबंधनीय हैं।",
        "spiritual_practice_or_meditation_supports_clarity_on_a_major_choice.": "आध्यात्मिक अभ्यास या ध्यान एक प्रमुख विकल्प पर स्पष्टता का समर्थन करता है।",
        "this_month_favors_structured_goals_in_career_and_education.": "यह महीना करियर और शिक्षा में संरचित लक्ष्यों का पक्षधर है।",
        "emotional_healing_in_relationships_opens_space_for_deeper_trust.": "रिश्तों में भावनात्मक उपचार गहरे विश्वास के लिए जगह खोलता है।",
        "financial_planning_and_debt_reduction_bring_long-term_relief.": "वित्तीय नियोजन और ऋण में कमी दीर्घकालिक राहत लाती है।",
        "health_routines_started_now_can_become_sustainable_habits.": "अब शुरू की गई स्वास्थ्य दिनचर्या टिकाऊ आदतें बन सकती हैं।",
        "a_year_of_consolidation:_build_skills,_savings,_and_supportive_networks.": "समेकन का एक वर्ष: कौशल, बचत और सहायक नेटवर्क का निर्माण करें।",
        "partnerships_and_collaborations_define_success—choose_allies_wisely.": "साझेदारी और सहयोग सफलता को परिभाषित करते हैं—सहयोगियों को बुद्धिमानी से चुनें।",
        "relocation,_study_abroad,_or_new_roles_may_appear_in_the_second_half.": "स्थानांतरण, विदेश में अध्ययन, या नई भूमिकाएँ दूसरी छमाही में दिखाई दे सकती हैं।",
        "remedies_and_disciplined_spiritual_practice_amplify_positive_outcomes.": "उपाय और अनुशासित आध्यात्मिक अभ्यास सकारात्मक परिणामों को बढ़ाते हैं।",
        "moderate_energy—prioritize_rest_if_stressed.": "मध्यम ऊर्जा—तनाव होने पर विश्राम को प्राथमिकता दें।"
    }
}

def translate_filter(val, lang: str = "en") -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return [translate_filter(item, lang) for item in val]
    
    text = str(val).strip()
    if not text:
        return ""
        
    if lang == "hi":
        # Day of week and Month translation replacements
        replacements = {
            "monday": "सोमवार", "tuesday": "मंगलवार", "wednesday": "बुधवार", "thursday": "गुरुवार",
            "friday": "शुक्रवार", "saturday": "शनिवार", "sunday": "रविवार",
            "january": "जनवरी", "february": "फरवरी", "march": "मार्च", "april": "अप्रैल",
            "may": "मई", "june": "जून", "july": "जुलाई", "august": "अगस्त",
            "september": "सितंबर", "october": "अक्टूबर", "november": "नवंबर", "december": "दिसंबर"
        }
        lower_text = text.lower()
        replaced = False
        for k, v in replacements.items():
            if k in lower_text:
                import re
                text = re.sub(re.escape(k), v, text, flags=re.IGNORECASE)
                replaced = True
        if replaced:
            return text
        
    if len(text) > 100:
        key = text.lower().replace(" ", "_")
        t_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
        res = t_dict.get(key) or t_dict.get(text.lower())
        if res:
            return res
        return text

    if "," in text:
        parts = [p.strip() for p in text.split(",")]
        translated_parts = [translate_filter(p, lang) for p in parts]
        return ", ".join(translated_parts)
        
    key = text.lower().replace(" ", "_")
    t_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    
    res = t_dict.get(key)
    if res:
        return res
        
    # Check direct lower
    res = t_dict.get(text.lower())
    if res:
        return res
        
    return text

templates.env.filters["t"] = translate_filter

