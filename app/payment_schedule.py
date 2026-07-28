from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.issuer import IssuerDashboard
from app.overview import BondOverview


@dataclass(frozen=True)
class PaymentScheduleItem:
    """One coupon or principal payment obligation."""

    sequence: int
    obligation: str
    obligation_type: str

    due_timestamp: int
    grace_deadline: int

    required: Decimal
    funded: Decimal
    distributed: Decimal

    funding_gap: Decimal
    undistributed_funds: Decimal
    remaining_contractual_payment: Decimal

    is_defaulted: bool
    defaulted_at: int

    status: str


@dataclass(frozen=True)
class PaymentSchedule:
    """Complete payment schedule for the tokenized bond."""

    lifecycle_name: str
    current_block_timestamp: int

    items: tuple[PaymentScheduleItem, ...]

    total_required: Decimal
    total_funded: Decimal
    total_distributed: Decimal

    total_funding_gap: Decimal
    total_undistributed_funds: Decimal
    total_remaining_contractual_payment: Decimal

    next_obligation: str
    next_due_timestamp: int

    has_active_default: bool


def _calculate_grace_deadline(
    due_timestamp: int,
    grace_period_seconds: int,
) -> int:
    """Calculate the end of the grace period."""
    if due_timestamp == 0:
        return 0

    return (
        due_timestamp
        + grace_period_seconds
    )


def _build_schedule_item(
    *,
    sequence: int,
    obligation: str,
    obligation_type: str,
    due_timestamp: int,
    grace_period_seconds: int,
    required: Decimal,
    funded: Decimal,
    distributed: Decimal,
    is_defaulted: bool,
    defaulted_at: int,
    status: str,
) -> PaymentScheduleItem:
    """Build and calculate one schedule item."""
    funding_gap = max(
        required - funded,
        Decimal("0"),
    )

    undistributed_funds = max(
        funded - distributed,
        Decimal("0"),
    )

    remaining_contractual_payment = max(
        required - distributed,
        Decimal("0"),
    )

    grace_deadline = (
        _calculate_grace_deadline(
            due_timestamp,
            grace_period_seconds,
        )
    )

    return PaymentScheduleItem(
        sequence=sequence,
        obligation=obligation,
        obligation_type=obligation_type,
        due_timestamp=due_timestamp,
        grace_deadline=grace_deadline,
        required=required,
        funded=funded,
        distributed=distributed,
        funding_gap=funding_gap,
        undistributed_funds=(
            undistributed_funds
        ),
        remaining_contractual_payment=(
            remaining_contractual_payment
        ),
        is_defaulted=is_defaulted,
        defaulted_at=defaulted_at,
        status=status,
    )


def _find_next_obligation(
    items: tuple[PaymentScheduleItem, ...],
    current_block_timestamp: int,
) -> tuple[str, int]:
    """Find the next unpaid scheduled obligation."""
    scheduled_items = [
        item
        for item in items
        if (
            item.due_timestamp > 0
            and item.distributed < item.required
        )
    ]

    if not scheduled_items:
        return (
            "Chưa xác lập",
            0,
        )

    future_items = [
        item
        for item in scheduled_items
        if (
            item.due_timestamp
            >= current_block_timestamp
        )
    ]

    candidates = (
        future_items
        if future_items
        else scheduled_items
    )

    next_item = min(
        candidates,
        key=lambda item: item.due_timestamp,
    )

    return (
        next_item.obligation,
        next_item.due_timestamp,
    )


def build_payment_schedule(
    overview: BondOverview,
    issuer_dashboard: IssuerDashboard,
) -> PaymentSchedule:
    """
    Build the payment schedule from data already loaded.

    This function performs no RPC calls and creates no transactions.
    """
    coupon_1 = _build_schedule_item(
        sequence=1,
        obligation="Coupon 1",
        obligation_type="Coupon",
        due_timestamp=(
            issuer_dashboard
            .coupon_1
            .due_timestamp
        ),
        grace_period_seconds=(
            overview.grace_period_seconds
        ),
        required=(
            issuer_dashboard
            .coupon_1
            .required
        ),
        funded=(
            issuer_dashboard
            .coupon_1
            .funded
        ),
        distributed=(
            issuer_dashboard
            .coupon_1
            .claimed
        ),
        is_defaulted=(
            issuer_dashboard
            .coupon_1
            .is_defaulted
        ),
        defaulted_at=(
            issuer_dashboard
            .coupon_1
            .defaulted_at
        ),
        status=(
            issuer_dashboard
            .coupon_1
            .status
        ),
    )

    coupon_2 = _build_schedule_item(
        sequence=2,
        obligation="Coupon 2",
        obligation_type="Coupon",
        due_timestamp=(
            issuer_dashboard
            .coupon_2
            .due_timestamp
        ),
        grace_period_seconds=(
            overview.grace_period_seconds
        ),
        required=(
            issuer_dashboard
            .coupon_2
            .required
        ),
        funded=(
            issuer_dashboard
            .coupon_2
            .funded
        ),
        distributed=(
            issuer_dashboard
            .coupon_2
            .claimed
        ),
        is_defaulted=(
            issuer_dashboard
            .coupon_2
            .is_defaulted
        ),
        defaulted_at=(
            issuer_dashboard
            .coupon_2
            .defaulted_at
        ),
        status=(
            issuer_dashboard
            .coupon_2
            .status
        ),
    )

    principal = _build_schedule_item(
        sequence=3,
        obligation="Principal",
        obligation_type="Principal",
        due_timestamp=(
            issuer_dashboard
            .principal
            .maturity_timestamp
        ),
        grace_period_seconds=(
            overview.grace_period_seconds
        ),
        required=(
            issuer_dashboard
            .principal
            .required
        ),
        funded=(
            issuer_dashboard
            .principal
            .funded
        ),
        distributed=(
            issuer_dashboard
            .principal
            .redeemed
        ),
        is_defaulted=(
            issuer_dashboard
            .principal
            .is_defaulted
        ),
        defaulted_at=(
            issuer_dashboard
            .principal
            .defaulted_at
        ),
        status=(
            issuer_dashboard
            .principal
            .status
        ),
    )

    items = (
        coupon_1,
        coupon_2,
        principal,
    )

    total_required = sum(
        (
            item.required
            for item in items
        ),
        Decimal("0"),
    )

    total_funded = sum(
        (
            item.funded
            for item in items
        ),
        Decimal("0"),
    )

    total_distributed = sum(
        (
            item.distributed
            for item in items
        ),
        Decimal("0"),
    )

    total_funding_gap = sum(
        (
            item.funding_gap
            for item in items
        ),
        Decimal("0"),
    )

    total_undistributed_funds = sum(
        (
            item.undistributed_funds
            for item in items
        ),
        Decimal("0"),
    )

    total_remaining_contractual_payment = sum(
        (
            item.remaining_contractual_payment
            for item in items
        ),
        Decimal("0"),
    )

    next_obligation, next_due_timestamp = (
        _find_next_obligation(
            items,
            issuer_dashboard
            .current_block_timestamp,
        )
    )

    has_active_default = any(
        item.is_defaulted
        for item in items
    )

    return PaymentSchedule(
        lifecycle_name=(
            issuer_dashboard.lifecycle_name
        ),
        current_block_timestamp=(
            issuer_dashboard
            .current_block_timestamp
        ),
        items=items,
        total_required=total_required,
        total_funded=total_funded,
        total_distributed=total_distributed,
        total_funding_gap=(
            total_funding_gap
        ),
        total_undistributed_funds=(
            total_undistributed_funds
        ),
        total_remaining_contractual_payment=(
            total_remaining_contractual_payment
        ),
        next_obligation=next_obligation,
        next_due_timestamp=(
            next_due_timestamp
        ),
        has_active_default=(
            has_active_default
        ),
    )