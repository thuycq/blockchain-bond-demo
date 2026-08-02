from __future__ import annotations

import runpy
from pathlib import Path


MAIN_APP_FILE = Path(__file__).with_name("streamlit_app.py")

runpy.run_path(
    str(MAIN_APP_FILE),
    run_name="__main__",
)
