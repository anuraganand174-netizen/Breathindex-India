"""WSGI entry for Gunicorn / Render / Railway (run from project root)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.flask_api import app  # noqa: E402
