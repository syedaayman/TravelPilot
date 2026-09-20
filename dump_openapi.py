import sys
import json
import os

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath('.'))

from fastapi.openapi.utils import get_openapi
from backend.app.main import app

with open("frontend/openapi.json", "w") as f:
    json.dump(get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    ), f)
