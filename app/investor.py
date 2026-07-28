from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from web3 import Web3
from web3.exceptions import Web3Exception

from app.blockchain import (
    BlockchainClient,
    BlockchainError,
)
from app.config import TOKENIZED_BOND_ADDRESS


@dataclass(frozen=True)
class InvestorPosition:
    label: str
    address: str

    lifecycle_name: str
    position_status: str

    eth_balance: Decimal
    bond_usd_balance: Decimal
    bond_token_balance: int
    bond_usd_allowance: Decimal

    is_whitelisted: bool

    quantity_subscribed: int
    amount_paid: Decimal

    has_claimed_refund: bool
    has_claimed_coupon_1: bool
    has_claimed_coupon_2: bool
    has_redeemed_principal: bool

    refundable_amount: Decimal

    claimable_coupon_1: Decimal
    claimable_coupon_2: Decimal
    claimable_coupon_total: Decimal

    redeemable_principal: Decimal


def _derive_position_status(
    *,
    is_whitelisted: bool,
    quantity_subscribed: int,
    refundable_amount: Decimal,
    claimable_coupon_total: Decimal,
    redeemable_principal: Decimal,
) -> str:
    """Create a concise status for the selected investor."""
    if not is_whitelisted:
        return "Not whitelisted"

    if refundable_amount > 0:
        return "Refund available"

    if redeemable_principal > 0:
        return "Principal redemption available"

    if claimable_coupon_total > 0:
        return "Coupon available"

    if quantity_subscribed > 0:
        return "Bond position active"

    return "Whitelisted – no subscription yet"


def get_investor_position(
    client: BlockchainClient,
    investor_address: str,
    label: str,
) -> InvestorPosition:
    """
    Read and validate one investor position from Sepolia.

    The function uses getInvestorPosition() as the main aggregate view
    and cross-checks it against the public mappings and helper views.
    """
    try:
        address = Web3.to_checksum_address(
            investor_address
        )

        contract = client.tokenized_bond

        position_result = (
            contract.functions
            .getInvestorPosition(address)
            .call()
        )

        position_values = list(position_result)

        if len(position_values) != 11:
            raise BlockchainError(
                "getInvestorPosition() phải trả về 11 trường, "
                f"nhưng nhận được {len(position_values)} trường."
            )

        (
            aggregate_whitelisted,
            aggregate_quantity,
            aggregate_paid_raw,
            aggregate_bond_balance,
            aggregate_refund_claimed,
            aggregate_coupon_1_claimed,
            aggregate_coupon_2_claimed,
            aggregate_principal_redeemed,
            aggregate_refundable_raw,
            aggregate_coupon_total_raw,
            aggregate_principal_raw,
        ) = position_values

        # ----------------------------------------------------
        # Cross-check against public mappings
        # ----------------------------------------------------

        is_whitelisted = bool(
            contract.functions
            .whitelisted(address)
            .call()
        )

        quantity_subscribed = int(
            contract.functions
            .subscribedQuantity(address)
            .call()
        )

        amount_paid_raw = int(
            contract.functions
            .paidAmount(address)
            .call()
        )

        has_claimed_refund = bool(
            contract.functions
            .refundClaimed(address)
            .call()
        )

        has_claimed_coupon_1 = bool(
            contract.functions
            .couponClaimed(1, address)
            .call()
        )

        has_claimed_coupon_2 = bool(
            contract.functions
            .couponClaimed(2, address)
            .call()
        )

        has_redeemed_principal = bool(
            contract.functions
            .principalRedeemed(address)
            .call()
        )

        bond_token_balance = int(
            client.get_bond_token_balance(address)
        )

        # ----------------------------------------------------
        # Helper view functions
        # ----------------------------------------------------

        refundable_raw = int(
            contract.functions
            .getRefundAmount(address)
            .call()
        )

        claimable_coupon_1_raw = int(
            contract.functions
            .getClaimableCoupon(address, 1)
            .call()
        )

        claimable_coupon_2_raw = int(
            contract.functions
            .getClaimableCoupon(address, 2)
            .call()
        )

        claimable_coupon_total_raw = (
            claimable_coupon_1_raw
            + claimable_coupon_2_raw
        )

        redeemable_principal_raw = int(
            contract.functions
            .getPrincipalAmount(address)
            .call()
        )

        # ----------------------------------------------------
        # Validate aggregate view consistency
        # ----------------------------------------------------

        validations = [
            (
                bool(aggregate_whitelisted)
                == is_whitelisted,
                "Whitelist status",
            ),
            (
                int(aggregate_quantity)
                == quantity_subscribed,
                "Subscribed quantity",
            ),
            (
                int(aggregate_paid_raw)
                == amount_paid_raw,
                "Amount paid",
            ),
            (
                int(aggregate_bond_balance)
                == bond_token_balance,
                "BondToken balance",
            ),
            (
                bool(aggregate_refund_claimed)
                == has_claimed_refund,
                "Refund claimed",
            ),
            (
                bool(aggregate_coupon_1_claimed)
                == has_claimed_coupon_1,
                "Coupon 1 claimed",
            ),
            (
                bool(aggregate_coupon_2_claimed)
                == has_claimed_coupon_2,
                "Coupon 2 claimed",
            ),
            (
                bool(aggregate_principal_redeemed)
                == has_redeemed_principal,
                "Principal redeemed",
            ),
            (
                int(aggregate_refundable_raw)
                == refundable_raw,
                "Refundable amount",
            ),
            (
                int(aggregate_coupon_total_raw)
                == claimable_coupon_total_raw,
                "Claimable coupon total",
            ),
            (
                int(aggregate_principal_raw)
                == redeemable_principal_raw,
                "Redeemable principal",
            ),
        ]

        inconsistent_fields = [
            field_name
            for is_valid, field_name in validations
            if not is_valid
        ]

        if inconsistent_fields:
            raise BlockchainError(
                "Investor view không nhất quán tại các trường: "
                + ", ".join(inconsistent_fields)
            )

        # ----------------------------------------------------
        # Token values
        # ----------------------------------------------------

        bond_usd_decimals = int(
            client.bond_usd.functions
            .decimals()
            .call()
        )

        eth_balance = client.get_eth_balance(
            address
        )

        bond_usd_balance = (
            client.get_bond_usd_balance(address)
        )

        allowance_raw = int(
            client.bond_usd.functions
            .allowance(
                address,
                Web3.to_checksum_address(
                    TOKENIZED_BOND_ADDRESS
                ),
            )
            .call()
        )

        amount_paid = client.format_units(
            amount_paid_raw,
            bond_usd_decimals,
        )

        refundable_amount = client.format_units(
            refundable_raw,
            bond_usd_decimals,
        )

        claimable_coupon_1 = client.format_units(
            claimable_coupon_1_raw,
            bond_usd_decimals,
        )

        claimable_coupon_2 = client.format_units(
            claimable_coupon_2_raw,
            bond_usd_decimals,
        )

        claimable_coupon_total = client.format_units(
            claimable_coupon_total_raw,
            bond_usd_decimals,
        )

        redeemable_principal = client.format_units(
            redeemable_principal_raw,
            bond_usd_decimals,
        )

        bond_usd_allowance = client.format_units(
            allowance_raw,
            bond_usd_decimals,
        )

        system_state = client.get_system_state()

        position_status = _derive_position_status(
            is_whitelisted=is_whitelisted,
            quantity_subscribed=quantity_subscribed,
            refundable_amount=refundable_amount,
            claimable_coupon_total=(
                claimable_coupon_total
            ),
            redeemable_principal=(
                redeemable_principal
            ),
        )

        return InvestorPosition(
            label=label,
            address=address,
            lifecycle_name=(
                system_state.lifecycle_name
            ),
            position_status=position_status,
            eth_balance=eth_balance,
            bond_usd_balance=bond_usd_balance,
            bond_token_balance=bond_token_balance,
            bond_usd_allowance=bond_usd_allowance,
            is_whitelisted=is_whitelisted,
            quantity_subscribed=quantity_subscribed,
            amount_paid=amount_paid,
            has_claimed_refund=(
                has_claimed_refund
            ),
            has_claimed_coupon_1=(
                has_claimed_coupon_1
            ),
            has_claimed_coupon_2=(
                has_claimed_coupon_2
            ),
            has_redeemed_principal=(
                has_redeemed_principal
            ),
            refundable_amount=refundable_amount,
            claimable_coupon_1=(
                claimable_coupon_1
            ),
            claimable_coupon_2=(
                claimable_coupon_2
            ),
            claimable_coupon_total=(
                claimable_coupon_total
            ),
            redeemable_principal=(
                redeemable_principal
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
            "Không thể đọc vị thế investor "
            f"{investor_address}: {exc}"
        ) from exc