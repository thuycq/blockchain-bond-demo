from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

import pandas as pd
import streamlit as st
from web3 import Web3

from app.blockchain import (
    BlockchainClient,
    BlockchainError,
)
from app.components.bond_overview import (
    render_bond_overview,
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
    ADMIN_ADDRESS,
    BOND_TOKEN_ADDRESS,
    BOND_USD_ADDRESS,
    CHAIN_ID,
    ETHERSCAN_BASE_URL,
    ISSUER_ADDRESS,
    NETWORK_NAME,
    SEPOLIA_CHAIN_ID_HEX,
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
from app.wallet_component import (
    WalletState,
    render_wallet_connector,
)


st.set_page_config(
    page_title="Blockchain Bond Demo",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.25rem;
            font-weight: 750;
            margin-bottom: 0.15rem;
        }

        .sub-title {
            color: #6b7280;
            margin-bottom: 1.25rem;
        }

        .role-badge {
            display: inline-block;
            padding: 0.3rem 0.65rem;
            border-radius: 999px;
            border: 1px solid #9ca3af;
            font-weight: 650;
            margin-bottom: 0.75rem;
        }

        .load-time {
            color: #6b7280;
            font-size: 0.82rem;
            margin-top: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


WHITELIST_STATUS_NAMES = {
    0: "Not registered",
    1: "Pending approval",
    2: "Approved",
    3: "Rejected",
    4: "Revoked",
}


@st.cache_resource
def get_blockchain_client() -> BlockchainClient:
    """Create one reusable read-only Sepolia client."""
    return BlockchainClient()


@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def load_system_state() -> Any:
    return (
        get_blockchain_client()
        .get_system_state()
    )


@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def load_bond_overview() -> Any:
    return get_bond_overview(
        get_blockchain_client()
    )


@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def load_issuer_dashboard() -> Any:
    return get_issuer_dashboard(
        get_blockchain_client()
    )


@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def load_investor_position(
    address: str,
) -> Any:
    return get_investor_position(
        get_blockchain_client(),
        address,
        "Connected Investor",
    )


@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def load_whitelist_info(
    address: str,
) -> dict[str, Any]:
    client = get_blockchain_client()

    checksum_address = Web3.to_checksum_address(
        address
    )

    result = (
        client.tokenized_bond
        .functions
        .getWhitelistInfo(
            checksum_address
        )
        .call()
    )

    values = list(result)

    if len(values) != 4:
        raise BlockchainError(
            "getWhitelistInfo() không trả về đúng 4 trường."
        )

    status_value = int(values[0])

    return {
        "address": checksum_address,
        "status_value": status_value,
        "status_name": (
            WHITELIST_STATUS_NAMES.get(
                status_value,
                f"Unknown ({status_value})",
            )
        ),
        "is_whitelisted": bool(values[1]),
        "requested_at": int(values[2]),
        "reviewed_at": int(values[3]),
    }


@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def load_whitelist_applicants() -> list[dict[str, Any]]:
    client = get_blockchain_client()
    contract = client.tokenized_bond

    applicant_count = int(
        contract.functions
        .getWhitelistApplicantCount()
        .call()
    )

    rows: list[dict[str, Any]] = []

    for index in range(applicant_count):
        address = Web3.to_checksum_address(
            contract.functions
            .getWhitelistApplicantAt(index)
            .call()
        )

        info = load_whitelist_info(
            address
        )

        rows.append(
            {
                "No.": index + 1,
                "Address": address,
                "Status": info["status_name"],
                "Whitelisted": (
                    "Yes"
                    if info["is_whitelisted"]
                    else "No"
                ),
                "Requested At": (
                    info["requested_at"]
                    if info["requested_at"] > 0
                    else None
                ),
                "Reviewed At": (
                    info["reviewed_at"]
                    if info["reviewed_at"] > 0
                    else None
                ),
                "Etherscan": (
                    etherscan_address_url(
                        address
                    )
                ),
            }
        )

    return rows


def clear_dynamic_cache() -> None:
    load_system_state.clear()
    load_bond_overview.clear()
    load_issuer_dashboard.clear()
    load_investor_position.clear()
    load_whitelist_info.clear()
    load_whitelist_applicants.clear()


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


def determine_role(
    account: str,
) -> str:
    checksum_account = Web3.to_checksum_address(
        account
    )

    if (
        checksum_account
        == Web3.to_checksum_address(
            ADMIN_ADDRESS
        )
    ):
        return "ADMIN"

    if (
        checksum_account
        == Web3.to_checksum_address(
            ISSUER_ADDRESS
        )
    ):
        return "ISSUER"

    return "INVESTOR"


def render_heading(
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


def render_wallet_identity(
    wallet: WalletState,
    role: str,
) -> None:
    st.markdown(
        (
            '<div class="role-badge">'
            f"{role}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    identity_col_1, identity_col_2 = (
        st.columns([3, 1])
    )

    with identity_col_1:
        st.code(
            Web3.to_checksum_address(
                wallet.account
            ),
            language=None,
        )

    with identity_col_2:
        st.link_button(
            "Open wallet on Etherscan",
            etherscan_address_url(
                wallet.account
            ),
            use_container_width=True,
        )


def render_admin_home() -> None:
    render_heading(
        "Admin Portal",
        (
            "Whitelist requests and administrative "
            "subscription controls"
        ),
    )

    state = load_system_state()
    applicants = load_whitelist_applicants()

    pending_count = sum(
        1
        for row in applicants
        if row["Status"] == "Pending approval"
    )

    approved_count = sum(
        1
        for row in applicants
        if row["Status"] == "Approved"
    )

    metric_1, metric_2, metric_3, metric_4 = (
        st.columns(4)
    )

    metric_1.metric(
        "Lifecycle",
        state.lifecycle_name,
    )

    metric_2.metric(
        "All Applicants",
        len(applicants),
    )

    metric_3.metric(
        "Pending",
        pending_count,
    )

    metric_4.metric(
        "Approved",
        approved_count,
    )

    st.subheader(
        "Whitelist Applicants"
    )

    if not applicants:
        st.info(
            "Chưa có investor nào gửi yêu cầu whitelist."
        )
    else:
        st.dataframe(
            pd.DataFrame(applicants),
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

    st.subheader(
        "Admin Actions"
    )

    action_col_1, action_col_2, action_col_3 = (
        st.columns(3)
    )

    action_col_1.button(
        "Approve Pending Request",
        disabled=True,
        use_container_width=True,
    )

    action_col_2.button(
        "Reject Pending Request",
        disabled=True,
        use_container_width=True,
    )

    action_col_3.button(
        "Revoke Approved Investor",
        disabled=True,
        use_container_width=True,
    )

    pause_col_1, pause_col_2 = (
        st.columns(2)
    )

    pause_col_1.button(
        "Pause Subscription",
        disabled=True,
        use_container_width=True,
    )

    pause_col_2.button(
        "Unpause Subscription",
        disabled=True,
        use_container_width=True,
    )

    st.caption(
        "Các nút đang ở chế độ preview. "
        "Bước kế tiếp sẽ tạo transaction payload "
        "và yêu cầu ví Admin ký bằng MetaMask."
    )


def render_issuer_home() -> None:
    render_heading(
        "Issuer Portal",
        (
            "Offering management, proceeds, coupon "
            "and principal obligations"
        ),
    )

    with st.spinner(
        "Loading issuer data..."
    ):
        dashboard = (
            load_issuer_dashboard()
        )

    render_issuer_dashboard(
        dashboard
    )


def render_investor_home(
    account: str,
) -> None:
    render_heading(
        "Investor Portal",
        (
            "Whitelist registration and the connected "
            "wallet's bond position"
        ),
    )

    whitelist_info = (
        load_whitelist_info(
            account
        )
    )

    status_value = int(
        whitelist_info["status_value"]
    )

    status_name = str(
        whitelist_info["status_name"]
    )

    if status_value == 0:
        st.info(
            "Ví chưa đăng ký whitelist."
        )
    elif status_value == 1:
        st.warning(
            "Yêu cầu whitelist đang chờ Admin phê duyệt."
        )
    elif status_value == 2:
        st.success(
            "Ví đã được Admin phê duyệt whitelist."
        )
    elif status_value == 3:
        st.error(
            "Yêu cầu whitelist đã bị từ chối."
        )
    elif status_value == 4:
        st.warning(
            "Quyền whitelist của ví đã bị thu hồi."
        )

    status_col_1, status_col_2 = (
        st.columns(2)
    )

    status_col_1.metric(
        "Whitelist Status",
        status_name,
    )

    status_col_2.metric(
        "Whitelisted",
        (
            "Yes"
            if whitelist_info[
                "is_whitelisted"
            ]
            else "No"
        ),
    )

    request_allowed = (
        status_value
        in {
            0,
            3,
            4,
        }
    )

    st.button(
        "Request Whitelist",
        disabled=True,
        use_container_width=True,
        help=(
            "Transaction signing will be activated "
            "in the next step."
            if request_allowed
            else (
                "The current whitelist status "
                "does not allow a new request."
            )
        ),
    )

    with st.spinner(
        "Loading connected investor position..."
    ):
        position = (
            load_investor_position(
                account
            )
        )

    render_investor_portal(
        {
            "Connected Wallet": position,
        }
    )


def render_bond_page() -> None:
    render_heading(
        "Bond Overview",
        (
            "Public terms, lifecycle and "
            "offering progress"
        ),
    )

    with st.spinner(
        "Loading bond overview..."
    ):
        overview = load_bond_overview()

    render_bond_overview(
        overview
    )


def render_payment_page() -> None:
    render_heading(
        "Payment Schedule",
        (
            "Coupon and principal funding, "
            "distribution and default timeline"
        ),
    )

    overview = load_bond_overview()
    issuer_dashboard = (
        load_issuer_dashboard()
    )

    schedule = build_payment_schedule(
        overview,
        issuer_dashboard,
    )

    render_payment_schedule(
        schedule
    )


def render_technical_page() -> None:
    render_heading(
        "Technical Status",
        (
            "Clean Sepolia V2 deployment "
            "and contract references"
        ),
    )

    client = get_blockchain_client()
    network = client.get_network_status()
    state = load_system_state()
    contract_statuses = (
        client
        .get_all_contract_code_statuses()
    )

    metric_1, metric_2, metric_3, metric_4 = (
        st.columns(4)
    )

    metric_1.metric(
        "RPC",
        (
            "Connected"
            if network.connected
            else "Disconnected"
        ),
    )

    metric_2.metric(
        "Chain ID",
        network.chain_id,
    )

    metric_3.metric(
        "Latest Block",
        f"{network.latest_block:,}",
    )

    metric_4.metric(
        "Lifecycle",
        state.lifecycle_name,
    )

    rows = [
        {
            "Contract": item.contract_name,
            "Address": item.address,
            "Bytecode": (
                "Available"
                if item.has_code
                else "Missing"
            ),
            "Size": item.bytecode_size,
            "Etherscan": (
                etherscan_address_url(
                    item.address
                )
            ),
        }
        for item in contract_statuses
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

    st.json(
        {
            "Admin": state.admin,
            "Issuer": state.issuer,
            "Payment Token": (
                state.payment_token
            ),
            "Bond Token": state.bond_token,
            "Controller": (
                state.bond_token_controller
            ),
            "BondToken Owner": (
                state.bond_token_owner
            ),
            "BondToken Supply": (
                state.bond_token_supply
            ),
            "Total Subscribed": (
                state.total_subscribed
            ),
            "Total Raised": (
                str(
                    state.total_raised_display
                )
            ),
        }
    )


# ============================================================
# Landing page: wallet first
# ============================================================

render_heading(
    "Blockchain Bond Demo",
    (
        "Connect MetaMask to enter the role-based "
        "bond application on Ethereum Sepolia"
    ),
)

st.caption(
    "The Streamlit server never receives or stores "
    "the wallet private key."
)

wallet = render_wallet_connector(
    required_chain_id=(
        SEPOLIA_CHAIN_ID_HEX
    ),
)

if wallet.error:
    st.warning(
        wallet.error
    )

if not wallet.installed:
    st.info(
        "Cài MetaMask extension trong trình duyệt, "
        "sau đó tải lại trang."
    )
    st.stop()

if not wallet.connected:
    st.info(
        "Bước đầu tiên chỉ là kết nối ví. "
        "Ứng dụng chưa hiển thị portal trước khi "
        "MetaMask cấp quyền truy cập địa chỉ ví."
    )
    st.stop()

if not Web3.is_address(
    wallet.account
):
    st.error(
        "MetaMask không trả về địa chỉ Ethereum hợp lệ."
    )
    st.stop()

if (
    wallet.chain_id.lower()
    != SEPOLIA_CHAIN_ID_HEX.lower()
):
    st.warning(
        "MetaMask đang ở sai mạng. "
        "Bấm **Switch to Sepolia** trong khung MetaMask."
    )
    st.stop()


# ============================================================
# Role-based routing
# ============================================================

connected_account = (
    Web3.to_checksum_address(
        wallet.account
    )
)

role = determine_role(
    connected_account
)

render_wallet_identity(
    wallet,
    role,
)

with st.sidebar:
    st.header(
        "Blockchain Bond Demo"
    )

    st.write(
        f"**Role:** {role}"
    )

    st.code(
        shorten_address(
            connected_account
        ),
        language=None,
    )

    st.write(
        f"**Network:** {NETWORK_NAME}"
    )

    st.write(
        f"**Chain ID:** {CHAIN_ID}"
    )

    if role == "ADMIN":
        page_options = [
            "Admin Portal",
            "Bond Overview",
            "Technical Status",
        ]
    elif role == "ISSUER":
        page_options = [
            "Issuer Portal",
            "Bond Overview",
            "Payment Schedule",
            "Technical Status",
        ]
    else:
        page_options = [
            "Investor Portal",
            "Bond Overview",
            "Technical Status",
        ]

    page = st.radio(
        "Navigation",
        options=page_options,
    )

    st.divider()

    st.link_button(
        "Sepolia Etherscan",
        ETHERSCAN_BASE_URL,
        use_container_width=True,
    )

    st.caption(
        "Change account or network directly in MetaMask."
    )

    if st.button(
        "Refresh on-chain data",
        use_container_width=True,
    ):
        clear_dynamic_cache()
        st.rerun()

started_at = time.perf_counter()

try:
    if page == "Admin Portal":
        render_admin_home()

    elif page == "Issuer Portal":
        render_issuer_home()

    elif page == "Investor Portal":
        render_investor_home(
            connected_account
        )

    elif page == "Bond Overview":
        render_bond_page()

    elif page == "Payment Schedule":
        render_payment_page()

    elif page == "Technical Status":
        render_technical_page()

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

    st.divider()

    st.caption(
        "MetaMask provides the connected account and network. "
        "Transaction signing remains disabled in this checkpoint."
    )

except BlockchainError as exc:
    st.error(
        "Không thể đọc dữ liệu blockchain."
    )

    st.code(
        str(exc),
        language=None,
    )

except Exception as exc:
    st.error(
        "Ứng dụng gặp lỗi ngoài dự kiến."
    )

    st.code(
        str(exc),
        language=None,
    )
