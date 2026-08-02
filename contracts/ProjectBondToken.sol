// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title ProjectBondToken
 * @notice Bond token dùng chung cho nhiều dự án phát hành.
 *
 * Mỗi lần deploy truyền vào name và symbol riêng.
 * Token không chuyển nhượng và chỉ TokenizedBond tương ứng được mint/burn.
 */
contract ProjectBondToken is ERC20, Ownable {
    error ZeroAddress();
    error ZeroAmount();
    error NotController(address caller);
    error ControllerAlreadySet(address currentController);
    error NonTransferable();
    error ApprovalDisabled();

    event ControllerSet(address indexed controller);

    address public controller;

    constructor(
        string memory name_,
        string memory symbol_,
        address initialOwner
    )
        ERC20(name_, symbol_)
        Ownable(initialOwner)
    {
        if (initialOwner == address(0)) {
            revert ZeroAddress();
        }
    }

    modifier onlyController() {
        if (msg.sender != controller) {
            revert NotController(msg.sender);
        }
        _;
    }

    function decimals() public pure override returns (uint8) {
        return 0;
    }

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

    function transfer(
        address,
        uint256
    ) public pure override returns (bool) {
        revert NonTransferable();
    }

    function approve(
        address,
        uint256
    ) public pure override returns (bool) {
        revert ApprovalDisabled();
    }

    function transferFrom(
        address,
        address,
        uint256
    ) public pure override returns (bool) {
        revert NonTransferable();
    }

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
