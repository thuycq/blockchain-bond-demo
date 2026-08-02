from __future__ import annotations

import importlib
import json
import runpy
import sys
import types
from dataclasses import replace
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERIES_FILE = PROJECT_ROOT / "deployment" / "bond_series.json"
MAIN_APP_FILE = PROJECT_ROOT / "app" / "streamlit_app.py"

# Giữ bản config/overview gốc để tạo từng phiên chạy độc lập.
_BASE_CONFIG = importlib.import_module("app.config")
_BASE_OVERVIEW = importlib.import_module("app.overview")


def _read_series() -> dict[str, Any]:
    if not SERIES_FILE.exists():
        raise RuntimeError(
            "Chưa có deployment/bond_series.json. "
            "Hãy chạy script deploy ba bond mới trên Sepolia trước."
        )

    with SERIES_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise RuntimeError("bond_series.json không hợp lệ.")

    bonds = data.get("bonds")

    if not isinstance(bonds, list):
        raise RuntimeError("bond_series.json không có danh sách bonds hợp lệ.")

    return data


def _find_bond(
    series: dict[str, Any],
    bond_key: str,
) -> dict[str, Any]:
    for item in series["bonds"]:
        if (
            isinstance(item, dict)
            and item.get("key") == bond_key
        ):
            return item

    raise RuntimeError(
        f"Không tìm thấy cấu hình bond: {bond_key}"
    )


def _copy_module(
    source: types.ModuleType,
    module_name: str,
) -> types.ModuleType:
    target = types.ModuleType(module_name)

    for name, value in source.__dict__.items():
        if name in {
            "__name__",
            "__loader__",
            "__package__",
            "__spec__",
        }:
            continue

        setattr(target, name, value)

    target.__package__ = "app"
    return target


def _build_config_module(
    series: dict[str, Any],
    bond: dict[str, Any],
) -> types.ModuleType:
    config = _copy_module(
        _BASE_CONFIG,
        "app.config",
    )

    roles = series.get("roles")
    payment_token = series.get("paymentToken")
    contracts = bond.get("contracts")

    if not isinstance(roles, dict):
        raise RuntimeError("Thiếu roles trong bond_series.json.")

    if not isinstance(payment_token, dict):
        raise RuntimeError("Thiếu paymentToken trong bond_series.json.")

    if not isinstance(contracts, dict):
        raise RuntimeError("Thiếu contracts của bond đã chọn.")

    bond_token = contracts.get("BondToken")
    tokenized_bond = contracts.get("TokenizedBond")

    if not isinstance(bond_token, dict):
        raise RuntimeError("Thiếu BondToken deployment.")

    if not isinstance(tokenized_bond, dict):
        raise RuntimeError("Thiếu TokenizedBond deployment.")

    require_address = _BASE_CONFIG.require_address

    bond_usd_address = require_address(
        payment_token.get("address"),
        "BondUSDToken address",
    )
    bond_token_address = require_address(
        bond_token.get("address"),
        "BondToken address",
    )
    tokenized_bond_address = require_address(
        tokenized_bond.get("address"),
        "TokenizedBond address",
    )
    admin_address = require_address(
        roles.get("admin"),
        "admin address",
    )
    issuer_address = require_address(
        roles.get("issuer"),
        "issuer address",
    )

    deployment = {
        "version": "v2-whitelist-self-registration",
        "cleanDeployment": True,
        "network": series.get("network", "sepolia"),
        "chainId": int(
            series.get(
                "chainId",
                _BASE_CONFIG.EXPECTED_CHAIN_ID,
            )
        ),
        "roles": roles,
        "contracts": {
            "BondUSDToken": payment_token,
            "BondToken": bond_token,
            "TokenizedBond": tokenized_bond,
        },
    }

    config.DEPLOYMENT_FILE = SERIES_FILE
    config.DEPLOYMENT = deployment
    config.DEPLOYMENT_VERSION = (
        "v2-whitelist-self-registration"
    )
    config.CHAIN_ID = int(deployment["chainId"])

    config.BOND_USD_ADDRESS = bond_usd_address
    config.BOND_TOKEN_ADDRESS = bond_token_address
    config.TOKENIZED_BOND_ADDRESS = tokenized_bond_address
    config.ADMIN_ADDRESS = admin_address
    config.ISSUER_ADDRESS = issuer_address

    config.EXPECTED_CONTRACT_ADDRESSES = {
        "BondUSDToken": bond_usd_address,
        "BondToken": bond_token_address,
        "TokenizedBond": tokenized_bond_address,
    }

    config.EXPECTED_ROLE_ADDRESSES = {
        "admin": admin_address,
        "issuer": issuer_address,
    }

    config.ACTIVE_BOND_KEY = str(bond.get("key", ""))
    config.ACTIVE_BOND_NAME = str(
        bond.get("displayName", "Bond")
    )
    config.ACTIVE_BOND_SYMBOL = str(
        bond.get("symbol", "BOND")
    )

    return config


def _build_overview_module(
    bond: dict[str, Any],
) -> types.ModuleType:
    overview = _copy_module(
        _BASE_OVERVIEW,
        "app.overview",
    )

    display_name = str(
        bond.get("displayName", "Bond")
    )
    display_symbol = str(
        bond.get("symbol", "BOND")
    )

    def get_bond_overview(client: Any) -> Any:
        result = _BASE_OVERVIEW.get_bond_overview(
            client
        )

        return replace(
            result,
            bond_name=display_name,
            bond_symbol=display_symbol,
        )

    overview.get_bond_overview = get_bond_overview
    return overview


def _clear_dependent_modules() -> None:
    keep = {
        "app.bond_runtime",
    }

    removed: list[str] = []

    for module_name in list(sys.modules):
        if (
            module_name.startswith("app.")
            and module_name not in keep
        ):
            removed.append(module_name)
            sys.modules.pop(module_name, None)

    app_package = sys.modules.get("app")

    if app_package is None:
        return

    for module_name in removed:
        child_name = module_name.split(".", 1)[1]

        if "." not in child_name:
            try:
                delattr(app_package, child_name)
            except AttributeError:
                pass


def run_bond_app(bond_key: str) -> None:
    series = _read_series()
    bond = _find_bond(series, bond_key)

    config_module = _build_config_module(
        series,
        bond,
    )
    overview_module = _build_overview_module(
        bond
    )

    _clear_dependent_modules()

    sys.modules["app.config"] = config_module
    sys.modules["app.overview"] = overview_module

    app_package = sys.modules.get("app")

    if app_package is not None:
        setattr(app_package, "config", config_module)
        setattr(app_package, "overview", overview_module)

    runpy.run_path(
        str(MAIN_APP_FILE),
        run_name="__main__",
    )
