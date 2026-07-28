// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IBondToken
 * @notice Interface tối thiểu để TokenizedBond quản lý BondToken.
 */
interface IBondToken {
    /**
     * @notice Mint BondToken cho nhà đầu tư.
     * @param investor Địa chỉ nhà đầu tư nhận token.
     * @param quantity Số lượng trái phiếu được mint.
     */
    function mint(
        address investor,
        uint256 quantity
    ) external;

    /**
     * @notice Burn BondToken của nhà đầu tư.
     * @param investor Địa chỉ nhà đầu tư bị burn token.
     * @param quantity Số lượng trái phiếu bị burn.
     */
    function burn(
        address investor,
        uint256 quantity
    ) external;

    /**
     * @notice Trả về số lượng BondToken của một tài khoản.
     */
    function balanceOf(
        address account
    ) external view returns (uint256);

    /**
     * @notice Trả về tổng số BondToken đang lưu hành.
     */
    function totalSupply()
        external
        view
        returns (uint256);

    /**
     * @notice Trả về địa chỉ contract được quyền mint và burn.
     */
    function controller()
        external
        view
        returns (address);
}