from __future__ import annotations

import sys
import time
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

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
from app.transactions import (
    TransactionPreparationError,
    build_action_transaction,
    wait_for_action_receipt,
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


VIETNAM_TIMEZONE = ZoneInfo(
    "Asia/Ho_Chi_Minh"
)

ZERO_ADDRESS = (
    "0x0000000000000000000000000000000000000000"
)

WHITELIST_STATUS_NAMES = {
    0: "Not registered",
    1: "Pending approval",
    2: "Approved",
    3: "Rejected",
    4: "Revoked",
}


# ============================================================
# Session state
# ============================================================

if (
    "wallet_transaction_request"
    not in st.session_state
):
    st.session_state[
        "wallet_transaction_request"
    ] = None

if (
    "last_wallet_transaction"
    not in st.session_state
):
    st.session_state[
        "last_wallet_transaction"
    ] = None


# ============================================================
# Cached readers
# ============================================================

@st.cache_resource
def get_blockchain_client() -> BlockchainClient:
    return BlockchainClient()


@st.cache_data(
    ttl=15,
    show_spinner=False,
)
def load_system_state() -> Any:
    return (
        get_blockchain_client()
        .get_system_state()
    )


@st.cache_data(
    ttl=15,
    show_spinner=False,
)
def load_bond_overview() -> Any:
    return get_bond_overview(
        get_blockchain_client()
    )


@st.cache_data(
    ttl=15,
    show_spinner=False,
)
def load_issuer_dashboard() -> Any:
    return get_issuer_dashboard(
        get_blockchain_client()
    )


@st.cache_data(
    ttl=15,
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
    ttl=15,
    show_spinner=False,
)
def load_whitelist_info(
    address: str,
) -> dict[str, Any]:
    client = get_blockchain_client()

    checksum_address = (
        Web3.to_checksum_address(
            address
        )
    )

    result = list(
        client.tokenized_bond
        .functions
        .getWhitelistInfo(
            checksum_address
        )
        .call()
    )

    if len(result) != 4:
        raise BlockchainError(
            "getWhitelistInfo() không trả về đúng 4 trường."
        )

    status_value = int(
        result[0]
    )

    return {
        "address":
            checksum_address,
        "status_value":
            status_value,
        "status_name":
            WHITELIST_STATUS_NAMES.get(
                status_value,
                f"Unknown ({status_value})",
            ),
        "is_whitelisted":
            bool(result[1]),
        "requested_at":
            int(result[2]),
        "reviewed_at":
            int(result[3]),
    }


@st.cache_data(
    ttl=15,
    show_spinner=False,
)
def load_whitelist_applicants(
) -> list[dict[str, Any]]:
    client = get_blockchain_client()
    contract = client.tokenized_bond

    count = int(
        contract.functions
        .getWhitelistApplicantCount()
        .call()
    )

    rows: list[dict[str, Any]] = []

    for index in range(count):
        address = (
            Web3.to_checksum_address(
                contract.functions
                .getWhitelistApplicantAt(
                    index
                )
                .call()
            )
        )

        info = load_whitelist_info(
            address
        )

        rows.append(
            {
                "index": index,
                "address": address,
                "status_value":
                    info["status_value"],
                "status_name":
                    info["status_name"],
                "is_whitelisted":
                    info["is_whitelisted"],
                "requested_at":
                    info["requested_at"],
                "reviewed_at":
                    info["reviewed_at"],
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


# ============================================================
# Formatting and role helpers
# ============================================================

def format_timestamp(
    timestamp: int,
) -> str:
    if timestamp <= 0:
        return "—"

    utc_time = datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    )

    local_time = utc_time.astimezone(
        VIETNAM_TIMEZONE
    )

    return local_time.strftime(
        "%d/%m/%Y %H:%M:%S"
    )


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
    checksum_account = (
        Web3.to_checksum_address(
            account
        )
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

    col_1, col_2 = st.columns(
        [3, 1]
    )

    with col_1:
        st.code(
            Web3.to_checksum_address(
                wallet.account
            ),
            language=None,
        )

    with col_2:
        st.link_button(
            "Open wallet on Etherscan",
            etherscan_address_url(
                wallet.account
            ),
            use_container_width=True,
        )


def transaction_waiting() -> bool:
    return isinstance(
        st.session_state.get(
            "wallet_transaction_request"
        ),
        dict,
    )


# ============================================================
# Transaction queue and receipt handling
# ============================================================

def queue_action(
    *,
    action: str,
    sender: str,
    arguments: list[Any] | None = None,
    expected_event_args: (
        dict[str, Any] | None
    ) = None,
) -> None:
    try:
        request = build_action_transaction(
            get_blockchain_client(),
            action=action,
            sender=sender,
            arguments=arguments,
            expected_event_args=(
                expected_event_args
            ),
        )

        st.session_state[
            "wallet_transaction_request"
        ] = request

        st.session_state[
            "last_wallet_transaction"
        ] = None

        st.rerun()

    except TransactionPreparationError as exc:
        st.error(
            str(exc)
        )


def process_wallet_transaction(
    wallet: WalletState,
    connected_account: str,
) -> None:
    pending_request = (
        st.session_state.get(
            "wallet_transaction_request"
        )
    )

    if not isinstance(
        pending_request,
        dict,
    ):
        return

    expected_request_id = str(
        pending_request.get(
            "requestId",
            "",
        )
    )

    if (
        not expected_request_id
        or (
            wallet
            .transaction_request_id
            != expected_request_id
        )
    ):
        return

    if (
        wallet.transaction_status
        in {
            "rejected",
            "failed",
        }
    ):
        status = (
            wallet.transaction_status
        )

        message = (
            wallet.transaction_error
            or (
                "Người dùng đã từ chối giao dịch."
                if status == "rejected"
                else (
                    "MetaMask không thể gửi giao dịch."
                )
            )
        )

        st.session_state[
            "last_wallet_transaction"
        ] = {
            "action":
                pending_request.get(
                    "action"
                ),
            "label":
                pending_request.get(
                    "label"
                ),
            "status":
                status,
            "message":
                message,
        }

        st.session_state[
            "wallet_transaction_request"
        ] = None

        st.rerun()

    if (
        wallet.transaction_status
        != "submitted"
    ):
        return

    with st.spinner(
        "MetaMask đã gửi giao dịch. "
        "Đang chờ Sepolia xác nhận..."
    ):
        result = wait_for_action_receipt(
            get_blockchain_client(),
            request=pending_request,
            transaction_hash=(
                wallet.transaction_hash
            ),
        )

    st.session_state[
        "last_wallet_transaction"
    ] = result

    st.session_state[
        "wallet_transaction_request"
    ] = None

    clear_dynamic_cache()
    st.rerun()


def render_transaction_feedback() -> None:
    result = st.session_state.get(
        "last_wallet_transaction"
    )

    if not isinstance(
        result,
        dict,
    ):
        return

    label = str(
        result.get(
            "label",
            "Transaction",
        )
    )

    status = str(
        result.get(
            "status",
            "",
        )
    )

    message = str(
        result.get(
            "message",
            "",
        )
    )

    if status == "confirmed":
        st.success(
            f"{label}: {message}"
        )
    elif status == "submitted":
        st.warning(
            f"{label}: {message}"
        )
    elif status == "rejected":
        st.warning(
            f"{label}: {message}"
        )
    elif status == "failed":
        st.error(
            f"{label}: {message}"
        )

    transaction_hash = str(
        result.get(
            "transactionHash",
            "",
        )
        or ""
    )

    etherscan_url = str(
        result.get(
            "etherscanUrl",
            "",
        )
        or ""
    )

    if transaction_hash:
        st.code(
            transaction_hash,
            language=None,
        )

    if etherscan_url:
        st.link_button(
            "Open transaction on Etherscan",
            etherscan_url,
        )


# ============================================================
# Admin Portal
# ============================================================

def render_admin_portal(
    account: str,
) -> None:
    render_heading(
        "Admin Portal",
        (
            "BondUSD test-token funding, whitelist "
            "management and lifecycle controls"
        ),
    )

    client = get_blockchain_client()
    contract = client.tokenized_bond
    state = load_system_state()
    applicants = load_whitelist_applicants()
    busy = transaction_waiting()

    pending = [
        item
        for item in applicants
        if item["status_value"] == 1
    ]

    approved = [
        item
        for item in applicants
        if item["status_value"] == 2
    ]

    metric_1, metric_2, metric_3, metric_4 = (
        st.columns(4)
    )

    metric_1.metric(
        "Lifecycle",
        state.lifecycle_name,
    )
    metric_2.metric(
        "Applicants",
        len(applicants),
    )
    metric_3.metric(
        "Pending",
        len(pending),
    )
    metric_4.metric(
        "Approved",
        len(approved),
    )

    (
        whitelist_tab,
        token_tab,
        lifecycle_tab,
    ) = st.tabs(
        [
            "Whitelist",
            "Mint BondUSD",
            "Lifecycle Controls",
        ]
    )

    with whitelist_tab:
        st.subheader(
            "Whitelist Applicants"
        )

        if applicants:
            rows = [
                {
                    "No.":
                        item["index"] + 1,
                    "Address":
                        item["address"],
                    "Status":
                        item["status_name"],
                    "Whitelisted":
                        (
                            "Yes"
                            if item[
                                "is_whitelisted"
                            ]
                            else "No"
                        ),
                    "Requested At":
                        format_timestamp(
                            item["requested_at"]
                        ),
                    "Reviewed At":
                        format_timestamp(
                            item["reviewed_at"]
                        ),
                    "Etherscan":
                        etherscan_address_url(
                            item["address"]
                        ),
                }
                for item in applicants
            ]

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Etherscan": (
                        st.column_config
                        .LinkColumn(
                            "Etherscan",
                            display_text="Open",
                        )
                    ),
                },
            )
        else:
            st.info(
                "Chưa có investor nào gửi yêu cầu whitelist."
            )

        st.subheader(
            "Pending Requests"
        )

        if pending:
            pending_addresses = [
                item["address"]
                for item in pending
            ]

            selected_pending = st.selectbox(
                "Select pending investor",
                options=pending_addresses,
                format_func=shorten_address,
                key="admin_pending_investor",
            )

            approve_col, reject_col = (
                st.columns(2)
            )

            if approve_col.button(
                "Approve Whitelist",
                disabled=busy,
                type="primary",
                use_container_width=True,
                key="admin_approve_whitelist",
            ):
                queue_action(
                    action="approveWhitelist",
                    sender=account,
                    arguments=[
                        selected_pending
                    ],
                    expected_event_args={
                        "investor":
                            selected_pending,
                        "admin":
                            account,
                    },
                )

            if reject_col.button(
                "Reject Whitelist",
                disabled=busy,
                use_container_width=True,
                key="admin_reject_whitelist",
            ):
                queue_action(
                    action="rejectWhitelist",
                    sender=account,
                    arguments=[
                        selected_pending
                    ],
                    expected_event_args={
                        "investor":
                            selected_pending,
                        "admin":
                            account,
                    },
                )
        else:
            st.caption(
                "No Pending request is available."
            )

        st.subheader(
            "Approved Investors"
        )

        if approved:
            approved_addresses = [
                item["address"]
                for item in approved
            ]

            selected_approved = st.selectbox(
                "Select approved investor",
                options=approved_addresses,
                format_func=shorten_address,
                key="admin_approved_investor",
            )

            revoke_confirmation = st.checkbox(
                "I confirm that the selected investor "
                "should be revoked.",
                key="admin_revoke_confirm",
            )

            if st.button(
                "Revoke Whitelist",
                disabled=(
                    busy
                    or not revoke_confirmation
                ),
                use_container_width=True,
                key="admin_revoke_whitelist",
            ):
                queue_action(
                    action="revokeWhitelist",
                    sender=account,
                    arguments=[
                        selected_approved
                    ],
                    expected_event_args={
                        "investor":
                            selected_approved,
                        "admin":
                            account,
                    },
                )
        else:
            st.caption(
                "No Approved investor is available."
            )

    with token_tab:
        st.subheader(
            "Mint Test BondUSD"
        )

        st.info(
            "BondUSD is a Sepolia test token. "
            "The Admin/Owner may mint it to Investors "
            "or the Issuer for demo transactions."
        )

        recipient = st.text_input(
            "Recipient address",
            placeholder="0x...",
            key="admin_mint_recipient",
        ).strip()

        amount = int(
            st.number_input(
                "Amount (BONDUSD)",
                min_value=1,
                value=10_000,
                step=100,
                key="admin_mint_amount",
            )
        )

        recipient_valid = (
            Web3.is_address(
                recipient
            )
        )

        if recipient and not recipient_valid:
            st.warning(
                "Recipient address is not valid."
            )

        if st.button(
            "Mint BondUSD",
            disabled=(
                busy
                or not recipient_valid
            ),
            type="primary",
            use_container_width=True,
            key="admin_mint_bondusd",
        ):
            decimals = int(
                client.bond_usd.functions
                .decimals()
                .call()
            )

            raw_amount = (
                amount
                * 10**decimals
            )

            checksum_recipient = (
                Web3.to_checksum_address(
                    recipient
                )
            )

            queue_action(
                action="mintBondUSD",
                sender=account,
                arguments=[
                    checksum_recipient,
                    raw_amount,
                ],
                expected_event_args={
                    "from":
                        ZERO_ADDRESS,
                    "to":
                        checksum_recipient,
                    "value":
                        raw_amount,
                },
            )

    with lifecycle_tab:
        st.subheader(
            "Subscription Controls"
        )

        pause_col, unpause_col = (
            st.columns(2)
        )

        if pause_col.button(
            "Pause Subscription",
            disabled=(
                busy
                or state.subscription_paused
                or (
                    state.lifecycle_value
                    not in (0, 1)
                )
            ),
            use_container_width=True,
            key="admin_pause_subscription",
        ):
            queue_action(
                action="pauseSubscription",
                sender=account,
            )

        if unpause_col.button(
            "Unpause Subscription",
            disabled=(
                busy
                or not state.subscription_paused
                or (
                    state.lifecycle_value
                    not in (0, 1)
                )
            ),
            use_container_width=True,
            key="admin_unpause_subscription",
        ):
            queue_action(
                action="unpauseSubscription",
                sender=account,
            )

        st.subheader(
            "Permissionless Lifecycle Actions"
        )

        can_finalize = bool(
            contract.functions
            .canFinalize()
            .call()
        )

        can_close = bool(
            contract.functions
            .canClose()
            .call()
        )

        latest_block = (
            client.web3.eth.get_block(
                "latest"
            )
        )

        current_timestamp = int(
            latest_block["timestamp"]
        )

        maturity = int(
            contract.functions
            .maturity()
            .call()
        )

        grace_period = int(
            contract.functions
            .GRACE_PERIOD()
            .call()
        )

        can_mark_matured = (
            state.lifecycle_value == 3
            and maturity > 0
            and current_timestamp >= maturity
        )

        finalize_confirm = st.checkbox(
            "I understand that finalizing changes the offering "
            "to Active or Failed and cannot be undone.",
            key="admin_finalize_confirm",
        )

        if st.button(
            "Finalize Offering",
            disabled=(
                busy
                or not can_finalize
                or not finalize_confirm
            ),
            type="primary",
            use_container_width=True,
            key="admin_finalize_offering",
        ):
            queue_action(
                action="finalizeOffering",
                sender=account,
            )

        if st.button(
            "Mark Bond Matured",
            disabled=(
                busy
                or not can_mark_matured
            ),
            use_container_width=True,
            key="admin_mark_matured",
        ):
            queue_action(
                action="markMatured",
                sender=account,
            )

        st.subheader(
            "Default Monitoring"
        )

        default_cols = st.columns(3)

        for period in (1, 2):
            due = int(
                contract.functions
                .couponDue(period)
                .call()
            )

            required = int(
                contract.functions
                .couponRequired(period)
                .call()
            )

            funded = int(
                contract.functions
                .couponFunded(period)
                .call()
            )

            defaulted = bool(
                contract.functions
                .couponDefaulted(period)
                .call()
            )

            eligible = (
                state.lifecycle_value
                in (3, 4)
                and due > 0
                and (
                    current_timestamp
                    >= due + grace_period
                )
                and funded < required
                and not defaulted
            )

            with default_cols[
                period - 1
            ]:
                st.write(
                    f"**Coupon {period}**"
                )

                st.caption(
                    (
                        "Eligible for default"
                        if eligible
                        else "Not eligible"
                    )
                )

                if st.button(
                    f"Mark Coupon {period} Default",
                    disabled=(
                        busy
                        or not eligible
                    ),
                    use_container_width=True,
                    key=(
                        "admin_mark_coupon_"
                        f"default_{period}"
                    ),
                ):
                    queue_action(
                        action=(
                            "markCouponDefault"
                        ),
                        sender=account,
                        arguments=[
                            period
                        ],
                        expected_event_args={
                            "period":
                                period,
                        },
                    )

        principal_required = int(
            contract.functions
            .principalRequired()
            .call()
        )

        principal_funded = int(
            contract.functions
            .principalFunded()
            .call()
        )

        principal_defaulted = bool(
            contract.functions
            .principalDefaulted()
            .call()
        )

        principal_default_eligible = (
            state.lifecycle_value
            in (3, 4)
            and maturity > 0
            and (
                current_timestamp
                >= maturity + grace_period
            )
            and (
                principal_funded
                < principal_required
            )
            and not principal_defaulted
        )

        with default_cols[2]:
            st.write(
                "**Principal**"
            )

            st.caption(
                (
                    "Eligible for default"
                    if (
                        principal_default_eligible
                    )
                    else "Not eligible"
                )
            )

            if st.button(
                "Mark Principal Default",
                disabled=(
                    busy
                    or not (
                        principal_default_eligible
                    )
                ),
                use_container_width=True,
                key="admin_mark_principal_default",
            ):
                queue_action(
                    action=(
                        "markPrincipalDefault"
                    ),
                    sender=account,
                )

        st.subheader(
            "Close Bond"
        )

        close_confirm = st.checkbox(
            "I understand that Closed is the final lifecycle state.",
            key="admin_close_confirm",
        )

        if st.button(
            "Close Bond",
            disabled=(
                busy
                or not can_close
                or not close_confirm
            ),
            use_container_width=True,
            key="admin_close_bond",
        ):
            queue_action(
                action="closeBond",
                sender=account,
            )


# ============================================================
# Issuer Portal
# ============================================================

def render_issuer_portal(
    account: str,
) -> None:
    render_heading(
        "Issuer Portal",
        (
            "Offering management, proceeds, coupon "
            "and principal funding"
        ),
    )

    client = get_blockchain_client()
    contract = client.tokenized_bond
    dashboard = (
        load_issuer_dashboard()
    )
    busy = transaction_waiting()

    render_issuer_dashboard(
        dashboard
    )

    st.subheader(
        "Issuer Transactions"
    )

    action_col_1, action_col_2, action_col_3 = (
        st.columns(3)
    )

    if action_col_1.button(
        "Open Subscription",
        disabled=(
            busy
            or not (
                dashboard
                .can_open_subscription
            )
        ),
        type="primary",
        use_container_width=True,
        key="issuer_open_subscription",
    ):
        queue_action(
            action="openSubscription",
            sender=account,
        )

    finalize_confirm = st.checkbox(
        "Confirm offering finalization.",
        key="issuer_finalize_confirm",
    )

    if action_col_2.button(
        "Finalize Offering",
        disabled=(
            busy
            or not dashboard.can_finalize
            or not finalize_confirm
        ),
        use_container_width=True,
        key="issuer_finalize_offering",
    ):
        queue_action(
            action="finalizeOffering",
            sender=account,
        )

    if action_col_3.button(
        "Withdraw Proceeds",
        disabled=(
            busy
            or not (
                dashboard
                .can_withdraw_proceeds
            )
        ),
        use_container_width=True,
        key="issuer_withdraw_proceeds",
    ):
        queue_action(
            action="withdrawProceeds",
            sender=account,
            expected_event_args={
                "issuer":
                    account,
            },
        )

    st.subheader(
        "Coupon Funding"
    )

    allowance_raw = int(
        client.bond_usd.functions
        .allowance(
            account,
            TOKENIZED_BOND_ADDRESS,
        )
        .call()
    )

    coupon_columns = st.columns(2)

    for period in (1, 2):
        required_raw = int(
            contract.functions
            .couponRequired(period)
            .call()
        )

        funded_raw = int(
            contract.functions
            .couponFunded(period)
            .call()
        )

        obligation = (
            dashboard.coupon_1
            if period == 1
            else dashboard.coupon_2
        )

        with coupon_columns[
            period - 1
        ]:
            st.write(
                f"**Coupon {period}**"
            )

            st.write(
                (
                    f"Required: "
                    f"{obligation.required:,.2f} "
                    "BONDUSD"
                )
            )

            approve_ready = (
                required_raw > 0
                and funded_raw == 0
                and (
                    allowance_raw
                    < required_raw
                )
            )

            if st.button(
                f"Approve Coupon {period}",
                disabled=(
                    busy
                    or not approve_ready
                ),
                use_container_width=True,
                key=(
                    "issuer_approve_coupon_"
                    f"{period}"
                ),
            ):
                queue_action(
                    action="approveBondUSD",
                    sender=account,
                    arguments=[
                        TOKENIZED_BOND_ADDRESS,
                        required_raw,
                    ],
                    expected_event_args={
                        "owner":
                            account,
                        "spender":
                            TOKENIZED_BOND_ADDRESS,
                        "value":
                            required_raw,
                    },
                )

            deposit_ready = (
                obligation.can_deposit
                and (
                    allowance_raw
                    >= required_raw
                )
            )

            if st.button(
                f"Deposit Coupon {period}",
                disabled=(
                    busy
                    or not deposit_ready
                ),
                type="primary",
                use_container_width=True,
                key=(
                    "issuer_deposit_coupon_"
                    f"{period}"
                ),
            ):
                queue_action(
                    action="depositCoupon",
                    sender=account,
                    arguments=[
                        period
                    ],
                    expected_event_args={
                        "period":
                            period,
                        "amount":
                            required_raw,
                    },
                )

    st.subheader(
        "Principal Funding"
    )

    principal_required_raw = int(
        contract.functions
        .principalRequired()
        .call()
    )

    principal_funded_raw = int(
        contract.functions
        .principalFunded()
        .call()
    )

    principal_approve_ready = (
        principal_required_raw > 0
        and principal_funded_raw == 0
        and (
            allowance_raw
            < principal_required_raw
        )
    )

    principal_col_1, principal_col_2 = (
        st.columns(2)
    )

    if principal_col_1.button(
        "Approve Principal",
        disabled=(
            busy
            or not (
                principal_approve_ready
            )
        ),
        use_container_width=True,
        key="issuer_approve_principal",
    ):
        queue_action(
            action="approveBondUSD",
            sender=account,
            arguments=[
                TOKENIZED_BOND_ADDRESS,
                principal_required_raw,
            ],
            expected_event_args={
                "owner":
                    account,
                "spender":
                    TOKENIZED_BOND_ADDRESS,
                "value":
                    principal_required_raw,
            },
        )

    principal_deposit_ready = (
        dashboard.principal.can_deposit
        and (
            allowance_raw
            >= principal_required_raw
        )
    )

    if principal_col_2.button(
        "Deposit Principal",
        disabled=(
            busy
            or not (
                principal_deposit_ready
            )
        ),
        type="primary",
        use_container_width=True,
        key="issuer_deposit_principal",
    ):
        queue_action(
            action="depositPrincipal",
            sender=account,
            expected_event_args={
                "amount":
                    principal_required_raw,
            },
        )

    st.caption(
        "Funding is a two-transaction ERC-20 flow: "
        "Approve BondUSD first, then call the deposit function."
    )


# ============================================================
# Investor Portal
# ============================================================

def render_investor_portal_page(
    account: str,
) -> None:
    render_heading(
        "Investor Portal",
        (
            "Whitelist registration, BondUSD approval, "
            "subscription and investor claims"
        ),
    )

    client = get_blockchain_client()
    contract = client.tokenized_bond
    info = load_whitelist_info(
        account
    )
    position = load_investor_position(
        account
    )
    overview = load_bond_overview()
    state = load_system_state()
    busy = transaction_waiting()

    status_value = int(
        info["status_value"]
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
            "Ví đã được phê duyệt whitelist."
        )
    elif status_value == 3:
        st.error(
            "Yêu cầu whitelist đã bị từ chối."
        )
    elif status_value == 4:
        st.warning(
            "Quyền whitelist đã bị thu hồi."
        )

    status_col_1, status_col_2 = (
        st.columns(2)
    )

    status_col_1.metric(
        "Whitelist Status",
        info["status_name"],
    )

    status_col_2.metric(
        "Whitelisted",
        (
            "Yes"
            if info[
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

    if st.button(
        "Request Whitelist",
        disabled=(
            busy
            or not request_allowed
        ),
        type="primary",
        use_container_width=True,
        key="investor_request_whitelist",
    ):
        queue_action(
            action="requestWhitelist",
            sender=account,
            expected_event_args={
                "investor":
                    account,
            },
        )

    st.divider()

    render_investor_portal(
        position
    )

    st.subheader(
        "Subscribe Bond"
    )

    remaining_supply = max(
        int(
            overview.max_supply
        )
        - int(
            state.total_subscribed
        ),
        0,
    )

    subscription_open = bool(
        contract.functions
        .isSubscriptionOpen()
        .call()
    )

    quantity = int(
        st.number_input(
            "Bond quantity",
            min_value=1,
            value=1,
            step=1,
            disabled=(
                remaining_supply == 0
            ),
            key="investor_subscribe_quantity",
        )
    )

    quantity_within_supply = (
        quantity <= remaining_supply
    )

    issue_price_raw = int(
        contract.functions
        .ISSUE_PRICE()
        .call()
    )

    payment_raw = (
        quantity
        * issue_price_raw
    )

    balance_raw = int(
        client.bond_usd.functions
        .balanceOf(account)
        .call()
    )

    allowance_raw = int(
        client.bond_usd.functions
        .allowance(
            account,
            TOKENIZED_BOND_ADDRESS,
        )
        .call()
    )

    decimals = int(
        client.bond_usd.functions
        .decimals()
        .call()
    )

    payment_display = (
        Decimal(payment_raw)
        / Decimal(
            10**decimals
        )
    )

    st.write(
        (
            f"Payment required: "
            f"**{payment_display:,.2f} BONDUSD**"
        )
    )

    purchase_col_1, purchase_col_2 = (
        st.columns(2)
    )

    approve_ready = (
        info["is_whitelisted"]
        and subscription_open
        and remaining_supply > 0
        and quantity_within_supply
        and balance_raw >= payment_raw
        and allowance_raw < payment_raw
    )

    if purchase_col_1.button(
        "Approve Exact BondUSD",
        disabled=(
            busy
            or not approve_ready
        ),
        use_container_width=True,
        key="investor_approve_bondusd",
    ):
        queue_action(
            action="approveBondUSD",
            sender=account,
            arguments=[
                TOKENIZED_BOND_ADDRESS,
                payment_raw,
            ],
            expected_event_args={
                "owner":
                    account,
                "spender":
                    TOKENIZED_BOND_ADDRESS,
                "value":
                    payment_raw,
            },
        )

    subscribe_ready = (
        info["is_whitelisted"]
        and subscription_open
        and remaining_supply > 0
        and quantity_within_supply
        and balance_raw >= payment_raw
        and allowance_raw >= payment_raw
    )

    if purchase_col_2.button(
        "Subscribe",
        disabled=(
            busy
            or not subscribe_ready
        ),
        type="primary",
        use_container_width=True,
        key="investor_subscribe",
    ):
        queue_action(
            action="subscribe",
            sender=account,
            arguments=[
                quantity
            ],
            expected_event_args={
                "investor":
                    account,
                "quantity":
                    quantity,
                "payment":
                    payment_raw,
            },
        )

    if not info["is_whitelisted"]:
        st.caption(
            "The Investor must be Approved before purchasing."
        )
    elif not subscription_open:
        st.caption(
            "Subscription is not currently open."
        )
    elif not quantity_within_supply:
        st.caption(
            f"Only {remaining_supply} bond(s) remain available."
        )
    elif balance_raw < payment_raw:
        st.caption(
            "The wallet does not have enough BondUSD."
        )
    elif allowance_raw < payment_raw:
        st.caption(
            "Approve the exact BondUSD amount before subscribing."
        )

    st.subheader(
        "Claims and Redemption"
    )

    claim_col_1, claim_col_2, claim_col_3, claim_col_4 = (
        st.columns(4)
    )

    if claim_col_1.button(
        "Claim Refund",
        disabled=(
            busy
            or (
                position.refundable_amount
                <= 0
            )
        ),
        use_container_width=True,
        key="investor_claim_refund",
    ):
        queue_action(
            action="claimRefund",
            sender=account,
            expected_event_args={
                "investor":
                    account,
            },
        )

    if claim_col_2.button(
        "Claim Coupon 1",
        disabled=(
            busy
            or (
                position
                .claimable_coupon_1
                <= 0
            )
        ),
        use_container_width=True,
        key="investor_claim_coupon_1",
    ):
        queue_action(
            action="claimCoupon",
            sender=account,
            arguments=[
                1
            ],
            expected_event_args={
                "period":
                    1,
                "investor":
                    account,
            },
        )

    if claim_col_3.button(
        "Claim Coupon 2",
        disabled=(
            busy
            or (
                position
                .claimable_coupon_2
                <= 0
            )
        ),
        use_container_width=True,
        key="investor_claim_coupon_2",
    ):
        queue_action(
            action="claimCoupon",
            sender=account,
            arguments=[
                2
            ],
            expected_event_args={
                "period":
                    2,
                "investor":
                    account,
            },
        )

    if claim_col_4.button(
        "Redeem Principal",
        disabled=(
            busy
            or (
                position
                .redeemable_principal
                <= 0
            )
        ),
        use_container_width=True,
        key="investor_redeem_principal",
    ):
        queue_action(
            action="redeemPrincipal",
            sender=account,
            expected_event_args={
                "investor":
                    account,
            },
        )


# ============================================================
# Shared pages
# ============================================================

def render_bond_page() -> None:
    render_heading(
        "Bond Overview",
        (
            "Public terms, lifecycle and "
            "offering progress"
        ),
    )

    render_bond_overview(
        load_bond_overview()
    )


def render_payment_page() -> None:
    render_heading(
        "Payment Schedule",
        (
            "Coupon and principal funding, "
            "distribution and default timeline"
        ),
    )

    render_payment_schedule(
        build_payment_schedule(
            load_bond_overview(),
            load_issuer_dashboard(),
        )
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

    statuses = (
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
            "Contract":
                item.contract_name,
            "Address":
                item.address,
            "Bytecode":
                (
                    "Available"
                    if item.has_code
                    else "Missing"
                ),
            "Size":
                item.bytecode_size,
            "Etherscan":
                etherscan_address_url(
                    item.address
                ),
        }
        for item in statuses
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
            "Admin":
                state.admin,
            "Issuer":
                state.issuer,
            "Payment Token":
                state.payment_token,
            "Bond Token":
                state.bond_token,
            "Controller":
                state
                .bond_token_controller,
            "BondToken Owner":
                state.bond_token_owner,
            "BondToken Supply":
                state.bond_token_supply,
            "Total Subscribed":
                state.total_subscribed,
            "Total Raised":
                str(
                    state
                    .total_raised_display
                ),
            "Escrow":
                str(
                    state
                    .escrow_balance_display
                ),
        }
    )


# ============================================================
# Wallet-first landing
# ============================================================

render_heading(
    "Blockchain Bond Demo",
    (
        "Connect MetaMask to enter the role-based "
        "bond application on Ethereum Sepolia"
    ),
)

st.caption(
    "Private keys remain inside MetaMask. "
    "The Streamlit server prepares calldata and "
    "verifies public receipts only."
)

pending_browser_request = (
    st.session_state.get(
        "wallet_transaction_request"
    )
)

if isinstance(
    pending_browser_request,
    dict,
):
    # Only browser-required string fields are sent to JavaScript.
    # Large uint256 values remain in Python Session State to avoid
    # JavaScript number-precision loss.
    pending_browser_request = {
        key: pending_browser_request.get(key)
        for key in (
            "requestId",
            "action",
            "label",
            "from",
            "to",
            "data",
            "value",
            "gas",
        )
    }

wallet = render_wallet_connector(
    required_chain_id=(
        SEPOLIA_CHAIN_ID_HEX
    ),
    transaction_request=(
        pending_browser_request
    ),
)

if wallet.error:
    st.warning(
        wallet.error
    )

if not wallet.installed:
    st.info(
        "Install the MetaMask browser extension, "
        "then reload this page."
    )
    st.stop()

if not wallet.connected:
    st.info(
        "Connect MetaMask to continue."
    )
    st.stop()

if not Web3.is_address(
    wallet.account
):
    st.error(
        "MetaMask did not return a valid Ethereum address."
    )
    st.stop()

if (
    wallet.chain_id.lower()
    != SEPOLIA_CHAIN_ID_HEX.lower()
):
    st.warning(
        "MetaMask is connected to the wrong network. "
        "Use **Switch to Sepolia** in the wallet panel."
    )
    st.stop()


connected_account = (
    Web3.to_checksum_address(
        wallet.account
    )
)

role = determine_role(
    connected_account
)


# Cancel a queued payload when the account changes before signing.
pending_request = (
    st.session_state.get(
        "wallet_transaction_request"
    )
)

if isinstance(
    pending_request,
    dict,
):
    expected_sender = str(
        pending_request.get(
            "from",
            "",
        )
    )

    if (
        not Web3.is_address(
            expected_sender
        )
        or (
            Web3.to_checksum_address(
                expected_sender
            )
            != connected_account
        )
    ):
        st.session_state[
            "wallet_transaction_request"
        ] = None

        st.session_state[
            "last_wallet_transaction"
        ] = {
            "label":
                "Prepared transaction",
            "status":
                "failed",
            "message": (
                "MetaMask account changed before signing. "
                "The prepared transaction was cancelled."
            ),
        }

        st.rerun()


process_wallet_transaction(
    wallet,
    connected_account,
)

render_wallet_identity(
    wallet,
    role,
)

render_transaction_feedback()

if transaction_waiting():
    st.info(
        "A transaction is waiting for confirmation in MetaMask."
    )


# ============================================================
# Role-specific navigation
# ============================================================

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
            "Payment Schedule",
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
            "Payment Schedule",
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


# ============================================================
# Routing
# ============================================================

started_at = time.perf_counter()

try:
    if page == "Admin Portal":
        render_admin_portal(
            connected_account
        )
    elif page == "Issuer Portal":
        render_issuer_portal(
            connected_account
        )
    elif page == "Investor Portal":
        render_investor_portal_page(
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
            f"Page load time: "
            f"{elapsed:.3f} seconds"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.divider()

    st.caption(
        "Every state-changing action is signed in MetaMask "
        "and verified from its Sepolia transaction receipt."
    )

except BlockchainError as exc:
    st.error(
        "Không thể xử lý dữ liệu blockchain."
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
