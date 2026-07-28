from __future__ import annotations

from decimal import Decimal

import pandas as pd
import streamlit as st

from app.config import etherscan_address_url
from app.investor import InvestorPosition


def format_bondusd(value: Decimal) -> str:
    return f"{value:,.2f} BONDUSD"


def format_eth(value: Decimal) -> str:
    return f"{value:,.6f} ETH"


def format_boolean(value: bool) -> str:
    return "Yes" if value else "No"


def render_investor_portal(
    investor_positions: dict[str, InvestorPosition],
) -> None:
    """Render the read-only Investor Portal."""
    st.header("5. Investor Portal")

    st.caption(
        "Read-only inspection of the demo investor accounts. "
        "No wallet signing or transaction is performed."
    )

    selected_label = st.selectbox(
        "Select demo investor",
        options=list(investor_positions.keys()),
        key="investor_portal_account",
    )

    position = investor_positions[
        selected_label
    ]

    header_col_1, header_col_2 = st.columns(
        [3, 1]
    )

    with header_col_1:
        st.subheader(position.label)
        st.code(position.address, language=None)

    with header_col_2:
        st.link_button(
            "Open wallet on Etherscan",
            etherscan_address_url(
                position.address
            ),
            use_container_width=True,
        )

    if position.is_whitelisted:
        st.success(
            f"{position.label} is currently whitelisted."
        )
    else:
        st.warning(
            f"{position.label} is not whitelisted."
        )

    st.info(
        f"Investor status: **{position.position_status}**  \n"
        f"Contract lifecycle: **{position.lifecycle_name}**"
    )

    # ========================================================
    # Summary metrics
    # ========================================================

    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = (
        st.columns(4)
    )

    metric_col_1.metric(
        label="Sepolia ETH",
        value=format_eth(
            position.eth_balance
        ),
    )

    metric_col_2.metric(
        label="BondUSD Balance",
        value=format_bondusd(
            position.bond_usd_balance
        ),
    )

    metric_col_3.metric(
        label="BondToken Balance",
        value=(
            f"{position.bond_token_balance:,} DBOND26"
        ),
    )

    metric_col_4.metric(
        label="Subscribed Quantity",
        value=(
            f"{position.quantity_subscribed:,}"
        ),
    )

    (
        wallet_tab,
        position_tab,
        claims_tab,
        history_tab,
    ) = st.tabs(
        [
            "Wallet",
            "Bond Position",
            "Claimable Amounts",
            "Claim History",
        ]
    )

    # ========================================================
    # Wallet
    # ========================================================

    with wallet_tab:
        wallet_rows = [
            {
                "Asset / permission": "Sepolia ETH",
                "Value": format_eth(
                    position.eth_balance
                ),
                "Purpose": "Transaction gas",
            },
            {
                "Asset / permission": "BondUSD",
                "Value": format_bondusd(
                    position.bond_usd_balance
                ),
                "Purpose": "Payment and claims",
            },
            {
                "Asset / permission": "DBOND26",
                "Value": (
                    f"{position.bond_token_balance:,} token"
                ),
                "Purpose": "Bond ownership",
            },
            {
                "Asset / permission": (
                    "BondUSD allowance for TokenizedBond"
                ),
                "Value": format_bondusd(
                    position.bond_usd_allowance
                ),
                "Purpose": (
                    "Maximum BondUSD currently approved"
                ),
            },
        ]

        st.dataframe(
            pd.DataFrame(wallet_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Allowance only authorises the contract to transfer "
            "BondUSD up to the approved limit. It does not transfer "
            "tokens by itself."
        )

    # ========================================================
    # Position
    # ========================================================

    with position_tab:
        position_rows = [
            {
                "Indicator": "Whitelist status",
                "Value": format_boolean(
                    position.is_whitelisted
                ),
            },
            {
                "Indicator": "Subscribed quantity",
                "Value": (
                    f"{position.quantity_subscribed:,} "
                    "trái phiếu"
                ),
            },
            {
                "Indicator": "Amount paid",
                "Value": format_bondusd(
                    position.amount_paid
                ),
            },
            {
                "Indicator": "Current BondToken balance",
                "Value": (
                    f"{position.bond_token_balance:,} "
                    "DBOND26"
                ),
            },
            {
                "Indicator": "Current position status",
                "Value": position.position_status,
            },
        ]

        st.dataframe(
            pd.DataFrame(position_rows),
            use_container_width=True,
            hide_index=True,
        )

        if position.quantity_subscribed == 0:
            st.info(
                "Investor has not subscribed to the base "
                "deployment. The contract remains in Draft."
            )

    # ========================================================
    # Claimable amounts
    # ========================================================

    with claims_tab:
        claim_col_1, claim_col_2, claim_col_3, claim_col_4 = (
            st.columns(4)
        )

        claim_col_1.metric(
            label="Refund",
            value=format_bondusd(
                position.refundable_amount
            ),
        )

        claim_col_2.metric(
            label="Coupon 1",
            value=format_bondusd(
                position.claimable_coupon_1
            ),
        )

        claim_col_3.metric(
            label="Coupon 2",
            value=format_bondusd(
                position.claimable_coupon_2
            ),
        )

        claim_col_4.metric(
            label="Principal",
            value=format_bondusd(
                position.redeemable_principal
            ),
        )

        st.write(
            "**Total claimable coupon:** "
            + format_bondusd(
                position.claimable_coupon_total
            )
        )

        if (
            position.refundable_amount == 0
            and position.claimable_coupon_total == 0
            and position.redeemable_principal == 0
        ):
            st.caption(
                "No refund, coupon or principal is currently "
                "claimable for this address."
            )

    # ========================================================
    # Claim history
    # ========================================================

    with history_tab:
        history_rows = [
            {
                "Right / obligation": "Refund",
                "Completed": format_boolean(
                    position.has_claimed_refund
                ),
            },
            {
                "Right / obligation": "Coupon period 1",
                "Completed": format_boolean(
                    position.has_claimed_coupon_1
                ),
            },
            {
                "Right / obligation": "Coupon period 2",
                "Completed": format_boolean(
                    position.has_claimed_coupon_2
                ),
            },
            {
                "Right / obligation": "Principal redemption",
                "Completed": format_boolean(
                    position.has_redeemed_principal
                ),
            },
        ]

        st.dataframe(
            pd.DataFrame(history_rows),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Investor Actions")

    action_col_1, action_col_2, action_col_3, action_col_4, action_col_5 = (
        st.columns(5)
    )

    action_col_1.button(
        "Approve BondUSD",
        disabled=True,
        use_container_width=True,
        key="preview_approve",
    )

    action_col_2.button(
        "Subscribe",
        disabled=True,
        use_container_width=True,
        key="preview_subscribe",
    )

    action_col_3.button(
        "Claim Refund",
        disabled=True,
        use_container_width=True,
        key="preview_refund",
    )

    action_col_4.button(
        "Claim Coupon",
        disabled=True,
        use_container_width=True,
        key="preview_coupon",
    )

    action_col_5.button(
        "Redeem Principal",
        disabled=True,
        use_container_width=True,
        key="preview_principal",
    )

    st.caption(
        "Action buttons are intentionally disabled in read-only mode. "
        "They will be connected to MetaMask only after the dashboard "
        "and transaction validation layer are complete."
    )