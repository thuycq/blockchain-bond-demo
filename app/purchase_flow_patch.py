from __future__ import annotations

from typing import Callable

from app import bond_runtime


_OLD_APPROVE_READY = '''    approve_ready = (
        info["is_whitelisted"]
        and subscription_open
        and remaining_supply > 0
        and quantity_within_supply
        and balance_raw >= payment_raw
        and allowance_raw < payment_raw
    )
'''

_NEW_APPROVE_READY = '''    # ERC-20 approve does not require the wallet to already hold
    # the approved amount. Balance is checked only when subscribe() runs.
    approve_ready = (
        info["is_whitelisted"]
        and subscription_open
        and remaining_supply > 0
        and quantity_within_supply
        and allowance_raw < payment_raw
    )
'''

_OLD_GUIDANCE = '''    elif balance_raw < payment_raw:
        st.caption(
            "The wallet does not have enough BondUSD."
        )
    elif allowance_raw < payment_raw:
        st.caption(
            "Approve the exact BondUSD amount before subscribing."
        )
'''

_NEW_GUIDANCE = '''    elif allowance_raw < payment_raw:
        st.caption(
            "Approve the exact BondUSD amount before subscribing."
        )
    elif balance_raw < payment_raw:
        st.caption(
            "Approval is complete, but the wallet needs enough BondUSD before subscribing."
        )
'''

# Luôn lưu hàm gốc một lần duy nhất trên module bond_runtime.
# Điều này ngăn wrapper bị bọc lặp sau các lần Streamlit rerun.
if not hasattr(
    bond_runtime,
    "_purchase_flow_original_prepare",
):
    bond_runtime._purchase_flow_original_prepare = (
        bond_runtime._prepare_app_source
    )

_BASE_PREPARE: Callable[[str, str], str] = (
    bond_runtime._purchase_flow_original_prepare
)


def _prepare_patched_source(
    bond_key: str,
    bond_name: str,
) -> str:
    source = _BASE_PREPARE(
        bond_key,
        bond_name,
    )

    if _OLD_APPROVE_READY in source:
        source = source.replace(
            _OLD_APPROVE_READY,
            _NEW_APPROVE_READY,
            1,
        )
    elif _NEW_APPROVE_READY not in source:
        raise RuntimeError(
            "Không tìm thấy khối approve_ready trong bond app template."
        )

    if _OLD_GUIDANCE in source:
        source = source.replace(
            _OLD_GUIDANCE,
            _NEW_GUIDANCE,
            1,
        )
    elif _NEW_GUIDANCE not in source:
        raise RuntimeError(
            "Không tìm thấy khối hướng dẫn approve trong bond app template."
        )

    return source


def run_bond_app(bond_key: str) -> None:
    """Run one bond page with corrected investor approval logic."""
    bond_runtime._prepare_app_source = (
        _prepare_patched_source
    )

    try:
        bond_runtime.run_bond_app(
            bond_key
        )
    finally:
        bond_runtime._prepare_app_source = (
            _BASE_PREPARE
        )
