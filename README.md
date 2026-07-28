# AstroMatch – Astrology Platform (Python)

Full-stack MVP inspired by [AstroSage](https://www.astrosage.com/) UI with a **unique problem-based matching engine**.

## Features (working)

### Retention (free tools)
| Feature | URL |
|---------|-----|
| Daily / weekly / monthly / yearly horoscope | `/tools/horoscope` |
| Free Kundli (Vedic chart, 12 houses) | `/tools/kundli` |
| Kundli matching (gun milan %) | `/tools/match` |
| Panchang (tithi, nakshatra, rahu kaal) | `/tools/panchang` |
| Lal Kitab remedies | `/tools/remedies` |
| Tarot (3-card draw) | `/tools/tarot` |
| Browse astrologers | `/tools/astrologers` |

### Monetization
| Feature | Flow |
|---------|------|
| Wallet + demo recharge | `/account/wallet` |
| Pay for consultation | Book → `/flow/pay/{id}` → wallet debit |
| Live chat/call (demo UI) | `/flow/chat/{id}` after payment |
| HTML reports (print as PDF) | Auto-saved on kundli / match / session |

### Core matching (your differentiator)
| Feature | Flow |
|---------|------|
| Sign up / sign in | `/auth/signup`, `/auth/login` |
| User profile (cloud) | `/account/profile` |
| History (intakes, sessions, kundli, reports) | `/account/history` |
| Issue intake → top 3 + reasons | `/flow/problem` → intake → recommendations |
| Book → pay → chat → feedback | Full loop |
| Learning loop | `python -m app.learning` (also runs after feedback) |
| Admin quality dashboard | `/admin` |

## Quickstart

```powershell
cd c:\astro
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

**Demo:** `user@example.com` / `password` (₹500 wallet) · `admin@example.com` / `password`

## Notes

- Kundli/horoscope use deterministic algorithms (not Swiss Ephemeris). Swap in real ephemeris later.
- Payments are wallet-based demo (integrate Razorpay/Stripe for production).
- New DB tables are created on startup; re-run seed after schema changes.
