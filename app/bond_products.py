from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BondProduct:
    product_id: str
    name: str
    symbol: str
    category: str
    description: str
    face_value: Decimal
    issue_price: Decimal
    max_supply: int
    minimum_subscription: int
    annual_coupon_rate: Decimal
    coupon_per_period: Decimal
    coupon_periods: int
    subscription_minutes: int
    grace_minutes: int
    color_label: str
    scenario: str
    deployment_status: str
    is_live: bool

    @property
    def maximum_issue_value(self) -> Decimal:
        return self.issue_price * self.max_supply

    @property
    def minimum_funding(self) -> Decimal:
        return self.issue_price * self.minimum_subscription


BOND_PRODUCTS: tuple[BondProduct, ...] = (
    BondProduct(
        product_id="green-bond-26",
        name="GreenBond26",
        symbol="GBOND26",
        category="Green Finance",
        description=(
            "Trái phiếu mô phỏng tài trợ các dự án tiết kiệm năng lượng, "
            "giảm phát thải và phát triển hạ tầng xanh."
        ),
        face_value=Decimal("100"),
        issue_price=Decimal("100"),
        max_supply=100,
        minimum_subscription=60,
        annual_coupon_rate=Decimal("8"),
        coupon_per_period=Decimal("4"),
        coupon_periods=2,
        subscription_minutes=10,
        grace_minutes=3,
        color_label="Green",
        scenario="Successful offering / normal repayment",
        deployment_status="Live demo contract on Sepolia",
        is_live=True,
    ),
    BondProduct(
        product_id="energy-bond-26",
        name="EnergyBond26",
        symbol="EBOND26",
        category="Energy Infrastructure",
        description=(
            "Trái phiếu mô phỏng huy động vốn cho dự án năng lượng và "
            "nâng cấp hạ tầng cung ứng điện."
        ),
        face_value=Decimal("100"),
        issue_price=Decimal("100"),
        max_supply=120,
        minimum_subscription=72,
        annual_coupon_rate=Decimal("10"),
        coupon_per_period=Decimal("5"),
        coupon_periods=2,
        subscription_minutes=10,
        grace_minutes=3,
        color_label="Energy",
        scenario="Failed offering / investor refund",
        deployment_status="Configured product profile",
        is_live=False,
    ),
    BondProduct(
        product_id="edu-bond-26",
        name="EduBond26",
        symbol="EDUB26",
        category="Education Finance",
        description=(
            "Trái phiếu mô phỏng tài trợ cơ sở vật chất, học liệu số và "
            "các chương trình đào tạo."
        ),
        face_value=Decimal("100"),
        issue_price=Decimal("100"),
        max_supply=80,
        minimum_subscription=40,
        annual_coupon_rate=Decimal("6"),
        coupon_per_period=Decimal("3"),
        coupon_periods=2,
        subscription_minutes=10,
        grace_minutes=3,
        color_label="Education",
        scenario="Payment default / cure demonstration",
        deployment_status="Configured product profile",
        is_live=False,
    ),
)


BOND_PRODUCTS_BY_ID = {
    product.product_id: product
    for product in BOND_PRODUCTS
}
