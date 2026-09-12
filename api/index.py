import sys
import os
import traceback

# Ensure project root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from app.main import app
except Exception as err:
    print(f"Error importing app.main in api/index.py: {err}", file=sys.stderr)
    traceback.print_exc()
    raise err
