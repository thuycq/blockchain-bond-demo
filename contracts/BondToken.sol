// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title BondToken
 * @notice Token đại diện cho quyền sở hữu trái phiếu trong Blockchain Bond Demo.
 *
 * Quy ước:
 * - 1 DBOND26 = 1 trái phiếu.
 * - Token không có phần lẻ, decimals = 0.
 * - Token không được chuyển nhượng giữa các tài khoản.
 * - Chỉ controller là TokenizedBond mới được mint và burn.
 */
contract BondToken is ERC20, Ownable {
    // =============================================================
    //                           ERRORS
    // =============================================================

    error ZeroAddress();
    error ZeroAmount();
    error NotController(address caller);
    error ControllerAlreadySet(address currentController);
    error NonTransferable();
    error ApprovalDisabled();

    // =============================================================
    //                           EVENTS
    // =============================================================

    event ControllerSet(address indexed controller);

    // =============================================================
    //                           STORAGE
    // =============================================================

    /**
     * @notice Contract duy nhất được quyền mint và burn BondToken.
     * Sau này controller sẽ là địa chỉ TokenizedBond.
     */
    address public controller;

    // =============================================================
    //                         CONSTRUCTOR
    // =============================================================

    /**
     * @param initialOwner Owner tạm thời, có quyền thiết lập controller.
     *
     * Sau khi controller được thiết lập, owner sẽ renounce ownership.
     */
    constructor(address initialOwner)
        ERC20("Demo Corporate Bond Token 2026", "DBOND26")
        Ownable(initialOwner)
    {
        if (initialOwner == address(0)) {
            revert ZeroAddress();
        }
    }

    // =============================================================
    //                          MODIFIERS
    // =============================================================

    modifier onlyController() {
        if (msg.sender != controller) {
            revert NotController(msg.sender);
        }
        _;
    }

    // =============================================================
    //                      TOKEN CONFIGURATION
    // =============================================================

    /**
     * @notice BondToken không có phần lẻ.
     */
    function decimals() public pure override returns (uint8) {
        return 0;
    }

    /**
     * @notice Thiết lập TokenizedBond làm controller.
     *
     * Điều kiện:
     * - Chỉ owner tạm thời được gọi.
     * - Chỉ được thiết lập một lần.
     * - Controller không được là zero address.
     */
    function setController(address controller_) external onlyOwner {
        if (controller_ == address(0)) {
            revert ZeroAddress();
        }

        if (controller != address(0)) {
            revert ControllerAlreadySet(controller);
        }

        controller = controller_;

        emit ControllerSet(controller_);
    }

    // =============================================================
    //                         MINT / BURN
    // =============================================================

    /**
     * @notice Mint BondToken cho investor sau khi subscribe thành công.
     */
    function mint(
        address investor,
        uint256 quantity
    ) external onlyController {
        if (investor == address(0)) {
            revert ZeroAddress();
        }

        if (quantity == 0) {
            revert ZeroAmount();
        }

        _mint(investor, quantity);
    }

    /**
     * @notice Burn BondToken khi investor refund hoặc redeem principal.
     */
    function burn(
        address investor,
        uint256 quantity
    ) external onlyController {
        if (investor == address(0)) {
            revert ZeroAddress();
        }

        if (quantity == 0) {
            revert ZeroAmount();
        }

        _burn(investor, quantity);
    }

    // =============================================================
    //                  NON-TRANSFERABLE RESTRICTIONS
    // =============================================================

    /**
     * @notice Chặn chuyển token trực tiếp.
     */
    function transfer(
        address,
        uint256
    ) public pure override returns (bool) {
        revert NonTransferable();
    }

    /**
     * @notice Chặn cấp quyền sử dụng BondToken.
     */
    function approve(
        address,
        uint256
    ) public pure override returns (bool) {
        revert ApprovalDisabled();
    }

    /**
     * @notice Chặn chuyển token bằng allowance.
     */
    function transferFrom(
        address,
        address,
        uint256
    ) public pure override returns (bool) {
        revert NonTransferable();
    }

    /**
     * @dev Lớp bảo vệ cuối cùng:
     * chỉ cho phép mint từ zero address hoặc burn về zero address.
     */
    function _update(
        address from,
        address to,
        uint256 value
    ) internal override {
        bool isMint = from == address(0);
        bool isBurn = to == address(0);

        if (!isMint && !isBurn) {
            revert NonTransferable();
        }

        super._update(from, to, value);
    }
}