from __future__ import annotations

import pandas as pd
import streamlit as st

from app.compliance import ComplianceReport


def render_compliance_audit(
    report: ComplianceReport,
) -> None:
    """Render the complete Compliance and Audit page."""
    st.header("Compliance and Audit")

    st.caption(
        "Automated read-only checks of deployment references, "
        "roles, supply, financial reconciliation and lifecycle."
    )

    (
        metric_col_1,
        metric_col_2,
        metric_col_3,
        metric_col_4,
    ) = st.columns(4)

    metric_col_1.metric(
        label="Passed",
        value=report.pass_count,
    )

    metric_col_2.metric(
        label="Warnings",
        value=report.warning_count,
    )

    metric_col_3.metric(
        label="Failed",
        value=report.fail_count,
    )

    metric_col_4.metric(
        label="Information",
        value=report.info_count,
    )

    if report.fail_count > 0:
        st.error(
            f"Overall audit status: {report.overall_status}"
        )
    elif report.warning_count > 0:
        st.warning(
            f"Overall audit status: {report.overall_status}"
        )
    else:
        st.success(
            f"Overall audit status: {report.overall_status}"
        )

    all_tab, failed_tab, summary_tab = st.tabs(
        [
            "All Checks",
            "Warnings and Failures",
            "Audit Summary",
        ]
    )

    rows = [
        {
            "Category": check.category,
            "Check": check.check_name,
            "Status": check.status,
            "Detail": check.detail,
        }
        for check in report.checks
    ]

    with all_tab:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    with failed_tab:
        issue_rows = [
            row
            for row in rows
            if row["Status"] in {
                "WARN",
                "FAIL",
            }
        ]

        if issue_rows:
            st.dataframe(
                pd.DataFrame(issue_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success(
                "Không có warning hoặc failed check."
            )

    with summary_tab:
        summary_rows = [
            {
                "Indicator": "Overall status",
                "Value": report.overall_status,
            },
            {
                "Indicator": "Passed checks",
                "Value": report.pass_count,
            },
            {
                "Indicator": "Warnings",
                "Value": report.warning_count,
            },
            {
                "Indicator": "Failed checks",
                "Value": report.fail_count,
            },
            {
                "Indicator": "Informational controls",
                "Value": report.info_count,
            },
        ]

        st.dataframe(
            pd.DataFrame(summary_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.info(
            "Audit results are based on live public data from "
            "Ethereum Sepolia. The page does not sign or send transactions."
        )