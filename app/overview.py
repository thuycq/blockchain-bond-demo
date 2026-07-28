from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from web3.contract import Contract
from web3.exceptions import Web3Exception

from app.blockchain import (
    BlockchainClient,
    BlockchainError,
)


@dataclass(frozen=True)
class BondOverview:
    bond_name: str
    bond_symbol: str

    face_value: Decimal
    issue_price: Decimal

    max_supply: int
    minimum_subscription: int

    maximum_issue_value: Decimal
    minimum_issue_value: Decimal

    annual_coupon_rate_bps: int
    annual_coupon_rate_percent: Decimal

    coupon_per_period: Decimal
    coupon_period_count: int
    total_coupon_per_bond: Decimal

    subscription_duration_seconds: int
    coupon_1_delay_seconds: int
    coupon_2_delay_seconds: int
    grace_period_seconds: int

    lifecycle_value: int
    lifecycle_name: str

    subscription_open: bool
    subscription_paused: bool

    subscription_start: int
    subscription_deadline: int
    finalized_at: int

    coupon_1_due: int
    coupon_2_due: int
    maturity: int

    total_subscribed: int
    remaining_supply: int

    total_raised: Decimal
    total_refunded: Decimal

    maximum_progress_percent: Decimal
    minimum_progress_percent: Decimal

    is_defaulted: bool
    can_finalize: bool
    can_close: bool

    offering_status: str


def _find_function_abi(
    contract: Contract,
    function_name: str,
) -> dict[str, Any]:
    """Find a function definition inside the contract ABI."""
    for entry in contract.abi:
        if (
            entry.get("type") == "function"
            and entry.get("name") == function_name
        ):
            return entry

    raise BlockchainError(
        f"Không tìm thấy hàm {function_name} trong TokenizedBond ABI."
    )


def _read_named_output(
    contract: Contract,
    function_name: str,
) -> dict[str, Any]:
    """
    Read a view function and map tuple outputs to their ABI field names.

    This supports Solidity functions such as getBondInfo().
    """
    try:
        function_abi = _find_function_abi(
            contract,
            function_name,
        )

        result = getattr(
            contract.functions,
            function_name,
        )().call()

        outputs = function_abi.get("outputs", [])

        if (
            len(outputs) == 1
            and str(outputs[0].get("type", "")).startswith("tuple")
        ):
            components = outputs[0].get("components", [])
            values = list(result)

            return {
                (
                    component.get("name")
                    or f"field_{index}"
                ): values[index]
                for index, component in enumerate(components)
            }

        if len(outputs) > 1:
            values = list(result)

            return {
                (
                    output.get("name")
                    or f"field_{index}"
                ): values[index]
                for index, output in enumerate(outputs)
            }

        if len(outputs) == 1:
            output_name = outputs[0].get("name") or "value"
            return {output_name: result}

        return {}

    except (ValueError, Web3Exception, TypeError) as exc:
        raise BlockchainError(
            f"Không thể đọc {function_name}: {exc}"
        ) from exc


def _call_uint(
    contract: Contract,
    function_name: str,
) -> int:
    """Call a public uint constant or uint view function."""
    try:
        return int(
            getattr(
                contract.functions,
                function_name,
            )().call()
        )
    except (ValueError, Web3Exception, TypeError) as exc:
        raise BlockchainError(
            f"Không thể đọc {function_name}: {exc}"
        ) from exc


def _call_bool(
    contract: Contract,
    function_name: str,
) -> bool:
    """Call a public boolean view function."""
    try:
        return bool(
            getattr(
                contract.functions,
                function_name,
            )().call()
        )
    except (ValueError, Web3Exception, TypeError) as exc:
        raise BlockchainError(
            f"Không thể đọc {function_name}: {exc}"
        ) from exc


def _pick(
    data: dict[str, Any],
    *candidate_names: str,
    default: Any = None,
) -> Any:
    """Return the first matching field name from a dictionary."""
    for name in candidate_names:
        if name in data:
            return data[name]

    return default


def _derive_offering_status(
    lifecycle_value: int,
    subscription_open: bool,
    subscription_paused: bool,
    is_defaulted: bool,
) -> str:
    """Create a concise user-facing status label."""
    if lifecycle_value == 0:
        return "Chưa mở đăng ký"

    if lifecycle_value == 1:
        if subscription_paused:
            return "Đăng ký đang tạm dừng"

        if subscription_open:
            return "Đang mở đăng ký"

        return "Đã hết thời gian đăng ký, chờ finalize"

    if lifecycle_value == 2:
        return "Phát hành không thành công"

    if lifecycle_value == 3:
        if is_defaulted:
            return "Đang lưu hành – có nghĩa vụ bị default"

        return "Đang lưu hành"

    if lifecycle_value == 4:
        if is_defaulted:
            return "Đã đáo hạn – có nghĩa vụ bị default"

        return "Đã đáo hạn"

    if lifecycle_value == 5:
        return "Đã hoàn tất và đóng contract"

    return "Không xác định"


def get_bond_overview(
    client: BlockchainClient,
) -> BondOverview:
    """Read the full Bond Overview from Ethereum Sepolia."""
    contract = client.tokenized_bond
    system_state = client.get_system_state()

    try:
        bond_info = _read_named_output(
            contract,
            "getBondInfo",
        )

        bond_usd_decimals = int(
            client.bond_usd.functions.decimals().call()
        )

        bond_symbol = str(
            client.bond_token.functions.symbol().call()
        )

        bond_name = str(
            _pick(
                bond_info,
                "bondName",
                default="Demo Corporate Bond 2026",
            )
        )

        face_value_raw = int(
            _pick(
                bond_info,
                "faceValue",
                default=_call_uint(
                    contract,
                    "FACE_VALUE",
                ),
            )
        )

        issue_price_raw = int(
            _pick(
                bond_info,
                "issuePrice",
                default=_call_uint(
                    contract,
                    "ISSUE_PRICE",
                ),
            )
        )

        max_supply = int(
            _pick(
                bond_info,
                "maxSupply",
                default=_call_uint(
                    contract,
                    "MAX_BOND_SUPPLY",
                ),
            )
        )

        minimum_subscription = int(
            _pick(
                bond_info,
                "minimumSubscription",
                default=_call_uint(
                    contract,
                    "MINIMUM_SUBSCRIPTION",
                ),
            )
        )

        annual_coupon_rate_bps = _call_uint(
            contract,
            "ANNUAL_COUPON_RATE_BPS",
        )

        coupon_per_period_raw = int(
            _pick(
                bond_info,
                "couponPerPeriod",
                default=_call_uint(
                    contract,
                    "COUPON_PER_PERIOD",
                ),
            )
        )

        coupon_period_count = _call_uint(
            contract,
            "COUPON_PERIOD_COUNT",
        )

        subscription_duration_seconds = _call_uint(
            contract,
            "SUBSCRIPTION_DURATION",
        )

        coupon_1_delay_seconds = _call_uint(
            contract,
            "COUPON_1_DELAY",
        )

        coupon_2_delay_seconds = _call_uint(
            contract,
            "COUPON_2_DELAY",
        )

        grace_period_seconds = _call_uint(
            contract,
            "GRACE_PERIOD",
        )

        finalized_at = _call_uint(
            contract,
            "finalizedAt",
        )

        maturity = _call_uint(
            contract,
            "maturity",
        )

        coupon_1_due = int(
            contract.functions.couponDue(1).call()
        )

        coupon_2_due = int(
            contract.functions.couponDue(2).call()
        )

        total_refunded_raw = _call_uint(
            contract,
            "totalRefunded",
        )

        subscription_open = _call_bool(
            contract,
            "isSubscriptionOpen",
        )

        is_defaulted = _call_bool(
            contract,
            "isDefaulted",
        )

        can_finalize = _call_bool(
            contract,
            "canFinalize",
        )

        can_close = _call_bool(
            contract,
            "canClose",
        )

        face_value = client.format_units(
            face_value_raw,
            bond_usd_decimals,
        )

        issue_price = client.format_units(
            issue_price_raw,
            bond_usd_decimals,
        )

        coupon_per_period = client.format_units(
            coupon_per_period_raw,
            bond_usd_decimals,
        )

        total_refunded = client.format_units(
            total_refunded_raw,
            bond_usd_decimals,
        )

        remaining_supply = max(
            max_supply - system_state.total_subscribed,
            0,
        )

        maximum_progress_percent = (
            Decimal(system_state.total_subscribed)
            * Decimal(100)
            / Decimal(max_supply)
            if max_supply > 0
            else Decimal(0)
        )

        minimum_progress_percent = (
            Decimal(system_state.total_subscribed)
            * Decimal(100)
            / Decimal(minimum_subscription)
            if minimum_subscription > 0
            else Decimal(0)
        )

        annual_coupon_rate_percent = (
            Decimal(annual_coupon_rate_bps)
            / Decimal(100)
        )

        maximum_issue_value = (
            Decimal(max_supply) * issue_price
        )

        minimum_issue_value = (
            Decimal(minimum_subscription) * issue_price
        )

        total_coupon_per_bond = (
            coupon_per_period
            * Decimal(coupon_period_count)
        )

        offering_status = _derive_offering_status(
            lifecycle_value=system_state.lifecycle_value,
            subscription_open=subscription_open,
            subscription_paused=system_state.subscription_paused,
            is_defaulted=is_defaulted,
        )

        return BondOverview(
            bond_name=bond_name,
            bond_symbol=bond_symbol,
            face_value=face_value,
            issue_price=issue_price,
            max_supply=max_supply,
            minimum_subscription=minimum_subscription,
            maximum_issue_value=maximum_issue_value,
            minimum_issue_value=minimum_issue_value,
            annual_coupon_rate_bps=annual_coupon_rate_bps,
            annual_coupon_rate_percent=annual_coupon_rate_percent,
            coupon_per_period=coupon_per_period,
            coupon_period_count=coupon_period_count,
            total_coupon_per_bond=total_coupon_per_bond,
            subscription_duration_seconds=(
                subscription_duration_seconds
            ),
            coupon_1_delay_seconds=coupon_1_delay_seconds,
            coupon_2_delay_seconds=coupon_2_delay_seconds,
            grace_period_seconds=grace_period_seconds,
            lifecycle_value=system_state.lifecycle_value,
            lifecycle_name=system_state.lifecycle_name,
            subscription_open=subscription_open,
            subscription_paused=(
                system_state.subscription_paused
            ),
            subscription_start=(
                system_state.subscription_start
            ),
            subscription_deadline=(
                system_state.subscription_deadline
            ),
            finalized_at=finalized_at,
            coupon_1_due=coupon_1_due,
            coupon_2_due=coupon_2_due,
            maturity=maturity,
            total_subscribed=(
                system_state.total_subscribed
            ),
            remaining_supply=remaining_supply,
            total_raised=system_state.total_raised_display,
            total_refunded=total_refunded,
            maximum_progress_percent=(
                maximum_progress_percent
            ),
            minimum_progress_percent=(
                minimum_progress_percent
            ),
            is_defaulted=is_defaulted,
            can_finalize=can_finalize,
            can_close=can_close,
            offering_status=offering_status,
        )

    except (ValueError, Web3Exception, TypeError) as exc:
        raise BlockchainError(
            f"Không thể xây dựng Bond Overview: {exc}"
        ) from exc