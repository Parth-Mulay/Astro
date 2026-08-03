from __future__ import annotations
import os
from skyfield.api import Loader

# Initialize Loader targeting the current working directory.
# This will download de421.bsp and timescale files if they are not already cached.
load = Loader('.')

# Cache the timescale and ephemeris objects so they are loaded/downloaded only once.
ts = load.timescale()
eph = load('de421.bsp')
