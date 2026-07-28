from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class WalletState:
    """Current browser-wallet state returned by MetaMask."""

    installed: bool
    connected: bool
    account: str
    chain_id: str
    error: str


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

.wallet-heading {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--st-text-color);
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

    const statusElement =
        parentElement.querySelector("#wallet-status");

    const errorElement =
        parentElement.querySelector("#wallet-error");

    const requiredChainId =
        String(data.requiredChainId || "").toLowerCase();

    let currentWallet = {
        installed: false,
        connected: false,
        account: "",
        chainId: "",
        error: ""
    };

    function emitWallet(nextWallet) {
        currentWallet = {
            ...currentWallet,
            ...nextWallet
        };

        setStateValue(
            "wallet",
            currentWallet
        );

        render();
    }

    function render() {
        const {
            installed,
            connected,
            account,
            chainId,
            error
        } = currentWallet;

        errorElement.textContent = error || "";

        if (!installed) {
            statusElement.textContent =
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
            statusElement.textContent =
                "MetaMask is available. Connect the wallet to continue.";

            connectButton.textContent =
                "Connect MetaMask";

            return;
        }

        connectButton.textContent =
            "Wallet Connected";

        statusElement.textContent =
            `${account} | Chain ID: ${chainId}`;
    }

    async function readWalletState(
        requestAccounts
    ) {
        if (!window.ethereum) {
            emitWallet({
                installed: false,
                connected: false,
                account: "",
                chainId: "",
                error:
                    "Install the MetaMask browser extension before continuing."
            });

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
                chainId: chainId || "",
                error: ""
            });
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

    readWalletState(false);

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


def render_wallet_connector(
    *,
    required_chain_id: str,
    key: str = "bond_wallet_connector",
) -> WalletState:
    """Mount the MetaMask component and normalize its result."""
    result = wallet_component(
        data={
            "requiredChainId": required_chain_id,
        },
        default={
            "wallet": {
                "installed": False,
                "connected": False,
                "account": "",
                "chainId": "",
                "error": "",
            }
        },
        key=key,
        on_wallet_change=lambda: None,
        width="stretch",
    )

    raw_wallet: Any = getattr(
        result,
        "wallet",
        None,
    )

    if not isinstance(raw_wallet, dict):
        raw_wallet = {}

    return WalletState(
        installed=bool(
            raw_wallet.get(
                "installed",
                False,
            )
        ),
        connected=bool(
            raw_wallet.get(
                "connected",
                False,
            )
        ),
        account=str(
            raw_wallet.get(
                "account",
                "",
            )
            or ""
        ),
        chain_id=str(
            raw_wallet.get(
                "chainId",
                "",
            )
            or ""
        ),
        error=str(
            raw_wallet.get(
                "error",
                "",
            )
            or ""
        ),
    )
