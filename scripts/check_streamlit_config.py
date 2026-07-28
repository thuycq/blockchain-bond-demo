from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.config import (  # noqa: E402
    ADMIN_ADDRESS,
    BOND_TOKEN_ABI,
    BOND_TOKEN_ABI_FILE,
    BOND_TOKEN_ADDRESS,
    BOND_USD_ADDRESS,
    CHAIN_ID,
    DEPLOYMENT_FILE,
    INVESTOR_1_ADDRESS,
    INVESTOR_2_ADDRESS,
    ISSUER_ADDRESS,
    NETWORK_NAME,
    SEPOLIA_RPC_URL,
    TOKENIZED_BOND_ABI,
    TOKENIZED_BOND_ABI_FILE,
    TOKENIZED_BOND_ADDRESS,
)


def mask_rpc_url(rpc_url: str) -> str:
    """Do not print the full private RPC endpoint."""
    if len(rpc_url) <= 18:
        return "[configured]"

    return f"{rpc_url[:12]}...{rpc_url[-6:]}"


def main() -> None:
    print("=" * 70)
    print("BOND 6.2 - STREAMLIT CONFIG CHECK")
    print("=" * 70)

    print("\nNetwork")
    print(f"Name:     {NETWORK_NAME}")
    print(f"Chain ID: {CHAIN_ID}")
    print(f"RPC:      {mask_rpc_url(SEPOLIA_RPC_URL)}")

    print("\nDeployment files")
    print(f"Deployment:     {DEPLOYMENT_FILE}")
    print(f"BondToken ABI:  {BOND_TOKEN_ABI_FILE}")
    print(f"Tokenized ABI:  {TOKENIZED_BOND_ABI_FILE}")

    print("\nContract addresses")
    print(f"BondUSDToken:   {BOND_USD_ADDRESS}")
    print(f"BondToken:      {BOND_TOKEN_ADDRESS}")
    print(f"TokenizedBond:  {TOKENIZED_BOND_ADDRESS}")

    print("\nRoles")
    print(f"Admin:          {ADMIN_ADDRESS}")
    print(f"Issuer:         {ISSUER_ADDRESS}")
    print(f"Investor 1:     {INVESTOR_1_ADDRESS}")
    print(f"Investor 2:     {INVESTOR_2_ADDRESS}")

    print("\nABI")
    print(f"BondToken ABI entries:     {len(BOND_TOKEN_ABI)}")
    print(f"TokenizedBond ABI entries: {len(TOKENIZED_BOND_ABI)}")

    print("\n[OK] BOND 6.2 configuration loaded successfully.")
    print("No private key was loaded or displayed.")


if __name__ == "__main__":
    main()