from __future__ import annotations

from decimal import Decimal

import pandas as pd
import streamlit as st

from app.config import (
    etherscan_address_url,
)
from app.investor import (
    InvestorPosition,
)


def format_bondusd(
    value: Decimal,
) -> str:
    return f"{value:,.2f} BONDUSD"


def format_eth(
    value: Decimal,
) -> str:
    return f"{value:,.6f} ETH"


def format_boolean(
    value: bool,
) -> str:
    return "Yes" if value else "No"


def render_investor_portal(
    position: InvestorPosition,
) -> None:
    """Render read-only details for the connected Investor wallet."""
    st.subheader(
        "Connected Investor Position"
    )

    header_col_1, header_col_2 = (
        st.columns([3, 1])
    )

    with header_col_1:
        st.code(
            position.address,
            language=None,
        )

    with header_col_2:
        st.link_button(
            "Open wallet on Etherscan",
            etherscan_address_url(
                position.address
            ),
            use_container_width=True,
        )

    metric_1, metric_2, metric_3, metric_4 = (
        st.columns(4)
    )

    metric_1.metric(
        "Sepolia ETH",
        format_eth(
            position.eth_balance
        ),
    )

    metric_2.metric(
        "BondUSD",
        format_bondusd(
            position.bond_usd_balance
        ),
    )

    metric_3.metric(
        "DBOND26",
        f"{position.bond_token_balance:,}",
    )

    metric_4.metric(
        "Subscribed",
        f"{position.quantity_subscribed:,}",
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

    with wallet_tab:
        rows = [
            {
                "Asset / permission":
                    "Sepolia ETH",
                "Value":
                    format_eth(
                        position.eth_balance
                    ),
                "Purpose":
                    "Transaction gas",
            },
            {
                "Asset / permission":
                    "BondUSD",
                "Value":
                    format_bondusd(
                        position
                        .bond_usd_balance
                    ),
                "Purpose":
                    "Subscription and payments",
            },
            {
                "Asset / permission":
                    "BondUSD allowance",
                "Value":
                    format_bondusd(
                        position
                        .bond_usd_allowance
                    ),
                "Purpose":
                    "TokenizedBond spending limit",
            },
            {
                "Asset / permission":
                    "DBOND26",
                "Value":
                    (
                        f"{position.bond_token_balance:,} "
                        "token"
                    ),
                "Purpose":
                    "Bond ownership",
            },
        ]

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "ERC-20 approval only grants an allowance. "
            "The token is transferred only when subscribe() "
            "or a funding function is executed."
        )

    with position_tab:
        rows = [
            {
                "Indicator":
                    "Whitelisted",
                "Value":
                    format_boolean(
                        position
                        .is_whitelisted
                    ),
            },
            {
                "Indicator":
                    "Subscribed quantity",
                "Value":
                    (
                        f"{position.quantity_subscribed:,}"
                    ),
            },
            {
                "Indicator":
                    "Amount paid",
                "Value":
                    format_bondusd(
                        position.amount_paid
                    ),
            },
            {
                "Indicator":
                    "Current DBOND26 balance",
                "Value":
                    (
                        f"{position.bond_token_balance:,}"
                    ),
            },
            {
                "Indicator":
                    "Position status",
                "Value":
                    position.position_status,
            },
            {
                "Indicator":
                    "Contract lifecycle",
                "Value":
                    position.lifecycle_name,
            },
        ]

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    with claims_tab:
        claim_1, claim_2, claim_3, claim_4 = (
            st.columns(4)
        )

        claim_1.metric(
            "Refund",
            format_bondusd(
                position.refundable_amount
            ),
        )

        claim_2.metric(
            "Coupon 1",
            format_bondusd(
                position.claimable_coupon_1
            ),
        )

        claim_3.metric(
            "Coupon 2",
            format_bondusd(
                position.claimable_coupon_2
            ),
        )

        claim_4.metric(
            "Principal",
            format_bondusd(
                position.redeemable_principal
            ),
        )

    with history_tab:
        rows = [
            {
                "Right":
                    "Refund",
                "Completed":
                    format_boolean(
                        position
                        .has_claimed_refund
                    ),
            },
            {
                "Right":
                    "Coupon 1",
                "Completed":
                    format_boolean(
                        position
                        .has_claimed_coupon_1
                    ),
            },
            {
                "Right":
                    "Coupon 2",
                "Completed":
                    format_boolean(
                        position
                        .has_claimed_coupon_2
                    ),
            },
            {
                "Right":
                    "Principal redemption",
                "Completed":
                    format_boolean(
                        position
                        .has_redeemed_principal
                    ),
            },
        ]

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )
