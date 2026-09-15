import sys
import os
import traceback

# Ensure project root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Initialize database schema for serverless execution
try:
    from app.db import create_db_and_tables
    create_db_and_tables()
except Exception as e:
    print(f"Database table initialization warning: {e}", file=sys.stderr)

# Seed default admin, client, and astrologer accounts on first startup
try:
    from app.seed import run_seed
    run_seed()
    print("Database seeding completed successfully.", file=sys.stderr)
except Exception as e:
    print(f"Database seeding warning (non-fatal): {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)


try:
    from mangum import Mangum
    from app.main import app

    handler = Mangum(app, lifespan="off")
    app = handler
except Exception as err:
    print(f"Error initializing app in api/index.py: {err}", file=sys.stderr)
    traceback.print_exc()
    raise err
