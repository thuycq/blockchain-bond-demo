from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from app.config import etherscan_address_url
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


def format_readiness(
    value: bool,
) -> str:
    """Format action readiness."""
    return (
        "Sẵn sàng"
        if value
        else "Chưa sẵn sàng"
    )


def format_timestamp(
    timestamp: int,
) -> str:
    """Convert Unix timestamp to Vietnam time."""
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


def coupon_to_row(
    coupon: CouponObligation,
) -> dict[str, object]:
    """Convert a coupon obligation to one table row."""
    return {
        "Kỳ": f"Coupon {coupon.period}",
        "Ngày đến hạn": format_timestamp(
            coupon.due_timestamp
        ),
        "Phải nộp": format_bondusd(
            coupon.required
        ),
        "Đã nộp": format_bondusd(
            coupon.funded
        ),
        "Đã claim": format_bondusd(
            coupon.claimed
        ),
        "Thiếu funding": format_bondusd(
            coupon.funding_gap
        ),
        "Chưa claim": format_bondusd(
            coupon.unclaimed_amount
        ),
        "Default hiện tại": format_boolean(
            coupon.is_defaulted
        ),
        "Từng default": format_boolean(
            coupon.has_default_history
        ),
        "Trạng thái": coupon.status,
    }


def principal_to_rows(
    principal: PrincipalObligation,
) -> list[dict[str, object]]:
    """Build the principal detail table."""
    return [
        {
            "Chỉ tiêu": "Maturity",
            "Giá trị": format_timestamp(
                principal.maturity_timestamp
            ),
        },
        {
            "Chỉ tiêu": "Principal required",
            "Giá trị": format_bondusd(
                principal.required
            ),
        },
        {
            "Chỉ tiêu": "Principal funded",
            "Giá trị": format_bondusd(
                principal.funded
            ),
        },
        {
            "Chỉ tiêu": "Principal redeemed",
            "Giá trị": format_bondusd(
                principal.redeemed
            ),
        },
        {
            "Chỉ tiêu": "Funding gap",
            "Giá trị": format_bondusd(
                principal.funding_gap
            ),
        },
        {
            "Chỉ tiêu": "Funded but not redeemed",
            "Giá trị": format_bondusd(
                principal.unredeemed_amount
            ),
        },
        {
            "Chỉ tiêu": "Default hiện tại",
            "Giá trị": format_boolean(
                principal.is_defaulted
            ),
        },
        {
            "Chỉ tiêu": "Default timestamp",
            "Giá trị": format_timestamp(
                principal.defaulted_at
            ),
        },
        {
            "Chỉ tiêu": "Trạng thái",
            "Giá trị": principal.status,
        },
    ]


def render_issuer_dashboard(
    dashboard: IssuerDashboard,
) -> None:
    """Render the complete read-only Issuer Dashboard."""
    st.header("6. Issuer Dashboard")

    st.caption(
        "Dashboard chỉ đọc dành cho tổ chức phát hành. "
        "Không có private key hoặc giao dịch nào được tạo."
    )

    header_col_1, header_col_2 = st.columns(
        [3, 1]
    )

    with header_col_1:
        st.subheader("Issuer wallet")
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
            "Hệ thống đang ghi nhận ít nhất một "
            "nghĩa vụ bị default."
        )
    else:
        st.success(
            "Không có nghĩa vụ coupon hoặc principal "
            "đang bị default."
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
        label="Issuer BondUSD",
        value=format_bondusd(
            dashboard.bond_usd_balance
        ),
    )

    metric_col_3.metric(
        label="BondUSD Allowance",
        value=format_bondusd(
            dashboard.bond_usd_allowance
        ),
    )

    metric_col_4.metric(
        label="Lifecycle",
        value=dashboard.lifecycle_name,
    )

    (
        proceeds_tab,
        coupon_tab,
        principal_tab,
        action_tab,
    ) = st.tabs(
        [
            "Offering & Proceeds",
            "Coupon Obligations",
            "Principal Obligation",
            "Action Readiness",
        ]
    )

    with proceeds_tab:
        proceeds_col_1, proceeds_col_2, proceeds_col_3, proceeds_col_4 = (
            st.columns(4)
        )

        proceeds_col_1.metric(
            label="Total Raised",
            value=format_bondusd(
                dashboard.total_raised
            ),
        )

        proceeds_col_2.metric(
            label="Withdrawable Proceeds",
            value=format_bondusd(
                dashboard.withdrawable_proceeds
            ),
        )

        proceeds_col_3.metric(
            label="Contract Escrow",
            value=format_bondusd(
                dashboard.escrow_balance
            ),
        )

        proceeds_col_4.metric(
            label="Proceeds Withdrawn",
            value=format_boolean(
                dashboard.proceeds_withdrawn
            ),
        )

        offering_rows = [
            {
                "Indicator": "Lifecycle",
                "Value": dashboard.lifecycle_name,
            },
            {
                "Indicator": "Subscription open",
                "Value": format_boolean(
                    dashboard.subscription_open
                ),
            },
            {
                "Indicator": "Subscription paused",
                "Value": format_boolean(
                    dashboard.subscription_paused
                ),
            },
            {
                "Indicator": "Can finalize",
                "Value": format_boolean(
                    dashboard.can_finalize
                ),
            },
            {
                "Indicator": "Can close",
                "Value": format_boolean(
                    dashboard.can_close
                ),
            },
        ]

        st.dataframe(
            pd.DataFrame(offering_rows),
            use_container_width=True,
            hide_index=True,
        )

        if dashboard.lifecycle_value == 0:
            st.info(
                "Offering vẫn ở Draft. Issuer chưa mở "
                "subscription và chưa có proceeds."
            )

    with coupon_tab:
        coupon_rows = [
            coupon_to_row(
                dashboard.coupon_1
            ),
            coupon_to_row(
                dashboard.coupon_2
            ),
        ]

        st.dataframe(
            pd.DataFrame(coupon_rows),
            use_container_width=True,
            hide_index=True,
        )

        coupon_metric_1, coupon_metric_2, coupon_metric_3 = (
            st.columns(3)
        )

        coupon_required_total = (
            dashboard.coupon_1.required
            + dashboard.coupon_2.required
        )

        coupon_funded_total = (
            dashboard.coupon_1.funded
            + dashboard.coupon_2.funded
        )

        coupon_claimed_total = (
            dashboard.coupon_1.claimed
            + dashboard.coupon_2.claimed
        )

        coupon_metric_1.metric(
            label="Coupon Required",
            value=format_bondusd(
                coupon_required_total
            ),
        )

        coupon_metric_2.metric(
            label="Coupon Funded",
            value=format_bondusd(
                coupon_funded_total
            ),
        )

        coupon_metric_3.metric(
            label="Coupon Claimed",
            value=format_bondusd(
                coupon_claimed_total
            ),
        )

        if coupon_required_total == 0:
            st.caption(
                "Coupon obligations will be calculated "
                "when the offering is finalized successfully."
            )

    with principal_tab:
        st.dataframe(
            pd.DataFrame(
                principal_to_rows(
                    dashboard.principal
                )
            ),
            use_container_width=True,
            hide_index=True,
        )

        principal_metric_1, principal_metric_2, principal_metric_3 = (
            st.columns(3)
        )

        principal_metric_1.metric(
            label="Principal Required",
            value=format_bondusd(
                dashboard.principal.required
            ),
        )

        principal_metric_2.metric(
            label="Principal Funded",
            value=format_bondusd(
                dashboard.principal.funded
            ),
        )

        principal_metric_3.metric(
            label="Principal Redeemed",
            value=format_bondusd(
                dashboard.principal.redeemed
            ),
        )

        if dashboard.principal.required == 0:
            st.caption(
                "Principal obligation will be calculated "
                "when the offering is finalized successfully."
            )

    with action_tab:
        action_rows = [
            {
                "Action": "Open Subscription",
                "Caller": "Issuer",
                "Readiness": format_readiness(
                    dashboard.can_open_subscription
                ),
            },
            {
                "Action": "Finalize Offering",
                "Caller": "Permissionless",
                "Readiness": format_readiness(
                    dashboard.can_finalize
                ),
            },
            {
                "Action": "Withdraw Proceeds",
                "Caller": "Issuer",
                "Readiness": format_readiness(
                    dashboard.can_withdraw_proceeds
                ),
            },
            {
                "Action": "Deposit Coupon 1",
                "Caller": "Issuer",
                "Readiness": format_readiness(
                    dashboard.coupon_1.can_deposit
                ),
            },
            {
                "Action": "Deposit Coupon 2",
                "Caller": "Issuer",
                "Readiness": format_readiness(
                    dashboard.coupon_2.can_deposit
                ),
            },
            {
                "Action": "Deposit Principal",
                "Caller": "Issuer",
                "Readiness": format_readiness(
                    dashboard.principal.can_deposit
                ),
            },
            {
                "Action": "Close Bond",
                "Caller": "Permissionless",
                "Readiness": format_readiness(
                    dashboard.can_close
                ),
            },
        ]

        st.dataframe(
            pd.DataFrame(action_rows),
            use_container_width=True,
            hide_index=True,
        )

        summary_col_1, summary_col_2 = st.columns(
            2
        )

        summary_col_1.metric(
            label="Total Funding Gap",
            value=format_bondusd(
                dashboard.total_funding_gap
            ),
        )

        summary_col_2.metric(
            label="Funded but Unclaimed",
            value=format_bondusd(
                dashboard.total_unclaimed_obligations
            ),
        )

        st.subheader("Issuer Actions")

        button_col_1, button_col_2, button_col_3, button_col_4 = (
            st.columns(4)
        )

        button_col_1.button(
            "Open Subscription",
            disabled=True,
            use_container_width=True,
            key="issuer_preview_open",
        )

        button_col_2.button(
            "Withdraw Proceeds",
            disabled=True,
            use_container_width=True,
            key="issuer_preview_withdraw",
        )

        button_col_3.button(
            "Deposit Coupon",
            disabled=True,
            use_container_width=True,
            key="issuer_preview_coupon",
        )

        button_col_4.button(
            "Deposit Principal",
            disabled=True,
            use_container_width=True,
            key="issuer_preview_principal",
        )

        st.caption(
            "Các nút đang bị khóa trong chế độ read-only. "
            "Việc ký giao dịch bằng MetaMask sẽ được thực hiện "
            "sau khi toàn bộ dashboard được kiểm tra."
        )