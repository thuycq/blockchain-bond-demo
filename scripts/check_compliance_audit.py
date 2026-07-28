from __future__ import annotations

import sys
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
from app.compliance import (  # noqa: E402
    build_compliance_report,
)
from app.config import (  # noqa: E402
    INVESTOR_1_ADDRESS,
    INVESTOR_2_ADDRESS,
)
from app.investor import (  # noqa: E402
    get_investor_position,
)
from app.issuer import (  # noqa: E402
    get_issuer_dashboard,
)
from app.overview import (  # noqa: E402
    get_bond_overview,
)


def main() -> None:
    print("=" * 72)
    print("BOND 6.10 - COMPLIANCE AUDIT CHECK")
    print("=" * 72)

    client = BlockchainClient()

    network = client.get_network_status()

    contract_statuses = (
        client.get_all_contract_code_statuses()
    )

    system_state = client.get_system_state()

    overview = get_bond_overview(
        client
    )

    issuer_dashboard = get_issuer_dashboard(
        client
    )

    investor_positions = {
        "Investor 1": get_investor_position(
            client,
            INVESTOR_1_ADDRESS,
            "Investor 1",
        ),
        "Investor 2": get_investor_position(
            client,
            INVESTOR_2_ADDRESS,
            "Investor 2",
        ),
    }

    report = build_compliance_report(
        chain_id=network.chain_id,
        contract_statuses=contract_statuses,
        system_state=system_state,
        overview=overview,
        issuer_dashboard=issuer_dashboard,
        investor_positions=investor_positions,
    )

    for check in report.checks:
        print(
            f"[{check.status:<4}] "
            f"{check.category:<12} "
            f"{check.check_name}"
        )

    print("\nSummary")
    print(
        f"Passed:       {report.pass_count}"
    )
    print(
        f"Warnings:     {report.warning_count}"
    )
    print(
        f"Failed:       {report.fail_count}"
    )
    print(
        f"Information:  {report.info_count}"
    )
    print(
        f"Overall:      {report.overall_status}"
    )

    assert report.fail_count == 0
    assert report.overall_status in {
        "PASSED",
        "PASSED WITH WARNINGS",
    }

    print(
        "\n[OK] Compliance report contains no failed checks."
    )
    print(
        "[OK] Deployment references and roles are valid."
    )
    print(
        "[OK] Financial and lifecycle checks are consistent."
    )
    print(
        "[OK] No transaction was created."
    )


if __name__ == "__main__":
    main()