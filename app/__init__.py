"""Shared UI bootstrap for every Streamlit page."""

import streamlit as st


st.set_page_config(
    page_title="Blockchain Bond Demo",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        /* Ẩn hoàn toàn navigation tự động của Streamlit, bao gồm trang gốc. */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Ẩn chú thích kỹ thuật trong Financial Terms. */
        div[data-testid="stTabs"] div[role="tabpanel"]:first-of-type
        [data-testid="stCaptionContainer"] {
            display: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Điều hướng riêng chỉ hiển thị ba đợt phát hành mới.
with st.sidebar:
    st.markdown("### Bond Offerings")
    st.page_link(
        "pages/1_GreenBond26.py",
        label="GreenBond26",
        icon="🌱",
    )
    st.page_link(
        "pages/2_EnergyBond26.py",
        label="EnergyBond26",
        icon="⚡",
    )
    st.page_link(
        "pages/3_EduBond26.py",
        label="EduBond26",
        icon="🎓",
    )
    st.divider()
