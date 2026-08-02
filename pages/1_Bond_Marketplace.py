from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from app.bond_products import BOND_PRODUCTS
from app.config import (
    BOND_TOKEN_ADDRESS,
    BOND_USD_ADDRESS,
    TOKENIZED_BOND_ADDRESS,
    etherscan_address_url,
)


st.set_page_config(
    page_title="Bond Marketplace",
    page_icon="🏦",
    layout="wide",
)


st.title("Bond Marketplace")
st.caption(
    "Danh mục sản phẩm trái phiếu token hóa phục vụ mô phỏng trên Ethereum Sepolia."
)

st.info(
    "GreenBond26 đang sử dụng bộ smart contract live hiện tại. "
    "EnergyBond26 và EduBond26 là hai cấu hình sản phẩm được bổ sung nhanh cho website; "
    "hai sản phẩm này chưa có contract độc lập trên Sepolia."
)

columns = st.columns(3)

for column, product in zip(columns, BOND_PRODUCTS):
    with column:
        status = "LIVE ON SEPOLIA" if product.is_live else "PRODUCT PROFILE"
        st.subheader(product.name)
        st.caption(f"{product.symbol} · {product.category}")
        st.markdown(f"**{status}**")
        st.write(product.description)
        st.metric("Annual coupon", f"{product.annual_coupon_rate}%")
        st.metric("Maximum issue value", f"{product.maximum_issue_value:,.0f} BONDUSD")
        st.metric("Minimum funding", f"{product.minimum_funding:,.0f} BONDUSD")
        st.write(f"**Scenario:** {product.scenario}")

st.divider()

selected_name = st.selectbox(
    "Chọn sản phẩm để xem điều khoản",
    [product.name for product in BOND_PRODUCTS],
)

selected = next(
    product for product in BOND_PRODUCTS if product.name == selected_name
)

left, right = st.columns([2, 1])

with left:
    st.subheader(f"Điều khoản {selected.name}")

    terms = pd.DataFrame(
        [
            ("Symbol", selected.symbol),
            ("Face value", f"{selected.face_value:,.0f} BONDUSD"),
            ("Issue price", f"{selected.issue_price:,.0f} BONDUSD"),
            ("Maximum supply", f"{selected.max_supply} bonds"),
            (
                "Minimum subscription",
                f"{selected.minimum_subscription} bonds",
            ),
            (
                "Maximum issue value",
                f"{selected.maximum_issue_value:,.0f} BONDUSD",
            ),
            (
                "Minimum funding",
                f"{selected.minimum_funding:,.0f} BONDUSD",
            ),
            ("Annual coupon rate", f"{selected.annual_coupon_rate}%"),
            (
                "Coupon per period",
                f"{selected.coupon_per_period:,.0f} BONDUSD/bond",
            ),
            ("Coupon periods", selected.coupon_periods),
            (
                "Subscription duration",
                f"{selected.subscription_minutes} minutes",
            ),
            ("Grace period", f"{selected.grace_minutes} minutes"),
            ("Deployment", selected.deployment_status),
        ],
        columns=["Term", "Value"],
    )

    st.dataframe(
        terms,
        hide_index=True,
        use_container_width=True,
    )

with right:
    st.subheader("Demo status")

    if selected.is_live:
        st.success("Đang liên kết với bộ smart contract live trên Sepolia.")
        st.link_button(
            "Open TokenizedBond",
            etherscan_address_url(TOKENIZED_BOND_ADDRESS),
            use_container_width=True,
        )
        st.link_button(
            "Open BondToken",
            etherscan_address_url(BOND_TOKEN_ADDRESS),
            use_container_width=True,
        )
        st.link_button(
            "Open BondUSD",
            etherscan_address_url(BOND_USD_ADDRESS),
            use_container_width=True,
        )
        st.warning(
            "Các giao dịch được thực hiện tại ứng dụng chính bằng MetaMask."
        )
    else:
        st.warning(
            "Sản phẩm này hiện là cấu hình trình bày trên website. "
            "Để giao dịch độc lập cần deploy thêm một BondToken và một TokenizedBond."
        )

st.divider()

st.subheader("So sánh nhanh")
comparison = pd.DataFrame(
    [
        {
            "Product": product.name,
            "Symbol": product.symbol,
            "Coupon": f"{product.annual_coupon_rate}%",
            "Max supply": product.max_supply,
            "Minimum": product.minimum_subscription,
            "Maximum value": f"{product.maximum_issue_value:,.0f}",
            "Scenario": product.scenario,
            "Status": "Live" if product.is_live else "Profile",
        }
        for product in BOND_PRODUCTS
    ]
)

st.dataframe(
    comparison,
    hide_index=True,
    use_container_width=True,
)

st.caption(
    "BONDUSD là token thanh toán dùng chung. Mỗi đợt phát hành độc lập cần một "
    "BondToken và một TokenizedBond riêng."
)
