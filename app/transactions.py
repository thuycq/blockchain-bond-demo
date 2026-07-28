from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from web3 import Web3
from web3.exceptions import (
    ContractLogicError,
    TimeExhausted,
    Web3Exception,
)

from app.blockchain import (
    BlockchainClient,
    BlockchainError,
)
from app.config import (
    BOND_USD_ADDRESS,
    TOKENIZED_BOND_ADDRESS,
    etherscan_transaction_url,
)


class TransactionPreparationError(
    BlockchainError
):
    """Raised when a MetaMask transaction cannot be prepared."""


@dataclass(frozen=True)
class ActionDefinition:
    """Static metadata for one supported transaction action."""

    contract_name: str
    function_name: str
    event_name: str
    label: str


ACTION_DEFINITIONS: dict[
    str,
    ActionDefinition,
] = {
    "mintBondUSD": ActionDefinition(
        "bond_usd",
        "mint",
        "Transfer",
        "Mint BondUSD",
    ),
    "approveBondUSD": ActionDefinition(
        "bond_usd",
        "approve",
        "Approval",
        "Approve BondUSD",
    ),
    "requestWhitelist": ActionDefinition(
        "tokenized_bond",
        "requestWhitelist",
        "WhitelistRequested",
        "Request Whitelist",
    ),
    "approveWhitelist": ActionDefinition(
        "tokenized_bond",
        "approveWhitelist",
        "WhitelistApproved",
        "Approve Whitelist",
    ),
    "rejectWhitelist": ActionDefinition(
        "tokenized_bond",
        "rejectWhitelist",
        "WhitelistRejected",
        "Reject Whitelist",
    ),
    "revokeWhitelist": ActionDefinition(
        "tokenized_bond",
        "revokeWhitelist",
        "WhitelistRevoked",
        "Revoke Whitelist",
    ),
    "pauseSubscription": ActionDefinition(
        "tokenized_bond",
        "pauseSubscription",
        "SubscriptionPaused",
        "Pause Subscription",
    ),
    "unpauseSubscription": ActionDefinition(
        "tokenized_bond",
        "unpauseSubscription",
        "SubscriptionUnpaused",
        "Unpause Subscription",
    ),
    "openSubscription": ActionDefinition(
        "tokenized_bond",
        "openSubscription",
        "SubscriptionOpened",
        "Open Subscription",
    ),
    "subscribe": ActionDefinition(
        "tokenized_bond",
        "subscribe",
        "BondSubscribed",
        "Subscribe Bond",
    ),
    "finalizeOffering": ActionDefinition(
        "tokenized_bond",
        "finalizeOffering",
        "OfferingFinalized",
        "Finalize Offering",
    ),
    "withdrawProceeds": ActionDefinition(
        "tokenized_bond",
        "withdrawProceeds",
        "ProceedsWithdrawn",
        "Withdraw Proceeds",
    ),
    "claimRefund": ActionDefinition(
        "tokenized_bond",
        "claimRefund",
        "RefundClaimed",
        "Claim Refund",
    ),
    "depositCoupon": ActionDefinition(
        "tokenized_bond",
        "depositCoupon",
        "CouponFunded",
        "Deposit Coupon",
    ),
    "claimCoupon": ActionDefinition(
        "tokenized_bond",
        "claimCoupon",
        "CouponClaimed",
        "Claim Coupon",
    ),
    "depositPrincipal": ActionDefinition(
        "tokenized_bond",
        "depositPrincipal",
        "PrincipalFunded",
        "Deposit Principal",
    ),
    "markMatured": ActionDefinition(
        "tokenized_bond",
        "markMatured",
        "BondMatured",
        "Mark Matured",
    ),
    "redeemPrincipal": ActionDefinition(
        "tokenized_bond",
        "redeemPrincipal",
        "PrincipalRedeemed",
        "Redeem Principal",
    ),
    "markCouponDefault": ActionDefinition(
        "tokenized_bond",
        "markCouponDefault",
        "CouponDefaultRecorded",
        "Mark Coupon Default",
    ),
    "markPrincipalDefault": ActionDefinition(
        "tokenized_bond",
        "markPrincipalDefault",
        "PrincipalDefaultRecorded",
        "Mark Principal Default",
    ),
    "closeBond": ActionDefinition(
        "tokenized_bond",
        "closeBond",
        "BondClosed",
        "Close Bond",
    ),
}


def _safe_error_message(
    exc: Exception,
) -> str:
    message = str(exc).strip()

    if not message:
        return exc.__class__.__name__

    if len(message) > 700:
        return message[:700] + "..."

    return message


def _get_contract(
    client: BlockchainClient,
    contract_name: str,
) -> Any:
    if contract_name == "bond_usd":
        return client.bond_usd

    if contract_name == "tokenized_bond":
        return client.tokenized_bond

    raise TransactionPreparationError(
        f"Contract type is not supported: {contract_name}"
    )


def _contract_address(
    contract_name: str,
) -> str:
    if contract_name == "bond_usd":
        return Web3.to_checksum_address(
            BOND_USD_ADDRESS
        )

    if contract_name == "tokenized_bond":
        return Web3.to_checksum_address(
            TOKENIZED_BOND_ADDRESS
        )

    raise TransactionPreparationError(
        f"Contract address is not configured: {contract_name}"
    )


def build_action_transaction(
    client: BlockchainClient,
    *,
    action: str,
    sender: str,
    arguments: list[Any] | None = None,
    expected_event_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build, simulate and estimate one transaction for MetaMask.

    No private key is loaded. The returned payload contains calldata
    only and is signed by MetaMask in the browser.
    """
    definition = ACTION_DEFINITIONS.get(
        action
    )

    if definition is None:
        raise TransactionPreparationError(
            f"Transaction action is not supported: {action}"
        )

    try:
        checksum_sender = (
            Web3.to_checksum_address(
                sender
            )
        )

        contract = _get_contract(
            client,
            definition.contract_name,
        )

        destination = _contract_address(
            definition.contract_name
        )

        function_arguments = (
            arguments
            if arguments is not None
            else []
        )

        call_data = contract.encode_abi(
            definition.function_name,
            args=function_arguments,
        )

        simulation_transaction = {
            "from": checksum_sender,
            "to": destination,
            "data": call_data,
            "value": 0,
        }

        # Detect role, lifecycle, balance, allowance and status errors
        # before opening the MetaMask confirmation window.
        client.web3.eth.call(
            simulation_transaction
        )

        estimated_gas = int(
            client.web3.eth.estimate_gas(
                simulation_transaction
            )
        )

        gas_limit = max(
            estimated_gas
            + estimated_gas // 4,
            estimated_gas + 12_000,
        )

        return {
            "requestId": uuid4().hex,
            "action": action,
            "label": definition.label,
            "contractName":
                definition.contract_name,
            "functionName":
                definition.function_name,
            "eventName":
                definition.event_name,
            "from": checksum_sender,
            "to": destination,
            "data": call_data,
            "value": "0x0",
            "gas": hex(gas_limit),
            "arguments": function_arguments,
            "expectedEventArgs": (
                expected_event_args
                if expected_event_args
                is not None
                else {}
            ),
        }

    except TransactionPreparationError:
        raise

    except (
        ValueError,
        TypeError,
        ContractLogicError,
        Web3Exception,
    ) as exc:
        raise TransactionPreparationError(
            f"Không thể chuẩn bị giao dịch "
            f"{definition.label}. "
            f"Chi tiết: {_safe_error_message(exc)}"
        ) from exc


def _values_match(
    actual: Any,
    expected: Any,
) -> bool:
    if (
        isinstance(actual, str)
        and isinstance(expected, str)
        and Web3.is_address(actual)
        and Web3.is_address(expected)
    ):
        return (
            Web3.to_checksum_address(
                actual
            )
            == Web3.to_checksum_address(
                expected
            )
        )

    if isinstance(actual, bytes):
        return actual.hex() == str(expected)

    try:
        if isinstance(expected, int):
            return int(actual) == expected
    except (
        TypeError,
        ValueError,
    ):
        return False

    return actual == expected


def _event_matches(
    event: Any,
    expected_args: dict[str, Any],
) -> bool:
    event_args = event.get(
        "args",
        {},
    )

    for key, expected_value in (
        expected_args.items()
    ):
        if key not in event_args:
            return False

        if not _values_match(
            event_args[key],
            expected_value,
        ):
            return False

    return True


def wait_for_action_receipt(
    client: BlockchainClient,
    *,
    request: dict[str, Any],
    transaction_hash: str,
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    """Wait for and validate one browser-wallet transaction receipt."""
    action = str(
        request.get(
            "action",
            "",
        )
    )

    definition = ACTION_DEFINITIONS.get(
        action
    )

    if definition is None:
        raise BlockchainError(
            f"Unknown pending action: {action}"
        )

    try:
        if (
            not isinstance(
                transaction_hash,
                str,
            )
            or not transaction_hash.startswith(
                "0x"
            )
            or len(transaction_hash) != 66
        ):
            raise ValueError(
                "Transaction hash is not valid."
            )

        receipt = (
            client.web3.eth
            .wait_for_transaction_receipt(
                transaction_hash,
                timeout=timeout_seconds,
                poll_latency=2,
            )
        )

        base_result: dict[str, Any] = {
            "action": action,
            "label": definition.label,
            "transactionHash":
                transaction_hash,
            "etherscanUrl":
                etherscan_transaction_url(
                    transaction_hash
                ),
            "blockNumber": int(
                receipt["blockNumber"]
            ),
            "gasUsed": int(
                receipt["gasUsed"]
            ),
        }

        if int(receipt["status"]) != 1:
            return {
                **base_result,
                "status": "failed",
                "message": (
                    "Giao dịch đã được ghi vào block "
                    "nhưng thực thi thất bại."
                ),
            }

        contract = _get_contract(
            client,
            definition.contract_name,
        )

        event_factory = getattr(
            contract.events,
            definition.event_name,
            None,
        )

        if event_factory is None:
            raise BlockchainError(
                f"ABI không có event "
                f"{definition.event_name}."
            )

        event_logs = (
            event_factory()
            .process_receipt(receipt)
        )

        expected_args = request.get(
            "expectedEventArgs",
            {},
        )

        if not isinstance(
            expected_args,
            dict,
        ):
            expected_args = {}

        matching_events = [
            event
            for event in event_logs
            if _event_matches(
                event,
                expected_args,
            )
        ]

        if len(matching_events) < 1:
            raise BlockchainError(
                "Receipt thành công nhưng không tìm thấy "
                f"{definition.event_name} event phù hợp."
            )

        return {
            **base_result,
            "status": "confirmed",
            "message": (
                f"{definition.label} đã được xác nhận "
                "trên Ethereum Sepolia."
            ),
            "eventName":
                definition.event_name,
            "eventCount":
                len(matching_events),
        }

    except TimeExhausted:
        return {
            "action": action,
            "label": definition.label,
            "status": "submitted",
            "transactionHash":
                transaction_hash,
            "etherscanUrl":
                etherscan_transaction_url(
                    transaction_hash
                ),
            "message": (
                "MetaMask đã gửi giao dịch nhưng ứng dụng "
                "chưa nhận được receipt trong thời gian chờ. "
                "Kiểm tra giao dịch trên Etherscan."
            ),
        }

    except BlockchainError:
        raise

    except (
        ValueError,
        TypeError,
        Web3Exception,
    ) as exc:
        raise BlockchainError(
            f"Không thể kiểm tra receipt của "
            f"{definition.label}. "
            f"Chi tiết: {_safe_error_message(exc)}"
        ) from exc
