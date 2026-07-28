from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from web3 import Web3


class ConfigError(RuntimeError):
    """Raised when the local Streamlit configuration is invalid."""


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT_DIR = PROJECT_ROOT / "deployment"
DEPLOYMENT_FILE = DEPLOYMENT_DIR / "sepolia.json"
ABI_DIR = DEPLOYMENT_DIR / "abi"

BOND_TOKEN_ABI_FILE = ABI_DIR / "BondToken.json"
TOKENIZED_BOND_ABI_FILE = ABI_DIR / "TokenizedBond.json"

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


# ============================================================
# Expected Sepolia deployment
# ============================================================

EXPECTED_CHAIN_ID = 11155111
NETWORK_NAME = "Ethereum Sepolia"
ETHERSCAN_BASE_URL = "https://sepolia.etherscan.io"

EXPECTED_CONTRACT_ADDRESSES = {
    "BondUSDToken": "0xcDe41c009D3fFd58CaA9a4CC561155c2616B7D7D",
    "BondToken": "0x47F8629e610489903bbc752f34421CFb068647cc",
    "TokenizedBond": "0x4ce75ac4FC853d8b683C649Ec7a10A2eA4ad65E3",
}

EXPECTED_ROLE_ADDRESSES = {
    "admin": "0x09428D10764503E9158374e556398b409d37381E",
    "issuer": "0x9D4C235100Ddfd5d61326769e16b2BB9dE04074e",
    "investor1": "0x054d225D719B6326b45c50f3dd3c5275234d96C3",
    "investor2": "0x6426d2Bd9b9c21218f805C5C54A7c7FAB3a6DEc2",
}


# ============================================================
# JSON helpers
# ============================================================

def read_json(path: Path) -> Any:
    """Read and decode a UTF-8 JSON file."""
    if not path.exists():
        raise ConfigError(f"Không tìm thấy file: {path}")

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"File JSON không hợp lệ: {path}\n"
            f"Chi tiết: {exc}"
        ) from exc


def extract_abi(path: Path) -> list[dict[str, Any]]:
    """
    Accept either:
    1. A plain ABI JSON array.
    2. A Hardhat artifact object containing the `abi` field.
    """
    data = read_json(path)

    if isinstance(data, list):
        return data

    if isinstance(data, dict) and isinstance(data.get("abi"), list):
        return data["abi"]

    raise ConfigError(
        f"Không tìm thấy ABI hợp lệ trong file: {path}"
    )


def normalize_key(value: str) -> str:
    """Normalize keys so BondUSDToken and bond_usd_token can match."""
    return "".join(character.lower() for character in value if character.isalnum())


def find_contract_entry(
    deployment: dict[str, Any],
    contract_name: str,
) -> Any | None:
    """
    Find a contract entry in common deployment JSON structures.

    Supported examples:
    {
        "contracts": {
            "BondToken": "0x..."
        }
    }

    {
        "contracts": {
            "BondToken": {
                "address": "0x..."
            }
        }
    }
    """
    target = normalize_key(contract_name)

    contracts = deployment.get("contracts", {})
    if isinstance(contracts, dict):
        for key, value in contracts.items():
            if normalize_key(str(key)) == target:
                return value

    for key, value in deployment.items():
        if normalize_key(str(key)) == target:
            return value

    return None


def extract_address_from_entry(entry: Any) -> str | None:
    """Extract an Ethereum address from a string or dictionary entry."""
    if isinstance(entry, str) and Web3.is_address(entry):
        return entry

    if isinstance(entry, dict):
        candidate_keys = (
            "address",
            "contractAddress",
            "contract_address",
        )

        for key in candidate_keys:
            value = entry.get(key)
            if isinstance(value, str) and Web3.is_address(value):
                return value

    return None


def get_contract_address(
    deployment: dict[str, Any],
    contract_name: str,
) -> str:
    """
    Read a contract address from sepolia.json.

    The known BOND 5 address is used only as a guarded fallback.
    """
    entry = find_contract_entry(deployment, contract_name)
    discovered_address = extract_address_from_entry(entry)
    expected_address = EXPECTED_CONTRACT_ADDRESSES[contract_name]

    if discovered_address is None:
        discovered_address = expected_address

    discovered_checksum = Web3.to_checksum_address(discovered_address)
    expected_checksum = Web3.to_checksum_address(expected_address)

    if discovered_checksum != expected_checksum:
        raise ConfigError(
            f"Địa chỉ {contract_name} trong sepolia.json không khớp "
            f"base deployment chính thức.\n"
            f"Trong JSON: {discovered_checksum}\n"
            f"Mong đợi:   {expected_checksum}"
        )

    return discovered_checksum


def get_chain_id(deployment: dict[str, Any]) -> int:
    """Read chain ID from common deployment JSON structures."""
    possible_values = (
        deployment.get("chainId"),
        deployment.get("chain_id"),
    )

    network = deployment.get("network")
    if isinstance(network, dict):
        possible_values += (
            network.get("chainId"),
            network.get("chain_id"),
        )

    for value in possible_values:
        if value is None:
            continue

        try:
            return int(value)
        except (TypeError, ValueError):
            continue

    return EXPECTED_CHAIN_ID


# ============================================================
# Load deployment and ABI
# ============================================================

DEPLOYMENT = read_json(DEPLOYMENT_FILE)

CHAIN_ID = get_chain_id(DEPLOYMENT)

if CHAIN_ID != EXPECTED_CHAIN_ID:
    raise ConfigError(
        f"Sai chain ID trong deployment file: {CHAIN_ID}. "
        f"Sepolia phải là {EXPECTED_CHAIN_ID}."
    )

BOND_USD_ADDRESS = get_contract_address(
    DEPLOYMENT,
    "BondUSDToken",
)

BOND_TOKEN_ADDRESS = get_contract_address(
    DEPLOYMENT,
    "BondToken",
)

TOKENIZED_BOND_ADDRESS = get_contract_address(
    DEPLOYMENT,
    "TokenizedBond",
)

ADMIN_ADDRESS = Web3.to_checksum_address(
    EXPECTED_ROLE_ADDRESSES["admin"]
)

ISSUER_ADDRESS = Web3.to_checksum_address(
    EXPECTED_ROLE_ADDRESSES["issuer"]
)

INVESTOR_1_ADDRESS = Web3.to_checksum_address(
    EXPECTED_ROLE_ADDRESSES["investor1"]
)

INVESTOR_2_ADDRESS = Web3.to_checksum_address(
    EXPECTED_ROLE_ADDRESSES["investor2"]
)

BOND_TOKEN_ABI = extract_abi(BOND_TOKEN_ABI_FILE)
TOKENIZED_BOND_ABI = extract_abi(TOKENIZED_BOND_ABI_FILE)


# ============================================================
# Minimal ERC-20 ABI for read-only BondUSD access
# ============================================================

BOND_USD_ABI: list[dict[str, Any]] = [
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "account",
                "type": "address",
            }
        ],
        "name": "balanceOf",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "owner",
                "type": "address",
            },
            {
                "internalType": "address",
                "name": "spender",
                "type": "address",
            },
        ],
        "name": "allowance",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


# ============================================================
# RPC settings
# ============================================================

SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "").strip()

if not SEPOLIA_RPC_URL:
    raise ConfigError(
        "Không tìm thấy SEPOLIA_RPC_URL trong file .env."
    )


def etherscan_address_url(address: str) -> str:
    """Create a Sepolia Etherscan address URL."""
    checksum_address = Web3.to_checksum_address(address)
    return f"{ETHERSCAN_BASE_URL}/address/{checksum_address}"


def etherscan_transaction_url(transaction_hash: str) -> str:
    """Create a Sepolia Etherscan transaction URL."""
    return f"{ETHERSCAN_BASE_URL}/tx/{transaction_hash}"