from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from app.overview import BondOverview


VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def format_bondusd(value: Decimal) -> str:
    """Format a BondUSD amount."""
    return f"{value:,.2f} BONDUSD"


def format_percent(value: Decimal) -> str:
    """Format a percentage."""
    return f"{value:,.2f}%"


def format_timestamp(timestamp: int) -> str:
    """Convert a Unix timestamp to Vietnam local time."""
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


def format_duration(seconds: int) -> str:
    """Format a duration for the demo timeline."""
    if seconds <= 0:
        return "0 phút"

    if seconds % 3600 == 0:
        return f"{seconds // 3600} giờ"

    if seconds % 60 == 0:
        return f"{seconds // 60} phút"

    return f"{seconds} giây"


def render_bond_overview(
    overview: BondOverview,
) -> None:
    """Render the complete Bond Overview section."""
    st.header("4. Bond Overview")

    st.caption(
        "Các thông số bên dưới được đọc trực tiếp từ "
        "TokenizedBond và BondToken trên Ethereum Sepolia."
    )

    title_col, symbol_col, lifecycle_col, coupon_col = st.columns(4)

    title_col.metric(
        label="Bond",
        value=overview.bond_name,
    )

    symbol_col.metric(
        label="Token Symbol",
        value=overview.bond_symbol,
    )

    lifecycle_col.metric(
        label="Lifecycle",
        value=overview.lifecycle_name,
    )

    coupon_col.metric(
        label="Annual Coupon Rate",
        value=format_percent(
            overview.annual_coupon_rate_percent
        ),
    )

    st.info(
        f"Trạng thái hiện tại: **{overview.offering_status}**"
    )

    (
        financial_tab,
        offering_tab,
        timeline_tab,
        operation_tab,
    ) = st.tabs(
        [
            "Financial Terms",
            "Offering Progress",
            "Timeline",
            "Operational Status",
        ]
    )

    # ========================================================
    # Financial terms
    # ========================================================

    with financial_tab:
        financial_rows = [
            {
                "Thông số": "Mệnh giá",
                "Giá trị": format_bondusd(
                    overview.face_value
                ),
            },
            {
                "Thông số": "Giá phát hành",
                "Giá trị": format_bondusd(
                    overview.issue_price
                ),
            },
            {
                "Thông số": "Khối lượng tối đa",
                "Giá trị": (
                    f"{overview.max_supply:,} trái phiếu"
                ),
            },
            {
                "Thông số": "Ngưỡng phát hành tối thiểu",
                "Giá trị": (
                    f"{overview.minimum_subscription:,} "
                    "trái phiếu"
                ),
            },
            {
                "Thông số": "Giá trị phát hành tối đa",
                "Giá trị": format_bondusd(
                    overview.maximum_issue_value
                ),
            },
            {
                "Thông số": "Giá trị tối thiểu để thành công",
                "Giá trị": format_bondusd(
                    overview.minimum_issue_value
                ),
            },
            {
                "Thông số": "Lãi suất coupon năm",
                "Giá trị": format_percent(
                    overview.annual_coupon_rate_percent
                ),
            },
            {
                "Thông số": "Coupon mỗi kỳ/trái phiếu",
                "Giá trị": format_bondusd(
                    overview.coupon_per_period
                ),
            },
            {
                "Thông số": "Số kỳ coupon",
                "Giá trị": (
                    f"{overview.coupon_period_count} kỳ"
                ),
            },
            {
                "Thông số": "Tổng coupon/trái phiếu",
                "Giá trị": format_bondusd(
                    overview.total_coupon_per_bond
                ),
            },
        ]

        st.dataframe(
            pd.DataFrame(financial_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Trong Solidity, đơn vị `ether` được dùng để biểu diễn "
            "BondUSD có 18 decimals; các giá trị này không phải ETH."
        )

    # ========================================================
    # Offering progress
    # ========================================================

    with offering_tab:
        progress_col_1, progress_col_2 = st.columns(2)

        with progress_col_1:
            st.subheader("Maximum supply progress")

            maximum_ratio = min(
                float(
                    overview.maximum_progress_percent
                    / Decimal(100)
                ),
                1.0,
            )

            st.progress(maximum_ratio)

            st.write(
                f"**{overview.total_subscribed:,} / "
                f"{overview.max_supply:,} trái phiếu**"
            )

            st.caption(
                "Tỷ lệ đã đăng ký trên tổng khối lượng tối đa: "
                f"{format_percent(overview.maximum_progress_percent)}"
            )

        with progress_col_2:
            st.subheader("Minimum threshold progress")

            minimum_ratio = min(
                float(
                    overview.minimum_progress_percent
                    / Decimal(100)
                ),
                1.0,
            )

            st.progress(minimum_ratio)

            st.write(
                f"**{overview.total_subscribed:,} / "
                f"{overview.minimum_subscription:,} "
                "trái phiếu**"
            )

            st.caption(
                "Mức hoàn thành ngưỡng phát hành tối thiểu: "
                f"{format_percent(overview.minimum_progress_percent)}"
            )

        offering_col_1, offering_col_2, offering_col_3, offering_col_4 = (
            st.columns(4)
        )

        offering_col_1.metric(
            label="Total Subscribed",
            value=f"{overview.total_subscribed:,}",
        )

        offering_col_2.metric(
            label="Remaining Supply",
            value=f"{overview.remaining_supply:,}",
        )

        offering_col_3.metric(
            label="Total Raised",
            value=format_bondusd(
                overview.total_raised
            ),
        )

        offering_col_4.metric(
            label="Total Refunded",
            value=format_bondusd(
                overview.total_refunded
            ),
        )

        if (
            overview.total_subscribed
            >= overview.minimum_subscription
        ):
            st.success(
                "Khối lượng đăng ký đã đạt ngưỡng tối thiểu."
            )
        else:
            shortfall = (
                overview.minimum_subscription
                - overview.total_subscribed
            )

            st.warning(
                "Khối lượng đăng ký chưa đạt ngưỡng tối thiểu. "
                f"Còn thiếu {shortfall:,} trái phiếu."
            )

    # ========================================================
    # Timeline
    # ========================================================

    with timeline_tab:
        timeline_rows = [
            {
                "Mốc": "Thời lượng subscription",
                "Thời gian": format_duration(
                    overview.subscription_duration_seconds
                ),
                "Trạng thái": "Thông số cố định",
            },
            {
                "Mốc": "Subscription start",
                "Thời gian": format_timestamp(
                    overview.subscription_start
                ),
                "Trạng thái": (
                    "Đã xác lập"
                    if overview.subscription_start > 0
                    else "Chưa xác lập"
                ),
            },
            {
                "Mốc": "Subscription deadline",
                "Thời gian": format_timestamp(
                    overview.subscription_deadline
                ),
                "Trạng thái": (
                    "Đã xác lập"
                    if overview.subscription_deadline > 0
                    else "Chưa xác lập"
                ),
            },
            {
                "Mốc": "Finalized at",
                "Thời gian": format_timestamp(
                    overview.finalized_at
                ),
                "Trạng thái": (
                    "Đã finalize"
                    if overview.finalized_at > 0
                    else "Chưa finalize"
                ),
            },
            {
                "Mốc": "Coupon 1 due",
                "Thời gian": format_timestamp(
                    overview.coupon_1_due
                ),
                "Trạng thái": (
                    f"{format_duration(overview.coupon_1_delay_seconds)} "
                    "sau finalize"
                ),
            },
            {
                "Mốc": "Coupon 2 due",
                "Thời gian": format_timestamp(
                    overview.coupon_2_due
                ),
                "Trạng thái": (
                    f"{format_duration(overview.coupon_2_delay_seconds)} "
                    "sau finalize"
                ),
            },
            {
                "Mốc": "Maturity",
                "Thời gian": format_timestamp(
                    overview.maturity
                ),
                "Trạng thái": (
                    "Bằng Coupon 2 due date"
                ),
            },
            {
                "Mốc": "Grace period",
                "Thời gian": format_duration(
                    overview.grace_period_seconds
                ),
                "Trạng thái": "Áp dụng trước khi ghi nhận default",
            },
        ]

        st.dataframe(
            pd.DataFrame(timeline_rows),
            use_container_width=True,
            hide_index=True,
        )

        if overview.finalized_at == 0:
            st.info(
                "Coupon due date và maturity chỉ được xác lập "
                "sau khi offering được finalize."
            )

    # ========================================================
    # Operational status
    # ========================================================

    with operation_tab:
        operational_rows = [
            {
                "Chỉ tiêu": "Lifecycle",
                "Giá trị": overview.lifecycle_name,
            },
            {
                "Chỉ tiêu": "Lifecycle value",
                "Giá trị": overview.lifecycle_value,
            },
            {
                "Chỉ tiêu": "Subscription open",
                "Giá trị": overview.subscription_open,
            },
            {
                "Chỉ tiêu": "Subscription paused",
                "Giá trị": overview.subscription_paused,
            },
            {
                "Chỉ tiêu": "Can finalize",
                "Giá trị": overview.can_finalize,
            },
            {
                "Chỉ tiêu": "Is defaulted",
                "Giá trị": overview.is_defaulted,
            },
            {
                "Chỉ tiêu": "Can close",
                "Giá trị": overview.can_close,
            },
        ]

        st.dataframe(
            pd.DataFrame(operational_rows),
            use_container_width=True,
            hide_index=True,
        )

        if overview.lifecycle_value == 0:
            st.success(
                "Base deployment vẫn ở Draft. "
                "Subscription chưa được mở."
            )

        if overview.is_defaulted:
            st.error(
                "Hệ thống đang ghi nhận ít nhất một nghĩa vụ default."
            )
        else:
            st.caption(
                "Hiện không có nghĩa vụ coupon hoặc principal "
                "đang được ghi nhận default."
            )