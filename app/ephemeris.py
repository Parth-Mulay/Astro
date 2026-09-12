from __future__ import annotations
import os
from skyfield.api import Loader

# Initialize Loader targeting current working directory or /tmp if read-only (e.g., Vercel / AWS Lambda)
cache_dir = '.' if os.access('.', os.W_OK) else '/tmp'
load = Loader(cache_dir, verbose=False)

# Cache the timescale and ephemeris objects safely
try:
    ts = load.timescale()
except Exception:
    ts = None

eph_file = 'de421.bsp'
if os.path.exists(eph_file):
    eph = load(eph_file)
elif os.path.exists(os.path.join(cache_dir, eph_file)):
    eph = load(os.path.join(cache_dir, eph_file))
else:
    try:
        eph = load(eph_file)
    except Exception:
        eph = None
