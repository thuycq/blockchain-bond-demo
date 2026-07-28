// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title MockBondUSD
 * @notice ERC-20 giả lập chỉ dùng để kiểm thử TokenizedBond trên local.
 *
 * Khi deploy lên Sepolia, hệ thống không sử dụng contract này mà dùng
 * BondUSDToken đã deploy trong Bài tập 4.
 */
contract MockBondUSD is ERC20, Ownable {
    error ZeroAddress();
    error ZeroAmount();

    constructor(address initialOwner)
        ERC20("Bond USD", "BONDUSD")
        Ownable(initialOwner)
    {}

    /**
     * @notice Mint BondUSD giả lập cho các tài khoản local.
     * @dev Chỉ owner được mint.
     */
    function mint(
        address to,
        uint256 amount
    ) external onlyOwner {
        if (to == address(0)) {
            revert ZeroAddress();
        }

        if (amount == 0) {
            revert ZeroAmount();
        }

        _mint(to, amount);
    }
}