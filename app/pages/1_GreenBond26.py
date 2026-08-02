import streamlit as st

from app.bond_runtime import run_bond_app


run_bond_app("greenBond26")

st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] ul li:first-child a {
            font-size: 0 !important;
        }

        [data-testid="stSidebarNav"] ul li:first-child a::after {
            content: "Demo Bond";
            font-size: 0.95rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)
