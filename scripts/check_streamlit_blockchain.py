from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.blockchain import (  # noqa: E402
    BlockchainClient,
    BlockchainError,
)


def main() -> None:
    print("=" * 72)
    print("BOND 6.3 - STREAMLIT BLOCKCHAIN CONNECTION CHECK")
    print("=" * 72)

    try:
        client = BlockchainClient()

        network = client.get_network_status()

        print("\nNetwork")
        print(f"Connected:     {network.connected}")
        print(f"Chain ID:      {network.chain_id}")
        print(f"Latest block:  {network.latest_block}")
        print(f"Gas price:     {network.gas_price_gwei} Gwei")

        print("\nContract bytecode")
        for status in client.get_all_contract_code_statuses():
            print(
                f"{status.contract_name:<16} "
                f"code={status.has_code} "
                f"bytes={status.bytecode_size} "
                f"address={status.address}"
            )

        bond_usd = client.get_bond_usd_metadata()
        bond_token = client.get_bond_token_metadata()

        print("\nBondUSD")
        print(f"Name:          {bond_usd.name}")
        print(f"Symbol:        {bond_usd.symbol}")
        print(f"Decimals:      {bond_usd.decimals}")
        print(f"Total supply:  {bond_usd.total_supply_display}")

        print("\nBondToken")
        print(f"Name:          {bond_token.name}")
        print(f"Symbol:        {bond_token.symbol}")
        print(f"Decimals:      {bond_token.decimals}")
        print(f"Total supply:  {bond_token.total_supply_display}")

        state = client.get_system_state()

        print("\nTokenizedBond roles and references")
        print(f"Admin:          {state.admin}")
        print(f"Issuer:         {state.issuer}")
        print(f"Payment token:  {state.payment_token}")
        print(f"Bond token:     {state.bond_token}")
        print(f"Controller:     {state.bond_token_controller}")
        print(f"Bond owner:     {state.bond_token_owner}")

        print("\nBase deployment state")
        print(
            f"Lifecycle:              "
            f"{state.lifecycle_name} "
            f"({state.lifecycle_value})"
        )
        print(
            f"Subscription paused:    "
            f"{state.subscription_paused}"
        )
        print(
            f"Subscription start:     "
            f"{state.subscription_start}"
        )
        print(
            f"Subscription deadline:  "
            f"{state.subscription_deadline}"
        )
        print(
            f"Total subscribed:       "
            f"{state.total_subscribed}"
        )
        print(
            f"Total raised:           "
            f"{state.total_raised_display} BONDUSD"
        )
        print(
            f"Proceeds withdrawn:     "
            f"{state.proceeds_withdrawn}"
        )
        print(
            f"BondToken supply:       "
            f"{state.bond_token_supply}"
        )
        print(
            f"Escrow balance:         "
            f"{state.escrow_balance_display} BONDUSD"
        )

        validation_errors = client.validate_base_deployment()

        if validation_errors:
            print("\n[ERROR] Base deployment validation failed:")

            for error in validation_errors:
                print(f"- {error}")

            raise SystemExit(1)

        print("\n[OK] Sepolia connection and contracts are valid.")
        print("[OK] Base deployment remains clean and in Draft.")
        print("[OK] No transaction was created.")

    except BlockchainError as exc:
        print(f"\n[ERROR] {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()