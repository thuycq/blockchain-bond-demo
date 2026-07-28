from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from web3 import Web3

from app.blockchain import (
    ContractCodeStatus,
    SystemState,
)
from app.config import (
    ADMIN_ADDRESS,
    BOND_TOKEN_ADDRESS,
    BOND_USD_ADDRESS,
    EXPECTED_CHAIN_ID,
    ISSUER_ADDRESS,
    TOKENIZED_BOND_ADDRESS,
)
from app.investor import InvestorPosition
from app.issuer import IssuerDashboard
from app.overview import BondOverview


@dataclass(frozen=True)
class AuditCheck:
    """One compliance or technical audit check."""

    category: str
    check_name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ComplianceReport:
    """Complete read-only compliance report."""

    checks: tuple[AuditCheck, ...]

    pass_count: int
    warning_count: int
    fail_count: int
    info_count: int

    overall_status: str


def _make_check(
    *,
    category: str,
    check_name: str,
    condition: bool,
    success_detail: str,
    failure_detail: str,
    failure_status: str = "FAIL",
) -> AuditCheck:
    """Create a PASS or failure audit item."""
    if condition:
        return AuditCheck(
            category=category,
            check_name=check_name,
            status="PASS",
            detail=success_detail,
        )

    return AuditCheck(
        category=category,
        check_name=check_name,
        status=failure_status,
        detail=failure_detail,
    )


def _make_info(
    *,
    category: str,
    check_name: str,
    detail: str,
) -> AuditCheck:
    """Create an informational audit item."""
    return AuditCheck(
        category=category,
        check_name=check_name,
        status="INFO",
        detail=detail,
    )


def build_compliance_report(
    *,
    chain_id: int,
    contract_statuses: list[ContractCodeStatus],
    system_state: SystemState,
    overview: BondOverview,
    issuer_dashboard: IssuerDashboard,
    investor_positions: dict[str, InvestorPosition],
) -> ComplianceReport:
    """
    Build a compliance report from data already loaded.

    This function creates no RPC calls and no transactions.
    """
    checks: list[AuditCheck] = []

    expected_admin = Web3.to_checksum_address(
        ADMIN_ADDRESS
    )

    expected_issuer = Web3.to_checksum_address(
        ISSUER_ADDRESS
    )

    expected_payment_token = Web3.to_checksum_address(
        BOND_USD_ADDRESS
    )

    expected_bond_token = Web3.to_checksum_address(
        BOND_TOKEN_ADDRESS
    )

    expected_controller = Web3.to_checksum_address(
        TOKENIZED_BOND_ADDRESS
    )

    zero_address = Web3.to_checksum_address(
        "0x0000000000000000000000000000000000000000"
    )

    # ========================================================
    # Network and deployment
    # ========================================================

    checks.append(
        _make_check(
            category="Network",
            check_name="Sepolia chain ID",
            condition=(
                chain_id
                == EXPECTED_CHAIN_ID
            ),
            success_detail=(
                f"Chain ID đúng: {chain_id}."
            ),
            failure_detail=(
                f"Chain ID không đúng: {chain_id}."
            ),
        )
    )

    for contract_status in contract_statuses:
        checks.append(
            _make_check(
                category="Deployment",
                check_name=(
                    f"{contract_status.contract_name} bytecode"
                ),
                condition=contract_status.has_code,
                success_detail=(
                    f"Bytecode tồn tại tại "
                    f"{contract_status.address}."
                ),
                failure_detail=(
                    f"Không tìm thấy bytecode tại "
                    f"{contract_status.address}."
                ),
            )
        )

    # ========================================================
    # Roles and references
    # ========================================================

    checks.append(
        _make_check(
            category="Roles",
            check_name="Admin address",
            condition=(
                system_state.admin
                == expected_admin
            ),
            success_detail=(
                "Admin address khớp deployment."
            ),
            failure_detail=(
                "Admin address không khớp deployment."
            ),
        )
    )

    checks.append(
        _make_check(
            category="Roles",
            check_name="Issuer address",
            condition=(
                system_state.issuer
                == expected_issuer
            ),
            success_detail=(
                "Issuer address khớp deployment."
            ),
            failure_detail=(
                "Issuer address không khớp deployment."
            ),
        )
    )

    checks.append(
        _make_check(
            category="References",
            check_name="Payment token reference",
            condition=(
                system_state.payment_token
                == expected_payment_token
            ),
            success_detail=(
                "TokenizedBond đang sử dụng BondUSD chính thức."
            ),
            failure_detail=(
                "Payment token reference không đúng."
            ),
        )
    )

    checks.append(
        _make_check(
            category="References",
            check_name="BondToken reference",
            condition=(
                system_state.bond_token
                == expected_bond_token
            ),
            success_detail=(
                "TokenizedBond tham chiếu đúng BondToken."
            ),
            failure_detail=(
                "BondToken reference không đúng."
            ),
        )
    )

    checks.append(
        _make_check(
            category="Control",
            check_name="BondToken controller",
            condition=(
                system_state.bond_token_controller
                == expected_controller
            ),
            success_detail=(
                "TokenizedBond là controller cố định."
            ),
            failure_detail=(
                "BondToken controller không đúng."
            ),
        )
    )

    checks.append(
        _make_check(
            category="Control",
            check_name="BondToken ownership",
            condition=(
                system_state.bond_token_owner
                == zero_address
            ),
            success_detail=(
                "BondToken ownership đã được renounce."
            ),
            failure_detail=(
                "BondToken vẫn còn owner."
            ),
        )
    )

    # ========================================================
    # Supply and financial consistency
    # ========================================================

    checks.append(
        _make_check(
            category="Supply",
            check_name="Maximum supply",
            condition=(
                system_state.total_subscribed
                <= overview.max_supply
            ),
            success_detail=(
                "Total subscribed không vượt maximum supply."
            ),
            failure_detail=(
                "Total subscribed vượt maximum supply."
            ),
        )
    )

    checks.append(
        _make_check(
            category="Supply",
            check_name="BondToken supply consistency",
            condition=(
                system_state.bond_token_supply
                <= system_state.total_subscribed
            ),
            success_detail=(
                "BondToken supply không vượt số lượng "
                "đã đăng ký mua."
            ),
            failure_detail=(
                "BondToken supply vượt total subscribed."
            ),
        )
    )

    expected_total_raised = (
        Decimal(
            system_state.total_subscribed
        )
        * overview.issue_price
    )

    checks.append(
        _make_check(
            category="Financial",
            check_name="Total raised reconciliation",
            condition=(
                system_state.total_raised_display
                == expected_total_raised
            ),
            success_detail=(
                "Total raised = subscribed quantity × issue price."
            ),
            failure_detail=(
                "Total raised không khớp quantity × issue price."
            ),
        )
    )

    # ========================================================
    # Lifecycle-specific checks
    # ========================================================

    valid_lifecycle_values = {
        0,
        1,
        2,
        3,
        4,
        5,
    }

    checks.append(
        _make_check(
            category="Lifecycle",
            check_name="Known lifecycle",
            condition=(
                system_state.lifecycle_value
                in valid_lifecycle_values
            ),
            success_detail=(
                f"Lifecycle hợp lệ: "
                f"{system_state.lifecycle_name}."
            ),
            failure_detail=(
                "Lifecycle value không được nhận diện."
            ),
        )
    )

    if system_state.lifecycle_value == 0:
        draft_is_clean = all(
            [
                system_state.subscription_start == 0,
                system_state.total_subscribed == 0,
                system_state.total_raised_raw == 0,
                system_state.bond_token_supply == 0,
                system_state.escrow_balance_raw == 0,
            ]
        )

        checks.append(
            _make_check(
                category="Lifecycle",
                check_name="Clean Draft state",
                condition=draft_is_clean,
                success_detail=(
                    "Draft chưa mở subscription, chưa mint "
                    "BondToken và escrow bằng 0."
                ),
                failure_detail=(
                    "Draft state đã phát sinh dữ liệu giao dịch."
                ),
            )
        )

    elif system_state.lifecycle_value == 1:
        subscription_reconciliation = (
            system_state.bond_token_supply
            == system_state.total_subscribed
        )

        checks.append(
            _make_check(
                category="Lifecycle",
                check_name="Subscription supply reconciliation",
                condition=subscription_reconciliation,
                success_detail=(
                    "Trong SubscriptionOpen, BondToken supply "
                    "khớp total subscribed."
                ),
                failure_detail=(
                    "BondToken supply không khớp total subscribed."
                ),
            )
        )

        checks.append(
            _make_check(
                category="Financial",
                check_name="Subscription escrow reconciliation",
                condition=(
                    system_state.escrow_balance_display
                    == system_state.total_raised_display
                ),
                success_detail=(
                    "Escrow khớp total raised trước finalize."
                ),
                failure_detail=(
                    "Escrow không khớp total raised."
                ),
            )
        )

    elif system_state.lifecycle_value == 2:
        checks.append(
            _make_check(
                category="Financial",
                check_name="Failed-offering refund reconciliation",
                condition=(
                    system_state.escrow_balance_display
                    + overview.total_refunded
                    == system_state.total_raised_display
                ),
                success_detail=(
                    "Escrow còn lại + total refunded "
                    "= total raised."
                ),
                failure_detail=(
                    "Refund reconciliation không khớp."
                ),
            )
        )

    else:
        checks.append(
            _make_info(
                category="Financial",
                check_name="Active escrow interpretation",
                detail=(
                    "Sau finalize, escrow có thể gồm coupon "
                    "hoặc principal funding nên không được "
                    "đối chiếu trực tiếp với total raised."
                ),
            )
        )

    # ========================================================
    # Whitelist
    # ========================================================

    for label, position in investor_positions.items():
        checks.append(
            _make_check(
                category="Whitelist",
                check_name=f"{label} whitelist",
                condition=position.is_whitelisted,
                success_detail=(
                    f"{label} đang được whitelist."
                ),
                failure_detail=(
                    f"{label} chưa được whitelist."
                ),
                failure_status="WARN",
            )
        )

    # ========================================================
    # Payment obligations and default
    # ========================================================

    obligation_default = any(
        [
            issuer_dashboard.coupon_1.is_defaulted,
            issuer_dashboard.coupon_2.is_defaulted,
            issuer_dashboard.principal.is_defaulted,
        ]
    )

    checks.append(
        _make_check(
            category="Default",
            check_name="Default aggregation",
            condition=(
                issuer_dashboard.is_defaulted
                == obligation_default
            ),
            success_detail=(
                "Default tổng hợp khớp trạng thái "
                "của từng nghĩa vụ."
            ),
            failure_detail=(
                "Default tổng hợp không khớp nghĩa vụ chi tiết."
            ),
        )
    )

    if system_state.lifecycle_value == 0:
        draft_obligations_zero = all(
            [
                issuer_dashboard.coupon_1.required
                == Decimal("0"),
                issuer_dashboard.coupon_2.required
                == Decimal("0"),
                issuer_dashboard.principal.required
                == Decimal("0"),
            ]
        )

        checks.append(
            _make_check(
                category="Payments",
                check_name="Draft payment obligations",
                condition=draft_obligations_zero,
                success_detail=(
                    "Draft chưa xác lập coupon và principal."
                ),
                failure_detail=(
                    "Draft đã phát sinh nghĩa vụ thanh toán."
                ),
            )
        )

    # ========================================================
    # Design information
    # ========================================================

    checks.append(
        _make_info(
            category="Design",
            check_name="BondToken transfer restriction",
            detail=(
                "BondToken được thiết kế non-transferable. "
                "Đặc tính này đã được kiểm thử trong BOND 4; "
                "dashboard read-only không gửi giao dịch thử."
            ),
        )
    )

    checks.append(
        _make_info(
            category="Security",
            check_name="Private-key handling",
            detail=(
                "Streamlit local chỉ sử dụng RPC và dữ liệu công khai. "
                "Không tải hoặc lưu private key người dùng."
            ),
        )
    )

    # ========================================================
    # Summary
    # ========================================================

    pass_count = sum(
        1
        for check in checks
        if check.status == "PASS"
    )

    warning_count = sum(
        1
        for check in checks
        if check.status == "WARN"
    )

    fail_count = sum(
        1
        for check in checks
        if check.status == "FAIL"
    )

    info_count = sum(
        1
        for check in checks
        if check.status == "INFO"
    )

    if fail_count > 0:
        overall_status = "FAILED"
    elif warning_count > 0:
        overall_status = "PASSED WITH WARNINGS"
    else:
        overall_status = "PASSED"

    return ComplianceReport(
        checks=tuple(checks),
        pass_count=pass_count,
        warning_count=warning_count,
        fail_count=fail_count,
        info_count=info_count,
        overall_status=overall_status,
    )