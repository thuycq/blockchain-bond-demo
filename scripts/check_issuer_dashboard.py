from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from app.blockchain import BlockchainClient  # noqa: E402
from app.config import ISSUER_ADDRESS  # noqa: E402
from app.issuer import get_issuer_dashboard  # noqa: E402


def main() -> None:
    print("=" * 72)
    print("BOND 6.7 - ISSUER DASHBOARD CHECK")
    print("=" * 72)

    client = BlockchainClient()

    dashboard = get_issuer_dashboard(
        client
    )

    print("\nIssuer")
    print(
        f"Address:                  "
        f"{dashboard.issuer_address}"
    )
    print(
        f"ETH balance:              "
        f"{dashboard.eth_balance}"
    )
    print(
        f"BondUSD balance:          "
        f"{dashboard.bond_usd_balance}"
    )
    print(
        f"BondUSD allowance:        "
        f"{dashboard.bond_usd_allowance}"
    )

    print("\nOffering")
    print(
        f"Lifecycle:                "
        f"{dashboard.lifecycle_name}"
    )
    print(
        f"Subscription open:        "
        f"{dashboard.subscription_open}"
    )
    print(
        f"Subscription paused:      "
        f"{dashboard.subscription_paused}"
    )
    print(
        f"Total raised:             "
        f"{dashboard.total_raised}"
    )
    print(
        f"Escrow balance:           "
        f"{dashboard.escrow_balance}"
    )
    print(
        f"Proceeds withdrawn:       "
        f"{dashboard.proceeds_withdrawn}"
    )
    print(
        f"Can open subscription:    "
        f"{dashboard.can_open_subscription}"
    )
    print(
        f"Can withdraw proceeds:    "
        f"{dashboard.can_withdraw_proceeds}"
    )

    print("\nCoupon 1")
    print(
        f"Required:                 "
        f"{dashboard.coupon_1.required}"
    )
    print(
        f"Funded:                   "
        f"{dashboard.coupon_1.funded}"
    )
    print(
        f"Claimed:                  "
        f"{dashboard.coupon_1.claimed}"
    )
    print(
        f"Defaulted:                "
        f"{dashboard.coupon_1.is_defaulted}"
    )
    print(
        f"Status:                   "
        f"{dashboard.coupon_1.status}"
    )

    print("\nCoupon 2")
    print(
        f"Required:                 "
        f"{dashboard.coupon_2.required}"
    )
    print(
        f"Funded:                   "
        f"{dashboard.coupon_2.funded}"
    )
    print(
        f"Claimed:                  "
        f"{dashboard.coupon_2.claimed}"
    )
    print(
        f"Defaulted:                "
        f"{dashboard.coupon_2.is_defaulted}"
    )
    print(
        f"Status:                   "
        f"{dashboard.coupon_2.status}"
    )

    print("\nPrincipal")
    print(
        f"Required:                 "
        f"{dashboard.principal.required}"
    )
    print(
        f"Funded:                   "
        f"{dashboard.principal.funded}"
    )
    print(
        f"Redeemed:                 "
        f"{dashboard.principal.redeemed}"
    )
    print(
        f"Defaulted:                "
        f"{dashboard.principal.is_defaulted}"
    )
    print(
        f"Status:                   "
        f"{dashboard.principal.status}"
    )

    assert (
        dashboard.issuer_address.lower()
        == ISSUER_ADDRESS.lower()
    )

    assert dashboard.lifecycle_value == 0
    assert dashboard.lifecycle_name == "Draft"

    assert dashboard.subscription_open is False
    assert dashboard.subscription_paused is False

    assert dashboard.can_open_subscription is True
    assert dashboard.can_finalize is False
    assert dashboard.can_withdraw_proceeds is False
    assert dashboard.can_close is False

    assert dashboard.total_raised == Decimal("0")
    assert dashboard.escrow_balance == Decimal("0")
    assert dashboard.withdrawable_proceeds == Decimal("0")
    assert dashboard.proceeds_withdrawn is False

    assert dashboard.coupon_1.required == Decimal("0")
    assert dashboard.coupon_1.funded == Decimal("0")
    assert dashboard.coupon_1.claimed == Decimal("0")
    assert dashboard.coupon_1.is_defaulted is False

    assert dashboard.coupon_2.required == Decimal("0")
    assert dashboard.coupon_2.funded == Decimal("0")
    assert dashboard.coupon_2.claimed == Decimal("0")
    assert dashboard.coupon_2.is_defaulted is False

    assert dashboard.principal.required == Decimal("0")
    assert dashboard.principal.funded == Decimal("0")
    assert dashboard.principal.redeemed == Decimal("0")
    assert dashboard.principal.is_defaulted is False

    assert dashboard.total_funding_gap == Decimal("0")
    assert dashboard.is_defaulted is False

    print("\n[OK] Issuer wallet and roles are valid.")
    print("[OK] Issuer obligations are consistent.")
    print("[OK] Base deployment remains in Draft.")
    print("[OK] No transaction was created.")


if __name__ == "__main__":
    main()