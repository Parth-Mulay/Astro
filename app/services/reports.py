from __future__ import annotations


def kundli_report_html(chart: dict) -> str:
    houses_rows = ""
    for h, data in chart.get("houses", {}).items():
        planets = ", ".join(data.get("planets", [])) or "—"
        houses_rows += f"<tr><td>House {h}</td><td>{data['sign']}</td><td>{planets}</td></tr>"

    return f"""
    <h1>Kundli Report — {chart['name']}</h1>
    <p><strong>DOB:</strong> {chart['dob']} · <strong>Time:</strong> {chart['birth_time']} · <strong>Place:</strong> {chart['place']}</p>
    <table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">
      <tr><th>Lagna</th><th>Moon</th><th>Sun</th><th>Nakshatra</th></tr>
      <tr><td>{chart['lagna']}</td><td>{chart['moon_sign']}</td><td>{chart['sun_sign']}</td><td>{chart['nakshatra']}</td></tr>
    </table>
    <h2>Vedic Chart (12 Houses)</h2>
    <table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">
      <tr><th>House</th><th>Sign</th><th>Planets</th></tr>
      {houses_rows}
    </table>
    <p><em>Includes Vedic, KP &amp; Lal Kitab reference flags. For detailed remedies, consult a matched astrologer.</em></p>
    """


def match_report_html(result: dict) -> str:
    return f"""
    <h1>Kundli Matching Report</h1>
    <p><strong>{result['boy']['name']}</strong> × <strong>{result['girl']['name']}</strong></p>
    <p>Score: <strong>{result['percent']}%</strong> ({result['gunas']}/{result['max_gunas']} gunas) — {result['verdict']}</p>
    <p>{result['summary']}</p>
    <p>Mangal dosha: {'Yes' if result['mangal_dosha'] else 'No'} · Nadi: {result['nadi']} · Bhakoot: {result['bhakoot']}</p>
    """


def session_report_html(sess_id: int, astrologer_name: str, price: int, category: str) -> str:
    return f"""
    <h1>Consultation Summary</h1>
    <p>Session #{sess_id} with <strong>{astrologer_name}</strong></p>
    <p>Category: {category} · Amount paid: ₹{price}</p>
    <p>Thank you for using AstroMatch. Your feedback improves future recommendations.</p>
    """
