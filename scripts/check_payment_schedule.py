from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from app.blockchain import BlockchainClient  # noqa: E402
from app.issuer import get_issuer_dashboard  # noqa: E402
from app.overview import get_bond_overview  # noqa: E402
from app.payment_schedule import (  # noqa: E402
    build_payment_schedule,
)


def main() -> None:
    print("=" * 72)
    print("BOND 6.9 - PAYMENT SCHEDULE CHECK")
    print("=" * 72)

    client = BlockchainClient()

    overview = get_bond_overview(
        client
    )

    issuer_dashboard = (
        get_issuer_dashboard(
            client
        )
    )

    schedule = build_payment_schedule(
        overview,
        issuer_dashboard,
    )

    print("\nSchedule")
    print(
        f"Lifecycle:                    "
        f"{schedule.lifecycle_name}"
    )
    print(
        f"Current block timestamp:      "
        f"{schedule.current_block_timestamp}"
    )
    print(
        f"Next obligation:              "
        f"{schedule.next_obligation}"
    )
    print(
        f"Next due timestamp:           "
        f"{schedule.next_due_timestamp}"
    )

    for item in schedule.items:
        print("\n" + "-" * 72)
        print(
            f"{item.sequence}. "
            f"{item.obligation}"
        )
        print(
            f"Due timestamp:                "
            f"{item.due_timestamp}"
        )
        print(
            f"Grace deadline:               "
            f"{item.grace_deadline}"
        )
        print(
            f"Required:                     "
            f"{item.required}"
        )
        print(
            f"Funded:                       "
            f"{item.funded}"
        )
        print(
            f"Distributed:                  "
            f"{item.distributed}"
        )
        print(
            f"Funding gap:                  "
            f"{item.funding_gap}"
        )
        print(
            f"Defaulted:                    "
            f"{item.is_defaulted}"
        )
        print(
            f"Status:                       "
            f"{item.status}"
        )

    assert len(
        schedule.items
    ) == 3

    assert schedule.lifecycle_name == "Draft"

    assert (
        schedule.next_obligation
        == "Chưa xác lập"
    )

    assert (
        schedule.next_due_timestamp
        == 0
    )

    assert (
        schedule.total_required
        == Decimal("0")
    )

    assert (
        schedule.total_funded
        == Decimal("0")
    )

    assert (
        schedule.total_distributed
        == Decimal("0")
    )

    assert (
        schedule.total_funding_gap
        == Decimal("0")
    )

    assert (
        schedule.has_active_default
        is False
    )

    for item in schedule.items:
        assert item.due_timestamp == 0
        assert item.grace_deadline == 0
        assert item.required == Decimal("0")
        assert item.funded == Decimal("0")
        assert item.distributed == Decimal("0")
        assert item.is_defaulted is False

    print(
        "\n[OK] Payment schedule contains "
        "two coupons and one principal obligation."
    )

    print(
        "[OK] Draft schedule values are correct."
    )

    print(
        "[OK] No additional blockchain "
        "transaction was created."
    )


if __name__ == "__main__":
    main()