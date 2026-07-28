from __future__ import annotations

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
    TOKENIZED_BOND_ADDRESS,
    etherscan_transaction_url,
)


class TransactionPreparationError(
    BlockchainError
):
    """Raised when a MetaMask transaction cannot be prepared."""


def _safe_error_message(
    exc: Exception,
) -> str:
    """Return a concise error message without exposing configuration."""
    message = str(exc).strip()

    if not message:
        return exc.__class__.__name__

    if len(message) > 500:
        return message[:500] + "..."

    return message


def build_request_whitelist_transaction(
    client: BlockchainClient,
    investor_address: str,
) -> dict[str, Any]:
    """
    Build a requestWhitelist() transaction for MetaMask.

    The function:
    - Validates the connected address.
    - Encodes requestWhitelist() using the deployed ABI.
    - Simulates the call through eth_call.
    - Estimates gas without signing.
    - Returns a browser-wallet transaction payload.

    No private key is loaded and no transaction is sent here.
    """
    try:
        investor = Web3.to_checksum_address(
            investor_address
        )

        contract_address = (
            Web3.to_checksum_address(
                TOKENIZED_BOND_ADDRESS
            )
        )

        call_data = (
            client.tokenized_bond
            .encode_abi(
                "requestWhitelist",
                args=[],
            )
        )

        simulation_transaction = {
            "from": investor,
            "to": contract_address,
            "data": call_data,
            "value": 0,
        }

        # Preflight simulation. A role, lifecycle, or status error
        # is detected before MetaMask opens.
        client.web3.eth.call(
            simulation_transaction
        )

        estimated_gas = int(
            client.web3.eth.estimate_gas(
                simulation_transaction
            )
        )

        # Add a 20% buffer for minor state/gas changes between
        # estimation and block inclusion.
        gas_limit = max(
            estimated_gas
            + estimated_gas // 5,
            estimated_gas + 10_000,
        )

        request_id = uuid4().hex

        return {
            "requestId": request_id,
            "action": "requestWhitelist",
            "label": "Request Whitelist",
            "from": investor,
            "to": contract_address,
            "data": call_data,
            "value": "0x0",
            "gas": hex(gas_limit),
        }

    except (
        ValueError,
        TypeError,
        ContractLogicError,
        Web3Exception,
    ) as exc:
        raise TransactionPreparationError(
            "Không thể chuẩn bị giao dịch requestWhitelist(). "
            f"Chi tiết: {_safe_error_message(exc)}"
        ) from exc


def wait_for_whitelist_request_receipt(
    client: BlockchainClient,
    transaction_hash: str,
    expected_investor: str,
    *,
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    """
    Wait for a requestWhitelist() receipt and verify its event.

    Returns a JSON-serialisable result for Streamlit Session State.
    """
    try:
        if not isinstance(
            transaction_hash,
            str,
        ):
            raise ValueError(
                "Transaction hash must be a string."
            )

        if (
            not transaction_hash.startswith("0x")
            or len(transaction_hash) != 66
        ):
            raise ValueError(
                "Transaction hash is not valid."
            )

        investor = Web3.to_checksum_address(
            expected_investor
        )

        receipt = (
            client.web3.eth
            .wait_for_transaction_receipt(
                transaction_hash,
                timeout=timeout_seconds,
                poll_latency=2,
            )
        )

        receipt_status = int(
            receipt["status"]
        )

        result: dict[str, Any] = {
            "action": "requestWhitelist",
            "label": "Request Whitelist",
            "transactionHash": (
                transaction_hash
            ),
            "etherscanUrl": (
                etherscan_transaction_url(
                    transaction_hash
                )
            ),
            "blockNumber": int(
                receipt["blockNumber"]
            ),
            "gasUsed": int(
                receipt["gasUsed"]
            ),
        }

        if receipt_status != 1:
            return {
                **result,
                "status": "failed",
                "message": (
                    "Giao dịch đã được ghi vào block "
                    "nhưng thực thi thất bại."
                ),
            }

        event_logs = (
            client.tokenized_bond
            .events
            .WhitelistRequested()
            .process_receipt(receipt)
        )

        matching_events = [
            event
            for event in event_logs
            if (
                Web3.to_checksum_address(
                    event["args"]["investor"]
                )
                == investor
            )
        ]

        if len(matching_events) != 1:
            raise BlockchainError(
                "Receipt thành công nhưng không tìm thấy đúng "
                "một WhitelistRequested event cho ví kết nối."
            )

        requested_at = int(
            matching_events[0]
            ["args"]
            ["requestedAt"]
        )

        return {
            **result,
            "status": "confirmed",
            "message": (
                "Yêu cầu whitelist đã được xác nhận "
                "trên Ethereum Sepolia."
            ),
            "investor": investor,
            "requestedAt": requested_at,
        }

    except TimeExhausted:
        return {
            "action": "requestWhitelist",
            "label": "Request Whitelist",
            "status": "submitted",
            "transactionHash": transaction_hash,
            "etherscanUrl": (
                etherscan_transaction_url(
                    transaction_hash
                )
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
            "Không thể kiểm tra receipt của requestWhitelist(). "
            f"Chi tiết: {_safe_error_message(exc)}"
        ) from exc
