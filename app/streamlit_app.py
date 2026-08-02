from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

pages = [
    st.Page(
        "pages/1_GreenBond26.py",
        title="GreenBond26",
        icon="🌱",
        default=True,
    ),
    st.Page(
        "pages/2_EnergyBond26.py",
        title="EnergyBond26",
        icon="⚡",
    ),
    st.Page(
        "pages/3_EduBond26.py",
        title="EduBond26",
        icon="🎓",
    ),
]

navigation = st.navigation(
    pages,
    position="sidebar",
)

navigation.run()
