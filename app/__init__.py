"""Shared UI bootstrap for every Streamlit page."""

import streamlit as st


# Streamlit 1.60 supports additive page configuration calls. Keeping this
# first ensures the shared styling below is valid on the main page as well.
st.set_page_config(
    page_title="Blockchain Bond Demo",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        /* Keep the original demo page available by URL, but hide it from nav. */
        [data-testid="stSidebarNav"] ul li:first-child {
            display: none !important;
        }

        /* Hide the Solidity/BondUSD explanatory caption in Financial Terms. */
        div[data-testid="stTabs"] div[role="tabpanel"]:first-of-type
        [data-testid="stCaptionContainer"] {
            display: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)
