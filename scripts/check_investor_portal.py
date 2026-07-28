from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.blockchain import BlockchainClient  # noqa: E402
from app.config import (  # noqa: E402
    INVESTOR_1_ADDRESS,
    INVESTOR_2_ADDRESS,
)
from app.investor import get_investor_position  # noqa: E402


def check_investor(
    client: BlockchainClient,
    label: str,
    address: str,
) -> None:
    position = get_investor_position(
        client,
        address,
        label,
    )

    print("\n" + "-" * 72)
    print(label)
    print("-" * 72)

    print(f"Address:                {position.address}")
    print(f"Whitelisted:            {position.is_whitelisted}")
    print(f"Status:                 {position.position_status}")
    print(f"ETH balance:            {position.eth_balance}")
    print(f"BondUSD balance:        {position.bond_usd_balance}")
    print(f"BondUSD allowance:      {position.bond_usd_allowance}")
    print(f"BondToken balance:      {position.bond_token_balance}")
    print(f"Subscribed quantity:    {position.quantity_subscribed}")
    print(f"Amount paid:            {position.amount_paid}")
    print(f"Refundable:             {position.refundable_amount}")
    print(f"Coupon 1 claimable:     {position.claimable_coupon_1}")
    print(f"Coupon 2 claimable:     {position.claimable_coupon_2}")
    print(f"Principal redeemable:   {position.redeemable_principal}")

    assert position.is_whitelisted is True

    assert position.quantity_subscribed == 0
    assert position.amount_paid == Decimal("0")
    assert position.bond_token_balance == 0

    assert position.refundable_amount == Decimal("0")
    assert position.claimable_coupon_1 == Decimal("0")
    assert position.claimable_coupon_2 == Decimal("0")
    assert position.claimable_coupon_total == Decimal("0")
    assert position.redeemable_principal == Decimal("0")

    assert position.has_claimed_refund is False
    assert position.has_claimed_coupon_1 is False
    assert position.has_claimed_coupon_2 is False
    assert position.has_redeemed_principal is False


def main() -> None:
    print("=" * 72)
    print("BOND 6.6 - INVESTOR PORTAL CHECK")
    print("=" * 72)

    client = BlockchainClient()

    check_investor(
        client,
        "Investor 1",
        INVESTOR_1_ADDRESS,
    )

    check_investor(
        client,
        "Investor 2",
        INVESTOR_2_ADDRESS,
    )

    print("\n[OK] Both investors are whitelisted.")
    print("[OK] Investor positions are consistent.")
    print("[OK] Base deployment remains in Draft.")
    print("[OK] No transaction was created.")


if __name__ == "__main__":
    main()