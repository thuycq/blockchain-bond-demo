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
    ISSUER_ADDRESS,
    TOKENIZED_BOND_ADDRESS,
)


@dataclass(frozen=True)
class CouponObligation:
    """Read-only information for one coupon period."""

    period: int
    due_timestamp: int

    required: Decimal
    funded: Decimal
    claimed: Decimal

    funding_gap: Decimal
    unclaimed_amount: Decimal

    is_defaulted: bool
    defaulted_at: int
    has_default_history: bool

    can_deposit: bool
    status: str


@dataclass(frozen=True)
class PrincipalObligation:
    """Read-only information for principal repayment."""

    maturity_timestamp: int

    required: Decimal
    funded: Decimal
    redeemed: Decimal

    funding_gap: Decimal
    unredeemed_amount: Decimal

    is_defaulted: bool
    defaulted_at: int
    has_default_history: bool

    can_deposit: bool
    status: str


@dataclass(frozen=True)
class IssuerDashboard:
    """Complete read-only state for the issuer dashboard."""

    issuer_address: str

    lifecycle_value: int
    lifecycle_name: str

    eth_balance: Decimal
    bond_usd_balance: Decimal
    bond_usd_allowance: Decimal

    total_raised: Decimal
    escrow_balance: Decimal

    proceeds_withdrawn: bool
    withdrawable_proceeds: Decimal

    subscription_paused: bool
    subscription_open: bool

    can_open_subscription: bool
    can_finalize: bool
    can_withdraw_proceeds: bool
    can_close: bool

    coupon_1: CouponObligation
    coupon_2: CouponObligation
    principal: PrincipalObligation

    total_funding_gap: Decimal
    total_unclaimed_obligations: Decimal

    is_defaulted: bool
    current_block_timestamp: int


def _derive_coupon_status(
    *,
    required: Decimal,
    funded: Decimal,
    due_timestamp: int,
    grace_period_seconds: int,
    current_timestamp: int,
    is_defaulted: bool,
) -> str:
    """Derive a friendly status for one coupon obligation."""
    if required == 0:
        return "Chưa xác lập"

    if funded >= required:
        if is_defaulted:
            return "Đã funding nhưng default chưa được cure"

        return "Đã funding đầy đủ"

    if is_defaulted:
        return "Đang default"

    if due_timestamp == 0:
        return "Chưa lên lịch"

    if current_timestamp < due_timestamp:
        return "Chưa đến hạn"

    grace_deadline = (
        due_timestamp
        + grace_period_seconds
    )

    if current_timestamp < grace_deadline:
        return "Đã đến hạn – đang trong grace period"

    return "Quá grace period – có thể ghi nhận default"


def _derive_principal_status(
    *,
    required: Decimal,
    funded: Decimal,
    maturity_timestamp: int,
    grace_period_seconds: int,
    current_timestamp: int,
    is_defaulted: bool,
) -> str:
    """Derive a friendly status for the principal obligation."""
    if required == 0:
        return "Chưa xác lập"

    if funded >= required:
        if is_defaulted:
            return "Đã funding nhưng default chưa được cure"

        return "Đã funding đầy đủ"

    if is_defaulted:
        return "Đang default"

    if maturity_timestamp == 0:
        return "Chưa xác lập maturity"

    if current_timestamp < maturity_timestamp:
        return "Chưa đến maturity"

    grace_deadline = (
        maturity_timestamp
        + grace_period_seconds
    )

    if current_timestamp < grace_deadline:
        return "Đã maturity – đang trong grace period"

    return "Quá grace period – có thể ghi nhận default"


def _read_coupon_obligation(
    client: BlockchainClient,
    *,
    period: int,
    lifecycle_value: int,
    current_timestamp: int,
    grace_period_seconds: int,
    bond_usd_decimals: int,
) -> CouponObligation:
    """Read one coupon period from getCouponInfo()."""
    try:
        result = list(
            client.tokenized_bond.functions
            .getCouponInfo(period)
            .call()
        )

        if len(result) != 6:
            raise BlockchainError(
                "getCouponInfo() phải trả về 6 trường, "
                f"nhưng nhận được {len(result)} trường."
            )

        (
            due_timestamp,
            required_raw,
            funded_raw,
            claimed_raw,
            is_defaulted,
            defaulted_at,
        ) = result

        required = client.format_units(
            int(required_raw),
            bond_usd_decimals,
        )

        funded = client.format_units(
            int(funded_raw),
            bond_usd_decimals,
        )

        claimed = client.format_units(
            int(claimed_raw),
            bond_usd_decimals,
        )

        funding_gap = max(
            required - funded,
            Decimal("0"),
        )

        unclaimed_amount = max(
            funded - claimed,
            Decimal("0"),
        )

        can_deposit = (
            lifecycle_value in (3, 4)
            and required > 0
            and funded < required
        )

        status = _derive_coupon_status(
            required=required,
            funded=funded,
            due_timestamp=int(due_timestamp),
            grace_period_seconds=(
                grace_period_seconds
            ),
            current_timestamp=current_timestamp,
            is_defaulted=bool(is_defaulted),
        )

        return CouponObligation(
            period=period,
            due_timestamp=int(due_timestamp),
            required=required,
            funded=funded,
            claimed=claimed,
            funding_gap=funding_gap,
            unclaimed_amount=unclaimed_amount,
            is_defaulted=bool(is_defaulted),
            defaulted_at=int(defaulted_at),
            has_default_history=(
                int(defaulted_at) > 0
            ),
            can_deposit=can_deposit,
            status=status,
        )

    except BlockchainError:
        raise

    except (
        ValueError,
        TypeError,
        Web3Exception,
    ) as exc:
        raise BlockchainError(
            f"Không thể đọc Coupon {period}: {exc}"
        ) from exc


def _read_principal_obligation(
    client: BlockchainClient,
    *,
    lifecycle_value: int,
    current_timestamp: int,
    grace_period_seconds: int,
    bond_usd_decimals: int,
) -> PrincipalObligation:
    """Read principal data from getPrincipalInfo()."""
    try:
        result = list(
            client.tokenized_bond.functions
            .getPrincipalInfo()
            .call()
        )

        if len(result) != 6:
            raise BlockchainError(
                "getPrincipalInfo() phải trả về 6 trường, "
                f"nhưng nhận được {len(result)} trường."
            )

        (
            maturity_timestamp,
            required_raw,
            funded_raw,
            redeemed_raw,
            is_defaulted,
            defaulted_at,
        ) = result

        required = client.format_units(
            int(required_raw),
            bond_usd_decimals,
        )

        funded = client.format_units(
            int(funded_raw),
            bond_usd_decimals,
        )

        redeemed = client.format_units(
            int(redeemed_raw),
            bond_usd_decimals,
        )

        funding_gap = max(
            required - funded,
            Decimal("0"),
        )

        unredeemed_amount = max(
            funded - redeemed,
            Decimal("0"),
        )

        can_deposit = (
            lifecycle_value in (3, 4)
            and required > 0
            and funded < required
        )

        status = _derive_principal_status(
            required=required,
            funded=funded,
            maturity_timestamp=(
                int(maturity_timestamp)
            ),
            grace_period_seconds=(
                grace_period_seconds
            ),
            current_timestamp=current_timestamp,
            is_defaulted=bool(is_defaulted),
        )

        return PrincipalObligation(
            maturity_timestamp=(
                int(maturity_timestamp)
            ),
            required=required,
            funded=funded,
            redeemed=redeemed,
            funding_gap=funding_gap,
            unredeemed_amount=unredeemed_amount,
            is_defaulted=bool(is_defaulted),
            defaulted_at=int(defaulted_at),
            has_default_history=(
                int(defaulted_at) > 0
            ),
            can_deposit=can_deposit,
            status=status,
        )

    except BlockchainError:
        raise

    except (
        ValueError,
        TypeError,
        Web3Exception,
    ) as exc:
        raise BlockchainError(
            f"Không thể đọc principal obligation: {exc}"
        ) from exc


def get_issuer_dashboard(
    client: BlockchainClient,
) -> IssuerDashboard:
    """Build the complete read-only issuer dashboard."""
    try:
        issuer_address = Web3.to_checksum_address(
            ISSUER_ADDRESS
        )

        tokenized_bond_address = (
            Web3.to_checksum_address(
                TOKENIZED_BOND_ADDRESS
            )
        )

        system_state = client.get_system_state()

        bond_usd_decimals = int(
            client.bond_usd.functions
            .decimals()
            .call()
        )

        latest_block = client.web3.eth.get_block(
            "latest"
        )

        current_block_timestamp = int(
            latest_block["timestamp"]
        )

        grace_period_seconds = int(
            client.tokenized_bond.functions
            .GRACE_PERIOD()
            .call()
        )

        eth_balance = client.get_eth_balance(
            issuer_address
        )

        bond_usd_balance = (
            client.get_bond_usd_balance(
                issuer_address
            )
        )

        allowance_raw = int(
            client.bond_usd.functions
            .allowance(
                issuer_address,
                tokenized_bond_address,
            )
            .call()
        )

        bond_usd_allowance = (
            client.format_units(
                allowance_raw,
                bond_usd_decimals,
            )
        )

        subscription_open = bool(
            client.tokenized_bond.functions
            .isSubscriptionOpen()
            .call()
        )

        can_finalize = bool(
            client.tokenized_bond.functions
            .canFinalize()
            .call()
        )

        can_close = bool(
            client.tokenized_bond.functions
            .canClose()
            .call()
        )

        is_defaulted = bool(
            client.tokenized_bond.functions
            .isDefaulted()
            .call()
        )

        coupon_1 = _read_coupon_obligation(
            client,
            period=1,
            lifecycle_value=(
                system_state.lifecycle_value
            ),
            current_timestamp=(
                current_block_timestamp
            ),
            grace_period_seconds=(
                grace_period_seconds
            ),
            bond_usd_decimals=(
                bond_usd_decimals
            ),
        )

        coupon_2 = _read_coupon_obligation(
            client,
            period=2,
            lifecycle_value=(
                system_state.lifecycle_value
            ),
            current_timestamp=(
                current_block_timestamp
            ),
            grace_period_seconds=(
                grace_period_seconds
            ),
            bond_usd_decimals=(
                bond_usd_decimals
            ),
        )

        principal = _read_principal_obligation(
            client,
            lifecycle_value=(
                system_state.lifecycle_value
            ),
            current_timestamp=(
                current_block_timestamp
            ),
            grace_period_seconds=(
                grace_period_seconds
            ),
            bond_usd_decimals=(
                bond_usd_decimals
            ),
        )

        can_open_subscription = (
            system_state.lifecycle_value == 0
            and not system_state.subscription_paused
        )

        can_withdraw_proceeds = (
            system_state.lifecycle_value in (3, 4)
            and not system_state.proceeds_withdrawn
            and system_state.total_raised_display > 0
        )

        withdrawable_proceeds = (
            system_state.total_raised_display
            if can_withdraw_proceeds
            else Decimal("0")
        )

        total_funding_gap = (
            coupon_1.funding_gap
            + coupon_2.funding_gap
            + principal.funding_gap
        )

        total_unclaimed_obligations = (
            coupon_1.unclaimed_amount
            + coupon_2.unclaimed_amount
            + principal.unredeemed_amount
        )

        return IssuerDashboard(
            issuer_address=issuer_address,
            lifecycle_value=(
                system_state.lifecycle_value
            ),
            lifecycle_name=(
                system_state.lifecycle_name
            ),
            eth_balance=eth_balance,
            bond_usd_balance=bond_usd_balance,
            bond_usd_allowance=(
                bond_usd_allowance
            ),
            total_raised=(
                system_state.total_raised_display
            ),
            escrow_balance=(
                system_state.escrow_balance_display
            ),
            proceeds_withdrawn=(
                system_state.proceeds_withdrawn
            ),
            withdrawable_proceeds=(
                withdrawable_proceeds
            ),
            subscription_paused=(
                system_state.subscription_paused
            ),
            subscription_open=(
                subscription_open
            ),
            can_open_subscription=(
                can_open_subscription
            ),
            can_finalize=can_finalize,
            can_withdraw_proceeds=(
                can_withdraw_proceeds
            ),
            can_close=can_close,
            coupon_1=coupon_1,
            coupon_2=coupon_2,
            principal=principal,
            total_funding_gap=(
                total_funding_gap
            ),
            total_unclaimed_obligations=(
                total_unclaimed_obligations
            ),
            is_defaulted=is_defaulted,
            current_block_timestamp=(
                current_block_timestamp
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
            f"Không thể xây dựng Issuer Dashboard: {exc}"
        ) from exc