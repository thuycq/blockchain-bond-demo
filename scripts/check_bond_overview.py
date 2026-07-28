from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.blockchain import BlockchainClient  # noqa: E402
from app.overview import get_bond_overview  # noqa: E402


def main() -> None:
    client = BlockchainClient()
    overview = get_bond_overview(client)

    print("=" * 72)
    print("BOND 6.5 - BOND OVERVIEW CHECK")
    print("=" * 72)

    print("\nBond")
    print(f"Name:                  {overview.bond_name}")
    print(f"Symbol:                {overview.bond_symbol}")
    print(f"Lifecycle:             {overview.lifecycle_name}")
    print(f"Offering status:       {overview.offering_status}")

    print("\nFinancial terms")
    print(f"Face value:            {overview.face_value} BONDUSD")
    print(f"Issue price:           {overview.issue_price} BONDUSD")
    print(f"Maximum supply:        {overview.max_supply}")
    print(
        f"Minimum subscription:  "
        f"{overview.minimum_subscription}"
    )
    print(
        f"Annual coupon rate:    "
        f"{overview.annual_coupon_rate_percent}%"
    )
    print(
        f"Coupon per period:     "
        f"{overview.coupon_per_period} BONDUSD"
    )
    print(
        f"Coupon periods:        "
        f"{overview.coupon_period_count}"
    )

    print("\nDemo timeline")
    print(
        f"Subscription duration: "
        f"{overview.subscription_duration_seconds} seconds"
    )
    print(
        f"Coupon 1 delay:        "
        f"{overview.coupon_1_delay_seconds} seconds"
    )
    print(
        f"Coupon 2 delay:        "
        f"{overview.coupon_2_delay_seconds} seconds"
    )
    print(
        f"Grace period:          "
        f"{overview.grace_period_seconds} seconds"
    )

    print("\nCurrent state")
    print(
        f"Total subscribed:      "
        f"{overview.total_subscribed}"
    )
    print(
        f"Total raised:          "
        f"{overview.total_raised} BONDUSD"
    )
    print(
        f"Subscription start:    "
        f"{overview.subscription_start}"
    )
    print(
        f"Finalized at:          "
        f"{overview.finalized_at}"
    )
    print(
        f"Maturity:              "
        f"{overview.maturity}"
    )
    print(
        f"Defaulted:             "
        f"{overview.is_defaulted}"
    )

    assert overview.bond_name == "Demo Corporate Bond 2026"
    assert overview.bond_symbol == "DBOND26"

    assert overview.face_value == Decimal("100")
    assert overview.issue_price == Decimal("100")

    assert overview.max_supply == 100
    assert overview.minimum_subscription == 60

    assert overview.annual_coupon_rate_percent == Decimal("10")
    assert overview.coupon_per_period == Decimal("5")
    assert overview.coupon_period_count == 2

    assert overview.subscription_duration_seconds == 600
    assert overview.coupon_1_delay_seconds == 300
    assert overview.coupon_2_delay_seconds == 600
    assert overview.grace_period_seconds == 180

    assert overview.lifecycle_value == 0
    assert overview.total_subscribed == 0
    assert overview.total_raised == Decimal("0")

    assert overview.subscription_start == 0
    assert overview.finalized_at == 0
    assert overview.maturity == 0

    print("\n[OK] Bond Overview values are correct.")
    print("[OK] Base deployment remains in Draft.")
    print("[OK] No transaction was created.")


if __name__ == "__main__":
    main()