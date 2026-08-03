#!/bin/bash
set -e

# FastAPI application startup script

echo "=== Starting AstroMatch Startup Process ==="

# 1. Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "ERROR: .env file not found! Copy .env.example to .env and configure it."
    exit 1
fi

# 2. Extract database path
DB_PATH=$(python -c "
from app.settings import settings
import os
url = settings.DATABASE_URL
if url.startswith('sqlite:///./'):
    print(url.replace('sqlite:///./', ''))
elif url.startswith('sqlite:////'):
    print(url.replace('sqlite:////', '/'))
else:
    print(url.replace('sqlite:///', ''))
")

echo "Database path resolved to: $DB_PATH"

# 3. Create persistent directories
echo "Creating required directories..."
mkdir -p uploads reports logs backups $(dirname "$DB_PATH")
chmod -R 775 uploads reports logs backups

# 4. Initialize and Seed database if it does not exist
if [ ! -f "$DB_PATH" ] || [ ! -s "$DB_PATH" ]; then
    echo "Database file '$DB_PATH' not found or empty. Seeding database..."
    python -m app.seed
    echo "Database seeding completed."
else
    echo "Database already exists. Skipping seed."
fi

# 5. Verify Skyfield ephemeris
if [ ! -f "de421.bsp" ]; then
    echo "Downloading Skyfield ephemeris de421.bsp..."
    python -c "from skyfield.api import Loader; load = Loader('.'); load('de421.bsp')"
fi

echo "=== Startup Verification Successful ==="
exec "$@"
