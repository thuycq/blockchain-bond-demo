from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from web3 import Web3
from web3.contract import Contract
from web3.exceptions import Web3Exception

from app.config import (
    ADMIN_ADDRESS,
    BOND_TOKEN_ABI,
    BOND_TOKEN_ADDRESS,
    BOND_USD_ABI,
    BOND_USD_ADDRESS,
    CHAIN_ID,
    EXPECTED_CHAIN_ID,
    ISSUER_ADDRESS,
    SEPOLIA_RPC_URL,
    TOKENIZED_BOND_ABI,
    TOKENIZED_BOND_ADDRESS,
)


class BlockchainError(RuntimeError):
    """Raised when Sepolia or a deployed contract cannot be read."""


LIFECYCLE_NAMES = {
    0: "Draft",
    1: "Subscription Open",
    2: "Failed",
    3: "Active",
    4: "Matured",
    5: "Closed",
}


@dataclass(frozen=True)
class NetworkStatus:
    connected: bool
    chain_id: int
    latest_block: int
    gas_price_wei: int
    gas_price_gwei: Decimal


@dataclass(frozen=True)
class ContractCodeStatus:
    contract_name: str
    address: str
    has_code: bool
    bytecode_size: int


@dataclass(frozen=True)
class TokenMetadata:
    name: str
    symbol: str
    decimals: int
    total_supply_raw: int
    total_supply_display: Decimal


@dataclass(frozen=True)
class SystemState:
    admin: str
    issuer: str
    payment_token: str
    bond_token: str
    lifecycle_value: int
    lifecycle_name: str
    subscription_paused: bool
    subscription_start: int
    subscription_deadline: int
    total_subscribed: int
    total_raised_raw: int
    total_raised_display: Decimal
    proceeds_withdrawn: bool
    bond_token_controller: str
    bond_token_owner: str
    bond_token_supply: int
    escrow_balance_raw: int
    escrow_balance_display: Decimal


class BlockchainClient:
    """Read-only client for the Blockchain Bond Demo on Sepolia."""

    def __init__(self) -> None:
        self.web3 = Web3(
            Web3.HTTPProvider(
                SEPOLIA_RPC_URL,
                request_kwargs={"timeout": 30},
            )
        )

        if not self.web3.is_connected():
            raise BlockchainError(
                "Không thể kết nối Ethereum Sepolia qua RPC."
            )

        actual_chain_id = int(self.web3.eth.chain_id)

        if actual_chain_id != EXPECTED_CHAIN_ID:
            raise BlockchainError(
                f"RPC đang kết nối sai mạng. "
                f"Chain ID nhận được: {actual_chain_id}; "
                f"Sepolia phải là: {EXPECTED_CHAIN_ID}."
            )

        if CHAIN_ID != EXPECTED_CHAIN_ID:
            raise BlockchainError(
                f"Chain ID trong deployment file không đúng: {CHAIN_ID}."
            )

        self.bond_usd: Contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(BOND_USD_ADDRESS),
            abi=BOND_USD_ABI,
        )

        self.bond_token: Contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(BOND_TOKEN_ADDRESS),
            abi=BOND_TOKEN_ABI,
        )

        self.tokenized_bond: Contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(
                TOKENIZED_BOND_ADDRESS
            ),
            abi=TOKENIZED_BOND_ABI,
        )

    @staticmethod
    def format_units(
        raw_amount: int,
        decimals: int,
    ) -> Decimal:
        """Convert an integer token amount into human-readable units."""
        return Decimal(raw_amount) / Decimal(10**decimals)

    def get_network_status(self) -> NetworkStatus:
        """Return current Sepolia connection information."""
        try:
            gas_price_wei = int(self.web3.eth.gas_price)

            return NetworkStatus(
                connected=self.web3.is_connected(),
                chain_id=int(self.web3.eth.chain_id),
                latest_block=int(self.web3.eth.block_number),
                gas_price_wei=gas_price_wei,
                gas_price_gwei=self.format_units(
                    gas_price_wei,
                    9,
                ),
            )
        except Web3Exception as exc:
            raise BlockchainError(
                f"Không thể đọc trạng thái mạng Sepolia: {exc}"
            ) from exc

    def get_contract_code_status(
        self,
        contract_name: str,
        address: str,
    ) -> ContractCodeStatus:
        """Check whether an address contains deployed bytecode."""
        try:
            checksum_address = Web3.to_checksum_address(address)
            bytecode = self.web3.eth.get_code(checksum_address)
            bytecode_size = len(bytecode)

            return ContractCodeStatus(
                contract_name=contract_name,
                address=checksum_address,
                has_code=bytecode_size > 0,
                bytecode_size=bytecode_size,
            )
        except (ValueError, Web3Exception) as exc:
            raise BlockchainError(
                f"Không thể kiểm tra bytecode của "
                f"{contract_name}: {exc}"
            ) from exc

    def get_all_contract_code_statuses(
        self,
    ) -> list[ContractCodeStatus]:
        """Check deployed code for all three contracts."""
        return [
            self.get_contract_code_status(
                "BondUSDToken",
                BOND_USD_ADDRESS,
            ),
            self.get_contract_code_status(
                "BondToken",
                BOND_TOKEN_ADDRESS,
            ),
            self.get_contract_code_status(
                "TokenizedBond",
                TOKENIZED_BOND_ADDRESS,
            ),
        ]

    def get_token_metadata(
        self,
        contract: Contract,
    ) -> TokenMetadata:
        """Read standard ERC-20 token metadata."""
        try:
            name = str(contract.functions.name().call())
            symbol = str(contract.functions.symbol().call())
            decimals = int(contract.functions.decimals().call())
            total_supply_raw = int(
                contract.functions.totalSupply().call()
            )

            return TokenMetadata(
                name=name,
                symbol=symbol,
                decimals=decimals,
                total_supply_raw=total_supply_raw,
                total_supply_display=self.format_units(
                    total_supply_raw,
                    decimals,
                ),
            )
        except (ValueError, Web3Exception) as exc:
            raise BlockchainError(
                f"Không thể đọc metadata token: {exc}"
            ) from exc

    def get_bond_usd_metadata(self) -> TokenMetadata:
        """Read BondUSD metadata."""
        return self.get_token_metadata(self.bond_usd)

    def get_bond_token_metadata(self) -> TokenMetadata:
        """Read BondToken metadata."""
        return self.get_token_metadata(self.bond_token)

    def get_eth_balance(self, address: str) -> Decimal:
        """Read Sepolia ETH balance."""
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance_wei = int(
                self.web3.eth.get_balance(checksum_address)
            )
            return self.format_units(balance_wei, 18)
        except (ValueError, Web3Exception) as exc:
            raise BlockchainError(
                f"Không thể đọc số dư Sepolia ETH: {exc}"
            ) from exc

    def get_bond_usd_balance(self, address: str) -> Decimal:
        """Read BondUSD balance for an address."""
        try:
            checksum_address = Web3.to_checksum_address(address)
            decimals = int(
                self.bond_usd.functions.decimals().call()
            )
            raw_balance = int(
                self.bond_usd.functions.balanceOf(
                    checksum_address
                ).call()
            )

            return self.format_units(raw_balance, decimals)
        except (ValueError, Web3Exception) as exc:
            raise BlockchainError(
                f"Không thể đọc số dư BondUSD: {exc}"
            ) from exc

    def get_bond_token_balance(self, address: str) -> int:
        """Read DBOND26 balance. BondToken has zero decimals."""
        try:
            checksum_address = Web3.to_checksum_address(address)
            return int(
                self.bond_token.functions.balanceOf(
                    checksum_address
                ).call()
            )
        except (ValueError, Web3Exception) as exc:
            raise BlockchainError(
                f"Không thể đọc số dư BondToken: {exc}"
            ) from exc

    def get_system_state(self) -> SystemState:
        """Read the base deployment state without changing blockchain data."""
        try:
            bond_usd_decimals = int(
                self.bond_usd.functions.decimals().call()
            )

            admin = Web3.to_checksum_address(
                self.tokenized_bond.functions.admin().call()
            )

            issuer = Web3.to_checksum_address(
                self.tokenized_bond.functions.issuer().call()
            )

            payment_token = Web3.to_checksum_address(
                self.tokenized_bond.functions.paymentToken().call()
            )

            bond_token = Web3.to_checksum_address(
                self.tokenized_bond.functions.bondToken().call()
            )

            lifecycle_value = int(
                self.tokenized_bond.functions.lifecycle().call()
            )

            subscription_paused = bool(
                self.tokenized_bond.functions
                .subscriptionPaused()
                .call()
            )

            subscription_start = int(
                self.tokenized_bond.functions
                .subscriptionStart()
                .call()
            )

            subscription_deadline = int(
                self.tokenized_bond.functions
                .subscriptionDeadline()
                .call()
            )

            total_subscribed = int(
                self.tokenized_bond.functions
                .totalSubscribed()
                .call()
            )

            total_raised_raw = int(
                self.tokenized_bond.functions.totalRaised().call()
            )

            proceeds_withdrawn = bool(
                self.tokenized_bond.functions
                .proceedsWithdrawn()
                .call()
            )

            bond_token_controller = Web3.to_checksum_address(
                self.bond_token.functions.controller().call()
            )

            bond_token_owner = Web3.to_checksum_address(
                self.bond_token.functions.owner().call()
            )

            bond_token_supply = int(
                self.bond_token.functions.totalSupply().call()
            )

            escrow_balance_raw = int(
                self.bond_usd.functions.balanceOf(
                    TOKENIZED_BOND_ADDRESS
                ).call()
            )

            return SystemState(
                admin=admin,
                issuer=issuer,
                payment_token=payment_token,
                bond_token=bond_token,
                lifecycle_value=lifecycle_value,
                lifecycle_name=LIFECYCLE_NAMES.get(
                    lifecycle_value,
                    f"Unknown ({lifecycle_value})",
                ),
                subscription_paused=subscription_paused,
                subscription_start=subscription_start,
                subscription_deadline=subscription_deadline,
                total_subscribed=total_subscribed,
                total_raised_raw=total_raised_raw,
                total_raised_display=self.format_units(
                    total_raised_raw,
                    bond_usd_decimals,
                ),
                proceeds_withdrawn=proceeds_withdrawn,
                bond_token_controller=bond_token_controller,
                bond_token_owner=bond_token_owner,
                bond_token_supply=bond_token_supply,
                escrow_balance_raw=escrow_balance_raw,
                escrow_balance_display=self.format_units(
                    escrow_balance_raw,
                    bond_usd_decimals,
                ),
            )
        except (ValueError, Web3Exception) as exc:
            raise BlockchainError(
                f"Không thể đọc trạng thái hệ thống: {exc}"
            ) from exc

    def validate_base_deployment(
        self,
    ) -> list[str]:
        """Validate the expected clean base deployment invariants."""
        state = self.get_system_state()
        errors: list[str] = []

        expected_admin = Web3.to_checksum_address(ADMIN_ADDRESS)
        expected_issuer = Web3.to_checksum_address(ISSUER_ADDRESS)
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

        if state.admin != expected_admin:
            errors.append("Admin address không khớp.")

        if state.issuer != expected_issuer:
            errors.append("Issuer address không khớp.")

        if state.payment_token != expected_payment_token:
            errors.append("Payment token không phải BondUSD chính thức.")

        if state.bond_token != expected_bond_token:
            errors.append("BondToken reference không khớp.")

        if state.bond_token_controller != expected_controller:
            errors.append("BondToken controller không phải TokenizedBond.")

        if state.bond_token_owner != zero_address:
            errors.append("BondToken ownership chưa được renounce.")

        if state.lifecycle_value != 0:
            errors.append(
                f"Base deployment không còn ở Draft: "
                f"{state.lifecycle_name}."
            )

        if state.subscription_start != 0:
            errors.append("Subscription đã từng được mở trên base.")

        if state.total_subscribed != 0:
            errors.append("Base đã có trái phiếu được đăng ký mua.")

        if state.total_raised_raw != 0:
            errors.append("Base đã ghi nhận vốn huy động.")

        if state.bond_token_supply != 0:
            errors.append("BondToken total supply không còn bằng 0.")

        if state.escrow_balance_raw != 0:
            errors.append("Escrow BondUSD không còn bằng 0.")

        return errors