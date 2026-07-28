from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from web3 import Web3
from web3.exceptions import Web3Exception

from app.blockchain import (
    BlockchainClient,
    BlockchainError,
)
from app.config import (
    ADMIN_ADDRESS,
    INVESTOR_1_ADDRESS,
    INVESTOR_2_ADDRESS,
    ISSUER_ADDRESS,
)
from app.investor import (
    InvestorPosition,
    get_investor_position,
)


@dataclass(frozen=True)
class WhitelistAccount:
    """Read-only information for one known wallet."""

    label: str
    address: str
    role: str

    is_whitelisted: bool
    subscribed_quantity: int
    amount_paid: Decimal

    bond_usd_balance: Decimal
    bond_token_balance: int


@dataclass(frozen=True)
class AdminDashboard:
    """Complete read-only state for the Admin Dashboard."""

    admin_address: str

    lifecycle_value: int
    lifecycle_name: str

    eth_balance: Decimal
    bond_usd_balance: Decimal

    subscription_paused: bool
    subscription_open: bool

    known_accounts: tuple[WhitelistAccount, ...]

    whitelisted_demo_count: int
    total_demo_accounts: int


def _to_whitelist_account(
    position: InvestorPosition,
    role: str,
) -> WhitelistAccount:
    """Convert an investor position into a whitelist table entry."""
    return WhitelistAccount(
        label=position.label,
        address=position.address,
        role=role,
        is_whitelisted=position.is_whitelisted,
        subscribed_quantity=position.quantity_subscribed,
        amount_paid=position.amount_paid,
        bond_usd_balance=position.bond_usd_balance,
        bond_token_balance=position.bond_token_balance,
    )


def inspect_wallet(
    client: BlockchainClient,
    wallet_address: str,
    label: str = "Inspected Wallet",
) -> InvestorPosition:
    """Inspect any valid Ethereum address without creating a transaction."""
    if not Web3.is_address(wallet_address):
        raise BlockchainError(
            "Địa chỉ ví không hợp lệ. "
            "Địa chỉ Ethereum phải có dạng 0x và gồm 40 ký tự hex."
        )

    checksum_address = Web3.to_checksum_address(
        wallet_address
    )

    return get_investor_position(
        client,
        checksum_address,
        label,
    )


def get_admin_dashboard(
    client: BlockchainClient,
) -> AdminDashboard:
    """Build the complete read-only Admin Dashboard."""
    try:
        admin_address = Web3.to_checksum_address(
            ADMIN_ADDRESS
        )

        system_state = client.get_system_state()

        subscription_open = bool(
            client.tokenized_bond.functions
            .isSubscriptionOpen()
            .call()
        )

        admin_position = get_investor_position(
            client,
            ADMIN_ADDRESS,
            "Admin",
        )

        issuer_position = get_investor_position(
            client,
            ISSUER_ADDRESS,
            "Issuer",
        )

        investor_1_position = get_investor_position(
            client,
            INVESTOR_1_ADDRESS,
            "Investor 1",
        )

        investor_2_position = get_investor_position(
            client,
            INVESTOR_2_ADDRESS,
            "Investor 2",
        )

        known_accounts = (
            _to_whitelist_account(
                admin_position,
                "Admin",
            ),
            _to_whitelist_account(
                issuer_position,
                "Issuer",
            ),
            _to_whitelist_account(
                investor_1_position,
                "Investor",
            ),
            _to_whitelist_account(
                investor_2_position,
                "Investor",
            ),
        )

        whitelisted_demo_count = sum(
            1
            for account in known_accounts
            if account.is_whitelisted
        )

        return AdminDashboard(
            admin_address=admin_address,
            lifecycle_value=system_state.lifecycle_value,
            lifecycle_name=system_state.lifecycle_name,
            eth_balance=client.get_eth_balance(
                admin_address
            ),
            bond_usd_balance=(
                client.get_bond_usd_balance(
                    admin_address
                )
            ),
            subscription_paused=(
                system_state.subscription_paused
            ),
            subscription_open=subscription_open,
            known_accounts=known_accounts,
            whitelisted_demo_count=(
                whitelisted_demo_count
            ),
            total_demo_accounts=len(
                known_accounts
            ),
        )

    except BlockchainError:
        raise

    except (
        ValueError,
        TypeError,
        Web3Exception,
    ) as exc:
        raise BlockchainError(
            f"Không thể xây dựng Admin Dashboard: {exc}"
        ) from exc