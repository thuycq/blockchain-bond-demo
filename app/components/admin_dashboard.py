from __future__ import annotations

from decimal import Decimal

import pandas as pd
import streamlit as st

from app.admin import (
    AdminDashboard,
    inspect_wallet,
)
from app.blockchain import (
    BlockchainClient,
    BlockchainError,
)
from app.config import (
    etherscan_address_url,
)


def format_bondusd(
    value: Decimal,
) -> str:
    """Format a BONDUSD amount."""
    return f"{value:,.2f} BONDUSD"


def format_eth(
    value: Decimal,
) -> str:
    """Format a Sepolia ETH amount."""
    return f"{value:,.6f} ETH"


def format_boolean(
    value: bool,
) -> str:
    """Format a Boolean value."""
    return "Yes" if value else "No"


def render_admin_dashboard(
    dashboard: AdminDashboard,
    client: BlockchainClient,
) -> None:
    """Render the complete read-only Admin Dashboard."""
    st.header("7. Admin Dashboard")

    st.caption(
        "Admin manages permissioned access to the bond offering. "
        "This page is currently read-only."
    )

    header_col_1, header_col_2 = st.columns(
        [3, 1]
    )

    with header_col_1:
        st.subheader("Admin wallet")
        st.code(
            dashboard.admin_address,
            language=None,
        )

    with header_col_2:
        st.link_button(
            "Open Admin on Etherscan",
            etherscan_address_url(
                dashboard.admin_address
            ),
            use_container_width=True,
        )

    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = (
        st.columns(4)
    )

    metric_col_1.metric(
        label="Sepolia ETH",
        value=format_eth(
            dashboard.eth_balance
        ),
    )

    metric_col_2.metric(
        label="Admin BondUSD",
        value=format_bondusd(
            dashboard.bond_usd_balance
        ),
    )

    metric_col_3.metric(
        label="Whitelisted Demo Wallets",
        value=(
            f"{dashboard.whitelisted_demo_count} / "
            f"{dashboard.total_demo_accounts}"
        ),
    )

    metric_col_4.metric(
        label="Lifecycle",
        value=dashboard.lifecycle_name,
    )

    if dashboard.subscription_paused:
        st.warning(
            "Subscription is currently paused."
        )
    else:
        st.success(
            "Subscription is not paused."
        )

    known_tab, inspect_tab, controls_tab = st.tabs(
        [
            "Known Wallets",
            "Inspect Any Wallet",
            "Admin Controls",
        ]
    )

    with known_tab:
        account_rows = []

        for account in dashboard.known_accounts:
            account_rows.append(
                {
                    "Label": account.label,
                    "Role": account.role,
                    "Address": account.address,
                    "Whitelisted": format_boolean(
                        account.is_whitelisted
                    ),
                    "Subscribed": (
                        account.subscribed_quantity
                    ),
                    "Amount Paid": format_bondusd(
                        account.amount_paid
                    ),
                    "BondUSD": format_bondusd(
                        account.bond_usd_balance
                    ),
                    "DBOND26": (
                        account.bond_token_balance
                    ),
                    "Etherscan": (
                        etherscan_address_url(
                            account.address
                        )
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(account_rows),
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

        st.info(
            "Danh sách trên chỉ là các ví demo đã biết. "
            "Smart contract không giới hạn whitelist ở các địa chỉ này."
        )

    with inspect_tab:
        st.write(
            "Nhập bất kỳ địa chỉ Ethereum nào để kiểm tra "
            "whitelist và vị thế hiện tại."
        )

        wallet_address = st.text_input(
            "Wallet address",
            placeholder="0x...",
            key="admin_wallet_lookup",
        )

        inspect_clicked = st.button(
            "Inspect Wallet",
            use_container_width=True,
            key="admin_inspect_wallet",
        )

        if inspect_clicked:
            if not wallet_address.strip():
                st.warning(
                    "Hãy nhập địa chỉ ví cần kiểm tra."
                )
            else:
                try:
                    inspected = inspect_wallet(
                        client,
                        wallet_address.strip(),
                    )

                    if inspected.is_whitelisted:
                        st.success(
                            "Địa chỉ đang được whitelist."
                        )
                    else:
                        st.warning(
                            "Địa chỉ chưa được whitelist."
                        )

                    inspected_col_1, inspected_col_2 = (
                        st.columns(2)
                    )

                    with inspected_col_1:
                        st.code(
                            inspected.address,
                            language=None,
                        )

                        st.write(
                            "**Status:** "
                            f"{inspected.position_status}"
                        )

                        st.write(
                            "**Whitelisted:** "
                            f"{format_boolean(inspected.is_whitelisted)}"
                        )

                    with inspected_col_2:
                        st.write(
                            "**BondUSD:** "
                            f"{format_bondusd(inspected.bond_usd_balance)}"
                        )

                        st.write(
                            "**Subscribed:** "
                            f"{inspected.quantity_subscribed:,}"
                        )

                        st.write(
                            "**DBOND26:** "
                            f"{inspected.bond_token_balance:,}"
                        )

                        st.link_button(
                            "Open Wallet on Etherscan",
                            etherscan_address_url(
                                inspected.address
                            ),
                            use_container_width=True,
                        )

                except BlockchainError as exc:
                    st.error(
                        str(exc)
                    )

        st.caption(
            "Wallet inspection only reads public blockchain data "
            "and does not require the wallet private key."
        )

    with controls_tab:
        st.subheader("Whitelist Management")

        management_address = st.text_input(
            "Investor address",
            placeholder="0x...",
            key="admin_management_address",
        )

        whitelist_col_1, whitelist_col_2 = st.columns(
            2
        )

        whitelist_col_1.button(
            "Add to Whitelist",
            disabled=True,
            use_container_width=True,
            key="admin_add_whitelist_preview",
        )

        whitelist_col_2.button(
            "Remove from Whitelist",
            disabled=True,
            use_container_width=True,
            key="admin_remove_whitelist_preview",
        )

        st.subheader("Subscription Controls")

        pause_col_1, pause_col_2 = st.columns(
            2
        )

        pause_col_1.button(
            "Pause Subscription",
            disabled=True,
            use_container_width=True,
            key="admin_pause_preview",
        )

        pause_col_2.button(
            "Unpause Subscription",
            disabled=True,
            use_container_width=True,
            key="admin_unpause_preview",
        )

        control_rows = [
            {
                "Control": "Add wallet to whitelist",
                "Required caller": "Admin",
                "Current mode": "Read-only",
            },
            {
                "Control": "Remove wallet from whitelist",
                "Required caller": "Admin",
                "Current mode": "Read-only",
            },
            {
                "Control": "Pause subscription",
                "Required caller": "Admin",
                "Current mode": "Read-only",
            },
            {
                "Control": "Unpause subscription",
                "Required caller": "Admin",
                "Current mode": "Read-only",
            },
        ]

        st.dataframe(
            pd.DataFrame(control_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Các nút sẽ được kích hoạt trong giai đoạn MetaMask. "
            "Admin sẽ ký giao dịch setWhitelist, pauseSubscription "
            "hoặc unpauseSubscription bằng chính ví Admin."
        )