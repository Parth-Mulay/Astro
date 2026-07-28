import sys
import unittest
from datetime import date, time
from app.vedic_engine.services.astrology_service import calculate_professional_kundli

class TestVedicEngineValidation(unittest.TestCase):
    def setUp(self):
        # Setup birth details for a known reference: May 15, 1995 at 10:30 in Mumbai
        # Sun: Taurus, Moon: Scorpio, Lagna: Cancer, Moon Nakshatra: Anuradha
        self.chart = calculate_professional_kundli(
            name="Reference Profile",
            dob=date(1995, 5, 15),
            birth_time=time(10, 30),
            place="Mumbai",
            calc_mode="modern",
            house_system="whole_sign"
        )
        
    def test_planetary_longitudes_and_signs(self):
        # Verify Sun placement
        sun_sign = self.chart["sun_sign"]
        self.assertEqual(sun_sign, "Taurus", f"Sun sign is {sun_sign}, expected Taurus.")
        
        # Verify Moon placement
        moon_sign = self.chart["moon_sign"]
        self.assertEqual(moon_sign, "Scorpio", f"Moon sign is {moon_sign}, expected Scorpio.")
        
        # Verify Lagna placement
        lagna = self.chart["lagna"]
        self.assertEqual(lagna, "Cancer", f"Lagna is {lagna}, expected Cancer.")
        
        # Verify Nakshatra
        nakshatra = self.chart["nakshatra"]
        self.assertEqual(nakshatra, "Anuradha", f"Nakshatra is {nakshatra}, expected Anuradha.")
        
    def test_divisional_charts_existance(self):
        # Verify Navamsa D9 exists
        self.assertIn("D9", self.chart["divisional_charts"])
        d9_placements = self.chart["divisional_charts"]["D9"]
        self.assertIn("Sun", d9_placements)
        self.assertIn("Moon", d9_placements)
        self.assertIn("Lagna", d9_placements)
        
    def test_panchang_elements(self):
        panchang = self.chart["panchang"]
        self.assertIn("tithi", panchang)
        self.assertIn("vara", panchang)
        self.assertIn("nakshatra", panchang)
        self.assertIn("yoga", panchang)
        self.assertIn("karana", panchang)
        
        # Verify Sunrise and Sunset formats
        self.assertRegex(panchang["sunrise"], r"\d{2}:\d{2}:\d{2}")
        self.assertRegex(panchang["sunset"], r"\d{2}:\d{2}:\d{2}")

    def test_shadbala_existance(self):
        shadbala = self.chart["shadbala"]
        self.assertIn("Sun", shadbala)
        self.assertIn("total", shadbala["Sun"])
        self.assertIn("sthanabala", shadbala["Sun"])

if __name__ == "__main__":
    unittest.main()
