from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any


# ============================================================
# Make project root importable
# ============================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


# ============================================================
# Third-party imports
# ============================================================

import pandas as pd
import streamlit as st


# ============================================================
# Project imports
# ============================================================

from app.admin import (
    get_admin_dashboard,
)
from app.blockchain import (
    BlockchainClient,
    BlockchainError,
)
from app.compliance import (
    build_compliance_report,
)
from app.components.admin_dashboard import (
    render_admin_dashboard,
)
from app.components.bond_overview import (
    render_bond_overview,
)
from app.components.compliance_audit import (
    render_compliance_audit,
)
from app.components.investor_portal import (
    render_investor_portal,
)
from app.components.issuer_dashboard import (
    render_issuer_dashboard,
)
from app.components.payment_schedule import (
    render_payment_schedule,
)
from app.config import (
    BOND_TOKEN_ADDRESS,
    BOND_USD_ADDRESS,
    ETHERSCAN_BASE_URL,
    INVESTOR_1_ADDRESS,
    INVESTOR_2_ADDRESS,
    NETWORK_NAME,
    TOKENIZED_BOND_ADDRESS,
    etherscan_address_url,
)
from app.investor import (
    get_investor_position,
)
from app.issuer import (
    get_issuer_dashboard,
)
from app.overview import (
    get_bond_overview,
)
from app.payment_schedule import (
    build_payment_schedule,
)


# ============================================================
# Streamlit page configuration
# ============================================================

st.set_page_config(
    page_title="Blockchain Bond Demo",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.25rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .sub-title {
            color: #6b7280;
            margin-bottom: 1.5rem;
        }

        .load-time {
            color: #6b7280;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Blockchain client
# ============================================================

@st.cache_resource
def get_blockchain_client() -> BlockchainClient:
    """Create one reusable RPC client."""
    return BlockchainClient()


# ============================================================
# Cached loaders
# ============================================================

@st.cache_data(
    ttl=15,
    show_spinner=False,
)
def load_network_status() -> Any:
    return (
        get_blockchain_client()
        .get_network_status()
    )


@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def load_contract_statuses() -> Any:
    return (
        get_blockchain_client()
        .get_all_contract_code_statuses()
    )


@st.cache_data(
    ttl=30,
    show_spinner=False,
)
def load_system_state() -> Any:
    return (
        get_blockchain_client()
        .get_system_state()
    )


@st.cache_data(
    ttl=30,
    show_spinner=False,
)
def load_bond_overview() -> Any:
    return get_bond_overview(
        get_blockchain_client()
    )


@st.cache_data(
    ttl=30,
    show_spinner=False,
)
def load_investor_position(
    address: str,
    label: str,
) -> Any:
    return get_investor_position(
        get_blockchain_client(),
        address,
        label,
    )


@st.cache_data(
    ttl=30,
    show_spinner=False,
)
def load_issuer_dashboard() -> Any:
    return get_issuer_dashboard(
        get_blockchain_client()
    )


@st.cache_data(
    ttl=30,
    show_spinner=False,
)
def load_admin_dashboard() -> Any:
    return get_admin_dashboard(
        get_blockchain_client()
    )


def clear_dynamic_cache() -> None:
    """Clear data that can change on-chain."""
    load_network_status.clear()
    load_system_state.clear()
    load_bond_overview.clear()
    load_investor_position.clear()
    load_issuer_dashboard.clear()
    load_admin_dashboard.clear()


def clear_all_cache() -> None:
    """Clear static and dynamic cached data."""
    clear_dynamic_cache()
    load_contract_statuses.clear()
    get_blockchain_client.clear()


# ============================================================
# Helpers
# ============================================================

def shorten_address(
    address: str,
) -> str:
    if len(address) <= 14:
        return address

    return (
        f"{address[:8]}"
        f"..."
        f"{address[-6:]}"
    )


def render_load_time(
    started_at: float,
) -> None:
    elapsed = (
        time.perf_counter()
        - started_at
    )

    st.markdown(
        (
            '<div class="load-time">'
            f"Page load time: {elapsed:.3f} seconds"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_page_heading(
    title: str,
    description: str,
) -> None:
    st.markdown(
        (
            '<div class="main-title">'
            f"{title}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            '<div class="sub-title">'
            f"{description}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_technical_status() -> None:
    """Render network, contract and base deployment status."""
    network = load_network_status()
    contract_statuses = load_contract_statuses()
    system_state = load_system_state()

    st.subheader("Network Status")

    (
        network_col_1,
        network_col_2,
        network_col_3,
        network_col_4,
    ) = st.columns(4)

    network_col_1.metric(
        label="RPC",
        value=(
            "Connected"
            if network.connected
            else "Disconnected"
        ),
    )

    network_col_2.metric(
        label="Chain ID",
        value=network.chain_id,
    )

    network_col_3.metric(
        label="Latest Block",
        value=f"{network.latest_block:,}",
    )

    network_col_4.metric(
        label="Gas Price",
        value=(
            f"{network.gas_price_gwei:.4f} Gwei"
        ),
    )

    st.subheader("Contract Status")

    rows = [
        {
            "Contract": status.contract_name,
            "Address": status.address,
            "Code": (
                "Available"
                if status.has_code
                else "Missing"
            ),
            "Bytecode Size": status.bytecode_size,
            "Etherscan": etherscan_address_url(
                status.address
            ),
        }
        for status in contract_statuses
    ]

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Etherscan": (
                st.column_config.LinkColumn(
                    "Etherscan",
                    display_text="Open",
                )
            ),
        },
    )

    st.subheader("Base Deployment")

    (
        state_col_1,
        state_col_2,
        state_col_3,
        state_col_4,
    ) = st.columns(4)

    state_col_1.metric(
        label="Lifecycle",
        value=system_state.lifecycle_name,
    )

    state_col_2.metric(
        label="BondToken Supply",
        value=system_state.bond_token_supply,
    )

    state_col_3.metric(
        label="Total Subscribed",
        value=system_state.total_subscribed,
    )

    state_col_4.metric(
        label="Escrow",
        value=(
            f"{system_state.escrow_balance_display:,.2f} "
            "BONDUSD"
        ),
    )

    control_col_1, control_col_2 = (
        st.columns(2)
    )

    with control_col_1:
        st.json(
            {
                "Admin": system_state.admin,
                "Issuer": system_state.issuer,
                "Payment token": (
                    system_state.payment_token
                ),
                "Bond token": (
                    system_state.bond_token
                ),
            }
        )

    with control_col_2:
        st.json(
            {
                "Controller": (
                    system_state.bond_token_controller
                ),
                "BondToken owner": (
                    system_state.bond_token_owner
                ),
                "Subscription paused": (
                    system_state.subscription_paused
                ),
                "Proceeds withdrawn": (
                    system_state.proceeds_withdrawn
                ),
            }
        )

    st.info(
        "Technical Status is read-only and creates no transaction."
    )


# ============================================================
# Sidebar navigation
# ============================================================

with st.sidebar:
    st.header(
        "Blockchain Bond Demo"
    )

    st.caption(
        "Ethereum Sepolia"
    )

    page = st.radio(
        "Navigation",
        options=[
            "Bond Overview",
            "Investor Portal",
            "Issuer Dashboard",
            "Admin Dashboard",
            "Payment Schedule",
            "Compliance and Audit",
            "Technical Status",
        ],
        key="main_navigation",
    )

    st.divider()

    st.write(
        f"**Network:** {NETWORK_NAME}"
    )

    st.write(
        "**Chain ID:** 11155111"
    )

    st.link_button(
        "Sepolia Etherscan",
        ETHERSCAN_BASE_URL,
        use_container_width=True,
    )

    st.divider()

    st.write(
        "**BondUSDToken**"
    )

    st.code(
        shorten_address(
            BOND_USD_ADDRESS
        ),
        language=None,
    )

    st.write(
        "**BondToken**"
    )

    st.code(
        shorten_address(
            BOND_TOKEN_ADDRESS
        ),
        language=None,
    )

    st.write(
        "**TokenizedBond**"
    )

    st.code(
        shorten_address(
            TOKENIZED_BOND_ADDRESS
        ),
        language=None,
    )

    st.divider()

    if st.button(
        "Refresh on-chain data",
        use_container_width=True,
        type="primary",
    ):
        clear_dynamic_cache()
        st.rerun()

    if st.button(
        "Clear all cache",
        use_container_width=True,
    ):
        clear_all_cache()
        st.rerun()


# ============================================================
# Page routing
# ============================================================

try:
    started_at = time.perf_counter()

    if page == "Bond Overview":
        render_page_heading(
            "Blockchain Bond Demo",
            (
                "Financial terms, offering progress "
                "and lifecycle overview"
            ),
        )

        with st.spinner(
            "Loading bond overview..."
        ):
            overview = load_bond_overview()

        render_bond_overview(
            overview
        )

    elif page == "Investor Portal":
        render_page_heading(
            "Investor Portal",
            (
                "Read-only investor balances, positions "
                "and claimable rights"
            ),
        )

        with st.spinner(
            "Loading investor positions..."
        ):
            investor_positions = {
                "Investor 1": (
                    load_investor_position(
                        INVESTOR_1_ADDRESS,
                        "Investor 1",
                    )
                ),
                "Investor 2": (
                    load_investor_position(
                        INVESTOR_2_ADDRESS,
                        "Investor 2",
                    )
                ),
            }

        render_investor_portal(
            investor_positions
        )

    elif page == "Issuer Dashboard":
        render_page_heading(
            "Issuer Dashboard",
            (
                "Offering proceeds, coupon obligations "
                "and principal repayment"
            ),
        )

        with st.spinner(
            "Loading issuer data..."
        ):
            issuer_dashboard = (
                load_issuer_dashboard()
            )

        render_issuer_dashboard(
            issuer_dashboard
        )

    elif page == "Admin Dashboard":
        render_page_heading(
            "Admin Dashboard",
            (
                "Whitelist inspection and permissioned "
                "subscription controls"
            ),
        )

        with st.spinner(
            "Loading admin data..."
        ):
            admin_dashboard = (
                load_admin_dashboard()
            )

        render_admin_dashboard(
            admin_dashboard,
            get_blockchain_client(),
        )

    elif page == "Payment Schedule":
        render_page_heading(
            "Payment Schedule",
            (
                "Coupon and principal funding, distribution "
                "and default timeline"
            ),
        )

        with st.spinner(
            "Loading payment obligations..."
        ):
            overview = load_bond_overview()
            issuer_dashboard = (
                load_issuer_dashboard()
            )

            payment_schedule = (
                build_payment_schedule(
                    overview,
                    issuer_dashboard,
                )
            )

        render_payment_schedule(
            payment_schedule
        )

    elif page == "Compliance and Audit":
        render_page_heading(
            "Compliance and Audit",
            (
                "Deployment, role, supply and financial "
                "reconciliation checks"
            ),
        )

        with st.spinner(
            "Running read-only audit..."
        ):
            network = load_network_status()

            contract_statuses = (
                load_contract_statuses()
            )

            system_state = (
                load_system_state()
            )

            overview = (
                load_bond_overview()
            )

            issuer_dashboard = (
                load_issuer_dashboard()
            )

            investor_positions = {
                "Investor 1": (
                    load_investor_position(
                        INVESTOR_1_ADDRESS,
                        "Investor 1",
                    )
                ),
                "Investor 2": (
                    load_investor_position(
                        INVESTOR_2_ADDRESS,
                        "Investor 2",
                    )
                ),
            }

            compliance_report = (
                build_compliance_report(
                    chain_id=network.chain_id,
                    contract_statuses=(
                        contract_statuses
                    ),
                    system_state=system_state,
                    overview=overview,
                    issuer_dashboard=(
                        issuer_dashboard
                    ),
                    investor_positions=(
                        investor_positions
                    ),
                )
            )

        render_compliance_audit(
            compliance_report
        )

    elif page == "Technical Status":
        render_page_heading(
            "Technical Status",
            (
                "RPC, deployed bytecode and base "
                "contract configuration"
            ),
        )

        with st.spinner(
            "Loading technical status..."
        ):
            render_technical_status()

    render_load_time(
        started_at
    )

    st.divider()

    st.caption(
        "Read-only local application. No private key is loaded "
        "and no transaction is signed by Streamlit."
    )

except BlockchainError as exc:
    st.error(
        "Không thể đọc dữ liệu blockchain."
    )

    st.code(
        str(exc),
        language=None,
    )

    st.warning(
        "Kiểm tra SEPOLIA_RPC_URL, kết nối Internet, "
        "deployment file và ABI."
    )

except Exception as exc:
    st.error(
        "Ứng dụng gặp lỗi ngoài dự kiến."
    )

    st.code(
        str(exc),
        language=None,
    )