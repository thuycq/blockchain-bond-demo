from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from app.payment_schedule import (
    PaymentSchedule,
    PaymentScheduleItem,
)


VIETNAM_TIMEZONE = ZoneInfo(
    "Asia/Ho_Chi_Minh"
)


def format_bondusd(
    value: Decimal,
) -> str:
    """Format a BONDUSD amount."""
    return f"{value:,.2f} BONDUSD"


def format_boolean(
    value: bool,
) -> str:
    """Format a Boolean value."""
    return "Yes" if value else "No"


def format_timestamp(
    timestamp: int,
) -> str:
    """Convert a Unix timestamp to Vietnam time."""
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


def calculate_funding_ratio(
    item: PaymentScheduleItem,
) -> float:
    """Return a progress ratio between zero and one."""
    if item.required <= 0:
        return 0.0

    ratio = (
        item.funded
        / item.required
    )

    return min(
        max(
            float(ratio),
            0.0,
        ),
        1.0,
    )


def render_obligation_progress(
    item: PaymentScheduleItem,
) -> None:
    """Render progress for one payment obligation."""
    st.markdown(
        f"#### {item.obligation}"
    )

    st.progress(
        calculate_funding_ratio(
            item
        )
    )

    detail_col_1, detail_col_2 = (
        st.columns(2)
    )

    with detail_col_1:
        st.write(
            "**Required:** "
            f"{format_bondusd(item.required)}"
        )

        st.write(
            "**Funded:** "
            f"{format_bondusd(item.funded)}"
        )

        st.write(
            "**Funding gap:** "
            f"{format_bondusd(item.funding_gap)}"
        )

    with detail_col_2:
        st.write(
            "**Distributed:** "
            f"{format_bondusd(item.distributed)}"
        )

        st.write(
            "**Due date:** "
            f"{format_timestamp(item.due_timestamp)}"
        )

        st.write(
            "**Status:** "
            f"{item.status}"
        )


def render_payment_schedule(
    schedule: PaymentSchedule,
) -> None:
    """Render the complete read-only payment schedule."""
    st.header(
        "8. Payment Schedule"
    )

    st.caption(
        "Coupon and principal obligations are calculated "
        "from data already loaded by the dashboard. "
        "This section creates no additional RPC calls."
    )

    if schedule.has_active_default:
        st.error(
            "Ít nhất một nghĩa vụ thanh toán "
            "đang bị default."
        )
    elif schedule.lifecycle_name == "Draft":
        st.info(
            "Offering đang ở Draft. Coupon schedule "
            "và principal obligation chưa được xác lập."
        )
    else:
        st.success(
            "Không có nghĩa vụ đang bị default."
        )

    (
        metric_col_1,
        metric_col_2,
        metric_col_3,
        metric_col_4,
    ) = st.columns(4)

    metric_col_1.metric(
        label="Total Required",
        value=format_bondusd(
            schedule.total_required
        ),
    )

    metric_col_2.metric(
        label="Total Funded",
        value=format_bondusd(
            schedule.total_funded
        ),
    )

    metric_col_3.metric(
        label="Total Distributed",
        value=format_bondusd(
            schedule.total_distributed
        ),
    )

    metric_col_4.metric(
        label="Funding Gap",
        value=format_bondusd(
            schedule.total_funding_gap
        ),
    )

    schedule_tab, progress_tab, summary_tab = (
        st.tabs(
            [
                "Schedule Table",
                "Funding Progress",
                "Payment Summary",
            ]
        )
    )

    with schedule_tab:
        schedule_rows = []

        for item in schedule.items:
            schedule_rows.append(
                {
                    "Sequence": (
                        item.sequence
                    ),
                    "Obligation": (
                        item.obligation
                    ),
                    "Type": (
                        item.obligation_type
                    ),
                    "Due Date": (
                        format_timestamp(
                            item.due_timestamp
                        )
                    ),
                    "Grace Deadline": (
                        format_timestamp(
                            item.grace_deadline
                        )
                    ),
                    "Required": (
                        format_bondusd(
                            item.required
                        )
                    ),
                    "Funded": (
                        format_bondusd(
                            item.funded
                        )
                    ),
                    "Distributed": (
                        format_bondusd(
                            item.distributed
                        )
                    ),
                    "Funding Gap": (
                        format_bondusd(
                            item.funding_gap
                        )
                    ),
                    "Default": (
                        format_boolean(
                            item.is_defaulted
                        )
                    ),
                    "Status": (
                        item.status
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(
                schedule_rows
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Grace Deadline = Due Date + Grace Period. "
            "Default chỉ được ghi nhận sau khi nghĩa vụ "
            "quá hạn và vượt grace period theo smart contract."
        )

    with progress_tab:
        progress_col_1, progress_col_2, progress_col_3 = (
            st.columns(3)
        )

        with progress_col_1:
            render_obligation_progress(
                schedule.items[0]
            )

        with progress_col_2:
            render_obligation_progress(
                schedule.items[1]
            )

        with progress_col_3:
            render_obligation_progress(
                schedule.items[2]
            )

    with summary_tab:
        summary_rows = [
            {
                "Indicator": (
                    "Current lifecycle"
                ),
                "Value": (
                    schedule.lifecycle_name
                ),
            },
            {
                "Indicator": (
                    "Current blockchain time"
                ),
                "Value": (
                    format_timestamp(
                        schedule
                        .current_block_timestamp
                    )
                ),
            },
            {
                "Indicator": (
                    "Next obligation"
                ),
                "Value": (
                    schedule.next_obligation
                ),
            },
            {
                "Indicator": (
                    "Next due date"
                ),
                "Value": (
                    format_timestamp(
                        schedule
                        .next_due_timestamp
                    )
                ),
            },
            {
                "Indicator": (
                    "Funded but not distributed"
                ),
                "Value": (
                    format_bondusd(
                        schedule
                        .total_undistributed_funds
                    )
                ),
            },
            {
                "Indicator": (
                    "Remaining contractual payments"
                ),
                "Value": (
                    format_bondusd(
                        schedule
                        .total_remaining_contractual_payment
                    )
                ),
            },
            {
                "Indicator": (
                    "Active default"
                ),
                "Value": (
                    format_boolean(
                        schedule
                        .has_active_default
                    )
                ),
            },
        ]

        st.dataframe(
            pd.DataFrame(
                summary_rows
            ),
            use_container_width=True,
            hide_index=True,
        )

        if (
            schedule.next_due_timestamp
            == 0
        ):
            st.caption(
                "Payment dates will be generated "
                "after a successful offering is finalized."
            )