from __future__ import annotations
import os
from skyfield.api import Loader

# Initialize Loader targeting current working directory or /tmp if read-only (e.g., Vercel / AWS Lambda)
cache_dir = '.' if os.access('.', os.W_OK) else '/tmp'
load = Loader(cache_dir, verbose=False)

try:
    ts = load.timescale()
except Exception:
    ts = None

eph_file = 'de421.bsp'
eph = None

# Search for de421.bsp in current dir, root dir, or cache dir
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
possible_paths = [
    eph_file,
    os.path.join(base_dir, eph_file),
    os.path.join(cache_dir, eph_file)
]

for p in possible_paths:
    if os.path.exists(p):
        try:
            eph = load(p)
            break
        except Exception:
            pass

if eph is None:
    try:
        eph = load(eph_file)
    except Exception:
        class SafeEphDict(dict):
            def __getitem__(self, item):
                return super().get(item, None)
        eph = SafeEphDict()
