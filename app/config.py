from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from web3 import Web3


class ConfigError(RuntimeError):
    """Raised when the Streamlit configuration is invalid."""


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
# Network
# ============================================================

EXPECTED_CHAIN_ID = 11155111
NETWORK_NAME = "Ethereum Sepolia"
ETHERSCAN_BASE_URL = "https://sepolia.etherscan.io"
SEPOLIA_CHAIN_ID_HEX = "0xaa36a7"


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
    Accept either a plain ABI array or a Hardhat artifact
    containing an `abi` field.
    """
    data = read_json(path)

    if isinstance(data, list):
        return data

    if (
        isinstance(data, dict)
        and isinstance(data.get("abi"), list)
    ):
        return data["abi"]

    raise ConfigError(
        f"Không tìm thấy ABI hợp lệ trong file: {path}"
    )


def require_address(
    value: Any,
    label: str,
) -> str:
    """Validate and checksum one Ethereum address."""
    if not isinstance(value, str):
        raise ConfigError(
            f"{label} không phải chuỗi địa chỉ."
        )

    if not Web3.is_address(value):
        raise ConfigError(
            f"{label} không phải địa chỉ Ethereum hợp lệ: "
            f"{value}"
        )

    return Web3.to_checksum_address(value)


def contract_address(
    deployment: dict[str, Any],
    contract_name: str,
) -> str:
    """Read one contract address from deployment/sepolia.json."""
    contracts = deployment.get("contracts")

    if not isinstance(contracts, dict):
        raise ConfigError(
            "sepolia.json không có trường contracts hợp lệ."
        )

    entry = contracts.get(contract_name)

    if not isinstance(entry, dict):
        raise ConfigError(
            f"Không tìm thấy deployment của {contract_name}."
        )

    return require_address(
        entry.get("address"),
        f"{contract_name} address",
    )


def role_address(
    deployment: dict[str, Any],
    role_name: str,
) -> str:
    """Read one configured role from deployment/sepolia.json."""
    roles = deployment.get("roles")

    if not isinstance(roles, dict):
        raise ConfigError(
            "sepolia.json không có trường roles hợp lệ."
        )

    return require_address(
        roles.get(role_name),
        f"{role_name} address",
    )


# ============================================================
# Load clean V2 deployment
# ============================================================

DEPLOYMENT = read_json(DEPLOYMENT_FILE)

CHAIN_ID = int(
    DEPLOYMENT.get(
        "chainId",
        EXPECTED_CHAIN_ID,
    )
)

if CHAIN_ID != EXPECTED_CHAIN_ID:
    raise ConfigError(
        f"Sai chain ID trong deployment file: {CHAIN_ID}. "
        f"Sepolia phải là {EXPECTED_CHAIN_ID}."
    )

DEPLOYMENT_VERSION = str(
    DEPLOYMENT.get("version", "")
)

if (
    DEPLOYMENT_VERSION
    != "v2-whitelist-self-registration"
):
    raise ConfigError(
        "Ứng dụng yêu cầu clean deployment V2 có "
        "whitelist self-registration."
    )

if DEPLOYMENT.get("cleanDeployment") is not True:
    raise ConfigError(
        "Deployment hiện tại không được đánh dấu là clean."
    )

BOND_USD_ADDRESS = contract_address(
    DEPLOYMENT,
    "BondUSDToken",
)

BOND_TOKEN_ADDRESS = contract_address(
    DEPLOYMENT,
    "BondToken",
)

TOKENIZED_BOND_ADDRESS = contract_address(
    DEPLOYMENT,
    "TokenizedBond",
)

ADMIN_ADDRESS = role_address(
    DEPLOYMENT,
    "admin",
)

ISSUER_ADDRESS = role_address(
    DEPLOYMENT,
    "issuer",
)

EXPECTED_CONTRACT_ADDRESSES = {
    "BondUSDToken": BOND_USD_ADDRESS,
    "BondToken": BOND_TOKEN_ADDRESS,
    "TokenizedBond": TOKENIZED_BOND_ADDRESS,
}

EXPECTED_ROLE_ADDRESSES = {
    "admin": ADMIN_ADDRESS,
    "issuer": ISSUER_ADDRESS,
}

BOND_TOKEN_ABI = extract_abi(
    BOND_TOKEN_ABI_FILE
)

TOKENIZED_BOND_ABI = extract_abi(
    TOKENIZED_BOND_ABI_FILE
)


# ============================================================
# BondUSD ERC-20 and owner ABI
# ============================================================

BOND_USD_ABI: list[dict[str, Any]] = [
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "spender",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "value",
                "type": "uint256",
            },
        ],
        "name": "Approval",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "from",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "to",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "value",
                "type": "uint256",
            },
        ],
        "name": "Transfer",
        "type": "event",
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [
            {
                "internalType": "uint8",
                "name": "",
                "type": "uint8",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
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
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "spender",
                "type": "address",
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256",
            },
        ],
        "name": "approve",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool",
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "to",
                "type": "address",
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256",
            },
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


# ============================================================
# RPC settings
# ============================================================

def load_rpc_url() -> str:
    """
    Read Sepolia RPC from local .env or Streamlit Cloud secrets.
    No private key is loaded by the application.
    """
    environment_value = os.getenv(
        "SEPOLIA_RPC_URL",
        "",
    ).strip()

    if environment_value:
        return environment_value

    try:
        secret_value = st.secrets.get(
            "SEPOLIA_RPC_URL",
            "",
        )

        if secret_value:
            return str(secret_value).strip()
    except (
        FileNotFoundError,
        KeyError,
        RuntimeError,
    ):
        pass

    return ""


SEPOLIA_RPC_URL = load_rpc_url()

if not SEPOLIA_RPC_URL:
    raise ConfigError(
        "Không tìm thấy SEPOLIA_RPC_URL. "
        "Local: khai báo trong .env. "
        "Streamlit Cloud: khai báo trong App Settings > Secrets."
    )


# ============================================================
# URL helpers
# ============================================================

def etherscan_address_url(
    address: str,
) -> str:
    """Create a Sepolia Etherscan address URL."""
    checksum_address = Web3.to_checksum_address(
        address
    )

    return (
        f"{ETHERSCAN_BASE_URL}/address/"
        f"{checksum_address}"
    )


def etherscan_transaction_url(
    transaction_hash: str,
) -> str:
    """Create a Sepolia Etherscan transaction URL."""
    return (
        f"{ETHERSCAN_BASE_URL}/tx/"
        f"{transaction_hash}"
    )
