#!/bin/bash
set -e

# FastAPI application startup script

echo "=== Starting AstroMatch Startup Process ==="

# 1. Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
elif [ -z "$ENVIRONMENT" ]; then
    echo "ERROR: .env file not found and ENVIRONMENT is not set!"
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
elif url.startswith('sqlite:///'):
    print(url.replace('sqlite:///', ''))
else:
    print('')
")

echo "Database path resolved to: $DB_PATH"

# 3. Create persistent directories
echo "Creating required directories..."
if [ -n "$DB_PATH" ]; then
    mkdir -p uploads reports logs backups $(dirname "$DB_PATH")
else
    mkdir -p uploads reports logs backups
fi
chmod -R 775 uploads reports logs backups

# 4. Initialize and Seed database if it does not exist
if [ -n "$DB_PATH" ]; then
    if [ ! -f "$DB_PATH" ] || [ ! -s "$DB_PATH" ]; then
        echo "Database file '$DB_PATH' not found or empty. Seeding database..."
        python -m app.seed
        echo "Database seeding completed."
    else
        echo "Database already exists. Skipping seed."
    fi
else
    echo "Using non-SQLite database. Running migrations/seed if needed..."
    python -m app.seed
fi

# 5. Verify Skyfield ephemeris
if [ ! -f "de421.bsp" ]; then
    echo "Downloading Skyfield ephemeris de421.bsp..."
    python -c "from skyfield.api import Loader; load = Loader('.'); load('de421.bsp')"
fi

echo "=== Startup Verification Successful ==="
exec "$@"
