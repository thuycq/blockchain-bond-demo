from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from app.config import (
    etherscan_address_url,
)
from app.issuer import (
    CouponObligation,
    IssuerDashboard,
    PrincipalObligation,
)


VIETNAM_TIMEZONE = ZoneInfo(
    "Asia/Ho_Chi_Minh"
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


def format_timestamp(
    timestamp: int,
) -> str:
    if timestamp == 0:
        return "Chưa xác lập"

    utc_time = datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    )

    local_time = utc_time.astimezone(
        VIETNAM_TIMEZONE
    )

    return local_time.strftime(
        "%d/%m/%Y %H:%M:%S (UTC+7)"
    )


def coupon_row(
    coupon: CouponObligation,
) -> dict[str, object]:
    return {
        "Period":
            coupon.period,
        "Due":
            format_timestamp(
                coupon.due_timestamp
            ),
        "Required":
            format_bondusd(
                coupon.required
            ),
        "Funded":
            format_bondusd(
                coupon.funded
            ),
        "Claimed":
            format_bondusd(
                coupon.claimed
            ),
        "Funding gap":
            format_bondusd(
                coupon.funding_gap
            ),
        "Default":
            format_boolean(
                coupon.is_defaulted
            ),
        "Status":
            coupon.status,
    }


def principal_rows(
    principal: PrincipalObligation,
) -> list[dict[str, object]]:
    return [
        {
            "Indicator":
                "Maturity",
            "Value":
                format_timestamp(
                    principal
                    .maturity_timestamp
                ),
        },
        {
            "Indicator":
                "Required",
            "Value":
                format_bondusd(
                    principal.required
                ),
        },
        {
            "Indicator":
                "Funded",
            "Value":
                format_bondusd(
                    principal.funded
                ),
        },
        {
            "Indicator":
                "Redeemed",
            "Value":
                format_bondusd(
                    principal.redeemed
                ),
        },
        {
            "Indicator":
                "Funding gap",
            "Value":
                format_bondusd(
                    principal.funding_gap
                ),
        },
        {
            "Indicator":
                "Default",
            "Value":
                format_boolean(
                    principal.is_defaulted
                ),
        },
        {
            "Indicator":
                "Status",
            "Value":
                principal.status,
        },
    ]


def render_issuer_dashboard(
    dashboard: IssuerDashboard,
) -> None:
    """Render issuer balances and obligations without action buttons."""
    st.subheader(
        "Issuer State"
    )

    header_col_1, header_col_2 = (
        st.columns([3, 1])
    )

    with header_col_1:
        st.code(
            dashboard.issuer_address,
            language=None,
        )

    with header_col_2:
        st.link_button(
            "Open issuer on Etherscan",
            etherscan_address_url(
                dashboard.issuer_address
            ),
            use_container_width=True,
        )

    if dashboard.is_defaulted:
        st.error(
            "The bond currently has at least one "
            "defaulted obligation."
        )
    else:
        st.success(
            "No coupon or principal obligation "
            "is currently marked as defaulted."
        )

    metric_1, metric_2, metric_3, metric_4 = (
        st.columns(4)
    )

    metric_1.metric(
        "Sepolia ETH",
        format_eth(
            dashboard.eth_balance
        ),
    )

    metric_2.metric(
        "Issuer BondUSD",
        format_bondusd(
            dashboard.bond_usd_balance
        ),
    )

    metric_3.metric(
        "BondUSD Allowance",
        format_bondusd(
            dashboard.bond_usd_allowance
        ),
    )

    metric_4.metric(
        "Lifecycle",
        dashboard.lifecycle_name,
    )

    (
        proceeds_tab,
        coupon_tab,
        principal_tab,
        readiness_tab,
    ) = st.tabs(
        [
            "Offering & Proceeds",
            "Coupon Obligations",
            "Principal Obligation",
            "Readiness",
        ]
    )

    with proceeds_tab:
        col_1, col_2, col_3, col_4 = (
            st.columns(4)
        )

        col_1.metric(
            "Total Raised",
            format_bondusd(
                dashboard.total_raised
            ),
        )

        col_2.metric(
            "Withdrawable",
            format_bondusd(
                dashboard
                .withdrawable_proceeds
            ),
        )

        col_3.metric(
            "Contract Escrow",
            format_bondusd(
                dashboard.escrow_balance
            ),
        )

        col_4.metric(
            "Proceeds Withdrawn",
            format_boolean(
                dashboard
                .proceeds_withdrawn
            ),
        )

    with coupon_tab:
        st.dataframe(
            pd.DataFrame(
                [
                    coupon_row(
                        dashboard.coupon_1
                    ),
                    coupon_row(
                        dashboard.coupon_2
                    ),
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    with principal_tab:
        st.dataframe(
            pd.DataFrame(
                principal_rows(
                    dashboard.principal
                )
            ),
            use_container_width=True,
            hide_index=True,
        )

    with readiness_tab:
        rows = [
            {
                "Action":
                    "Open Subscription",
                "Ready":
                    format_boolean(
                        dashboard
                        .can_open_subscription
                    ),
            },
            {
                "Action":
                    "Finalize Offering",
                "Ready":
                    format_boolean(
                        dashboard.can_finalize
                    ),
            },
            {
                "Action":
                    "Withdraw Proceeds",
                "Ready":
                    format_boolean(
                        dashboard
                        .can_withdraw_proceeds
                    ),
            },
            {
                "Action":
                    "Deposit Coupon 1",
                "Ready":
                    format_boolean(
                        dashboard
                        .coupon_1
                        .can_deposit
                    ),
            },
            {
                "Action":
                    "Deposit Coupon 2",
                "Ready":
                    format_boolean(
                        dashboard
                        .coupon_2
                        .can_deposit
                    ),
            },
            {
                "Action":
                    "Deposit Principal",
                "Ready":
                    format_boolean(
                        dashboard
                        .principal
                        .can_deposit
                    ),
            },
            {
                "Action":
                    "Close Bond",
                "Ready":
                    format_boolean(
                        dashboard.can_close
                    ),
            },
        ]

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )
