import sys
import os
import traceback

# Ensure project root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from mangum import Mangum
    from app.main import app

    handler = Mangum(app, lifespan="off")
    app = handler
except Exception as err:
    print(f"Error initializing app in api/index.py: {err}", file=sys.stderr)
    traceback.print_exc()
    raise err
