"""Shared UI styling for every Streamlit page."""

import streamlit as st


st.markdown(
    """
    <style>
        /* Hide the original main entrypoint from Streamlit's automatic nav. */
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
