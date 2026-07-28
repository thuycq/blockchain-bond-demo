from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class WalletState:
    """Browser-wallet and transaction state returned by MetaMask."""

    installed: bool
    connected: bool
    account: str
    chain_id: str
    error: str

    transaction_request_id: str
    transaction_action: str
    transaction_status: str
    transaction_hash: str
    transaction_error: str


WALLET_HTML = """
<div class="wallet-card">
    <div class="wallet-heading">MetaMask Wallet</div>

    <div id="wallet-status" class="wallet-status">
        Checking MetaMask...
    </div>

    <div class="wallet-actions">
        <button id="connect-wallet" class="primary-button">
            Connect MetaMask
        </button>

        <button id="switch-network" class="secondary-button">
            Switch to Sepolia
        </button>
    </div>

    <div id="wallet-error" class="wallet-error"></div>

    <div id="transaction-panel" class="transaction-panel">
        <div class="transaction-heading">
            Wallet Transaction
        </div>

        <div id="transaction-status" class="transaction-status">
            No transaction is waiting for MetaMask.
        </div>
    </div>
</div>
"""


WALLET_CSS = """
.wallet-card {
    border: 1px solid var(--st-border-color);
    border-radius: 0.75rem;
    padding: 1.25rem;
    background: var(--st-secondary-background-color);
    font-family: var(--st-font);
}

.wallet-heading,
.transaction-heading {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--st-text-color);
}

.wallet-heading {
    margin-bottom: 0.5rem;
}

.wallet-status {
    color: var(--st-text-color);
    margin-bottom: 1rem;
    word-break: break-word;
}

.wallet-actions {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
}

button {
    border-radius: 0.5rem;
    padding: 0.65rem 1rem;
    font-family: var(--st-font);
    font-weight: 600;
    cursor: pointer;
}

.primary-button {
    border: 1px solid var(--st-primary-color);
    background: var(--st-primary-color);
    color: white;
}

.secondary-button {
    border: 1px solid var(--st-primary-color);
    background: transparent;
    color: var(--st-primary-color);
}

button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
}

.wallet-error {
    color: #dc2626;
    margin-top: 0.75rem;
    min-height: 1.25rem;
}

.transaction-panel {
    border-top: 1px solid var(--st-border-color);
    margin-top: 1rem;
    padding-top: 1rem;
}

.transaction-status {
    color: var(--st-text-color);
    margin-top: 0.45rem;
    word-break: break-word;
}
"""


WALLET_JS = r"""
export default function(component) {
    const {
        data,
        parentElement,
        setStateValue
    } = component;

    const connectButton =
        parentElement.querySelector("#connect-wallet");

    const switchButton =
        parentElement.querySelector("#switch-network");

    const walletStatusElement =
        parentElement.querySelector("#wallet-status");

    const walletErrorElement =
        parentElement.querySelector("#wallet-error");

    const transactionStatusElement =
        parentElement.querySelector("#transaction-status");

    const requiredChainId =
        String(
            data.requiredChainId || ""
        ).toLowerCase();

    const transactionRequest =
        data.transactionRequest || null;

    const previousTransaction =
        data.previousTransaction || {};

    let currentWallet = {
        installed: false,
        connected: false,
        account: "",
        chainId: "",
        error: ""
    };

    let currentTransaction = {
        requestId:
            String(
                previousTransaction.requestId || ""
            ),
        action:
            String(
                previousTransaction.action || ""
            ),
        status:
            String(
                previousTransaction.status || ""
            ),
        hash:
            String(
                previousTransaction.hash || ""
            ),
        error:
            String(
                previousTransaction.error || ""
            )
    };

    if (!window.__bondWalletRequestRegistry) {
        window.__bondWalletRequestRegistry =
            new Set();
    }

    const requestRegistry =
        window.__bondWalletRequestRegistry;

    function emitWallet(nextWallet) {
        currentWallet = {
            ...currentWallet,
            ...nextWallet
        };

        setStateValue(
            "wallet",
            currentWallet
        );

        renderWallet();
    }

    function emitTransaction(nextTransaction) {
        currentTransaction = {
            ...currentTransaction,
            ...nextTransaction
        };

        setStateValue(
            "transaction",
            currentTransaction
        );

        renderTransaction();
    }

    function renderWallet() {
        const {
            installed,
            connected,
            account,
            chainId,
            error
        } = currentWallet;

        walletErrorElement.textContent =
            error || "";

        if (!installed) {
            walletStatusElement.textContent =
                "MetaMask extension was not detected.";

            connectButton.disabled = true;
            switchButton.disabled = true;
            return;
        }

        connectButton.disabled = false;

        const correctNetwork =
            String(chainId).toLowerCase()
            === requiredChainId;

        switchButton.disabled =
            !connected || correctNetwork;

        if (!connected) {
            walletStatusElement.textContent =
                "MetaMask is available. Connect the wallet to continue.";

            connectButton.textContent =
                "Connect MetaMask";

            return;
        }

        connectButton.textContent =
            "Wallet Connected";

        walletStatusElement.textContent =
            `${account} | Chain ID: ${chainId}`;
    }

    function renderTransaction() {
        const {
            status,
            hash,
            error
        } = currentTransaction;

        if (status === "submitted") {
            transactionStatusElement.textContent =
                `Transaction submitted: ${hash}`;
            return;
        }

        if (status === "rejected") {
            transactionStatusElement.textContent =
                `Transaction rejected: ${error}`;
            return;
        }

        if (status === "failed") {
            transactionStatusElement.textContent =
                `Transaction failed: ${error}`;
            return;
        }

        if (
            transactionRequest
            && transactionRequest.requestId
        ) {
            transactionStatusElement.textContent =
                "A transaction is ready. Confirm it in MetaMask.";
            return;
        }

        transactionStatusElement.textContent =
            "No transaction is waiting for MetaMask.";
    }

    async function readWalletState(
        requestAccounts
    ) {
        if (!window.ethereum) {
            currentWallet = {
                installed: false,
                connected: false,
                account: "",
                chainId: "",
                error:
                    "Install the MetaMask browser extension before continuing."
            };

            renderWallet();
            return;
        }

        try {
            const accountMethod =
                requestAccounts
                    ? "eth_requestAccounts"
                    : "eth_accounts";

            const accounts =
                await window.ethereum.request({
                    method: accountMethod
                });

            const chainId =
                await window.ethereum.request({
                    method: "eth_chainId"
                });

            currentWallet = {
                installed: true,
                connected:
                    Array.isArray(accounts)
                    && accounts.length > 0,
                account:
                    Array.isArray(accounts)
                    && accounts.length > 0
                        ? accounts[0]
                        : "",
                chainId: chainId || "",
                error: ""
            };

            renderWallet();

            // Only emit when the browser state differs from
            // the previous Python-side state.
            const previousWallet =
                data.previousWallet || {};

            const walletChanged =
                Boolean(previousWallet.installed)
                    !== currentWallet.installed
                || Boolean(previousWallet.connected)
                    !== currentWallet.connected
                || String(previousWallet.account || "")
                    .toLowerCase()
                    !== currentWallet.account.toLowerCase()
                || String(previousWallet.chainId || "")
                    .toLowerCase()
                    !== currentWallet.chainId.toLowerCase()
                || String(previousWallet.error || "")
                    !== currentWallet.error;

            if (walletChanged) {
                setStateValue(
                    "wallet",
                    currentWallet
                );
            }
        } catch (error) {
            emitWallet({
                installed: true,
                connected: false,
                account: "",
                chainId: "",
                error:
                    error?.message
                    || "MetaMask connection failed."
            });
        }
    }

    async function switchToSepolia() {
        if (!window.ethereum) {
            return;
        }

        try {
            await window.ethereum.request({
                method: "wallet_switchEthereumChain",
                params: [
                    {
                        chainId: requiredChainId
                    }
                ]
            });

            await readWalletState(false);
        } catch (error) {
            emitWallet({
                error:
                    error?.message
                    || "Unable to switch MetaMask to Sepolia."
            });
        }
    }

    function validateTransactionRequest() {
        if (
            !transactionRequest
            || !transactionRequest.requestId
        ) {
            return null;
        }

        if (!currentWallet.installed) {
            throw new Error(
                "MetaMask is not installed."
            );
        }

        if (!currentWallet.connected) {
            throw new Error(
                "Connect MetaMask before sending the transaction."
            );
        }

        if (
            String(currentWallet.chainId).toLowerCase()
            !== requiredChainId
        ) {
            throw new Error(
                "MetaMask must be connected to Ethereum Sepolia."
            );
        }

        const connectedAccount =
            String(
                currentWallet.account || ""
            ).toLowerCase();

        const requestedFrom =
            String(
                transactionRequest.from || ""
            ).toLowerCase();

        if (
            !connectedAccount
            || connectedAccount !== requestedFrom
        ) {
            throw new Error(
                "The transaction sender does not match the connected MetaMask account."
            );
        }

        if (
            !transactionRequest.to
            || !transactionRequest.data
        ) {
            throw new Error(
                "The transaction payload is incomplete."
            );
        }

        return {
            from: transactionRequest.from,
            to: transactionRequest.to,
            data: transactionRequest.data,
            value:
                transactionRequest.value
                || "0x0",
            gas: transactionRequest.gas
        };
    }

    async function maybeSendTransaction() {
        if (
            !transactionRequest
            || !transactionRequest.requestId
        ) {
            return;
        }

        const requestId =
            String(
                transactionRequest.requestId
            );

        if (
            currentTransaction.requestId === requestId
            && [
                "submitted",
                "rejected",
                "failed"
            ].includes(
                currentTransaction.status
            )
        ) {
            return;
        }

        if (
            requestRegistry.has(
                requestId
            )
        ) {
            return;
        }

        requestRegistry.add(
            requestId
        );

        try {
            const transaction =
                validateTransactionRequest();

            if (!transaction) {
                return;
            }

            transactionStatusElement.textContent =
                "Waiting for confirmation in MetaMask...";

            const transactionHash =
                await window.ethereum.request({
                    method: "eth_sendTransaction",
                    params: [transaction]
                });

            emitTransaction({
                requestId: requestId,
                action:
                    String(
                        transactionRequest.action
                        || ""
                    ),
                status: "submitted",
                hash:
                    String(
                        transactionHash
                        || ""
                    ),
                error: ""
            });
        } catch (error) {
            const rejected =
                Number(error?.code) === 4001;

            emitTransaction({
                requestId: requestId,
                action:
                    String(
                        transactionRequest.action
                        || ""
                    ),
                status:
                    rejected
                        ? "rejected"
                        : "failed",
                hash: "",
                error:
                    error?.message
                    || (
                        rejected
                            ? "The user rejected the transaction."
                            : "MetaMask transaction failed."
                    )
            });
        }
    }

    function handleAccountsChanged(accounts) {
        emitWallet({
            installed: true,
            connected:
                Array.isArray(accounts)
                && accounts.length > 0,
            account:
                Array.isArray(accounts)
                && accounts.length > 0
                    ? accounts[0]
                    : "",
            error: ""
        });
    }

    function handleChainChanged(chainId) {
        emitWallet({
            chainId: chainId || "",
            error: ""
        });
    }

    connectButton.onclick = async () => {
        await readWalletState(true);
    };

    switchButton.onclick = async () => {
        await switchToSepolia();
    };

    if (window.ethereum) {
        window.ethereum.on(
            "accountsChanged",
            handleAccountsChanged
        );

        window.ethereum.on(
            "chainChanged",
            handleChainChanged
        );
    }

    async function initialise() {
        renderTransaction();
        await readWalletState(false);
        await maybeSendTransaction();
    }

    initialise();

    return () => {
        connectButton.onclick = null;
        switchButton.onclick = null;

        if (
            window.ethereum
            && window.ethereum.removeListener
        ) {
            window.ethereum.removeListener(
                "accountsChanged",
                handleAccountsChanged
            );

            window.ethereum.removeListener(
                "chainChanged",
                handleChainChanged
            );
        }
    };
}
"""


wallet_component = st.components.v2.component(
    name="bond_metamask_wallet",
    html=WALLET_HTML,
    css=WALLET_CSS,
    js=WALLET_JS,
)


def _component_value(
    result: Any,
    name: str,
) -> dict[str, Any]:
    raw_value = getattr(
        result,
        name,
        None,
    )

    if isinstance(raw_value, dict):
        return raw_value

    return {}


def _previous_component_value(
    key: str,
    name: str,
) -> dict[str, Any]:
    previous_result = (
        st.session_state.get(key)
    )

    if previous_result is None:
        return {}

    raw_value = getattr(
        previous_result,
        name,
        None,
    )

    if isinstance(raw_value, dict):
        return raw_value

    return {}


def render_wallet_connector(
    *,
    required_chain_id: str,
    transaction_request: (
        dict[str, Any] | None
    ) = None,
    key: str = "bond_wallet_connector",
) -> WalletState:
    """
    Mount MetaMask and optionally ask it to send one transaction.

    Python provides the transaction payload. MetaMask keeps the
    private key and performs all signing in the browser.
    """
    previous_wallet = (
        _previous_component_value(
            key,
            "wallet",
        )
    )

    previous_transaction = (
        _previous_component_value(
            key,
            "transaction",
        )
    )

    result = wallet_component(
        data={
            "requiredChainId":
                required_chain_id,
            "transactionRequest":
                transaction_request,
            "previousWallet":
                previous_wallet,
            "previousTransaction":
                previous_transaction,
        },
        default={
            "wallet": {
                "installed": False,
                "connected": False,
                "account": "",
                "chainId": "",
                "error": "",
            },
            "transaction": {
                "requestId": "",
                "action": "",
                "status": "",
                "hash": "",
                "error": "",
            },
        },
        key=key,
        on_wallet_change=lambda: None,
        on_transaction_change=lambda: None,
        width="stretch",
    )

    wallet = _component_value(
        result,
        "wallet",
    )

    transaction = _component_value(
        result,
        "transaction",
    )

    return WalletState(
        installed=bool(
            wallet.get(
                "installed",
                False,
            )
        ),
        connected=bool(
            wallet.get(
                "connected",
                False,
            )
        ),
        account=str(
            wallet.get(
                "account",
                "",
            )
            or ""
        ),
        chain_id=str(
            wallet.get(
                "chainId",
                "",
            )
            or ""
        ),
        error=str(
            wallet.get(
                "error",
                "",
            )
            or ""
        ),
        transaction_request_id=str(
            transaction.get(
                "requestId",
                "",
            )
            or ""
        ),
        transaction_action=str(
            transaction.get(
                "action",
                "",
            )
            or ""
        ),
        transaction_status=str(
            transaction.get(
                "status",
                "",
            )
            or ""
        ),
        transaction_hash=str(
            transaction.get(
                "hash",
                "",
            )
            or ""
        ),
        transaction_error=str(
            transaction.get(
                "error",
                "",
            )
            or ""
        ),
    )
