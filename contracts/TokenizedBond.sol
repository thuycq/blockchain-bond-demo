// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

import {IBondToken} from "./interfaces/IBondToken.sol";

/**
 * @title TokenizedBond
 * @notice Smart contract nghiệp vụ trung tâm cho hệ thống trái phiếu token hóa.
 *
 * Phiên bản này bổ sung quy trình whitelist đầy đủ:
 * - Investor tự gửi requestWhitelist().
 * - Admin approve hoặc reject request.
 * - Admin có thể revoke quyền của investor đã được duyệt.
 *
 * BondUSD được dùng để:
 * - Đăng ký mua trái phiếu.
 * - Hoàn tiền nếu offering thất bại.
 * - Thanh toán coupon.
 * - Hoàn trả principal.
 */
contract TokenizedBond is ReentrancyGuard {
    using SafeERC20 for IERC20;

    // =============================================================
    // ENUMS
    // =============================================================

    enum Lifecycle {
        Draft,
        SubscriptionOpen,
        Failed,
        Active,
        Matured,
        Closed
    }

    enum WhitelistStatus {
        None,
        Pending,
        Approved,
        Rejected,
        Revoked
    }

    // =============================================================
    // STRUCTS
    // =============================================================

    struct BondInfo {
        string bondName;
        address adminAddress;
        address issuerAddress;
        address paymentTokenAddress;
        address bondTokenAddress;
        uint256 faceValue;
        uint256 issuePrice;
        uint256 maxSupply;
        uint256 minimumSubscription;
        uint256 annualCouponRateBps;
        uint256 couponPerPeriod;
        uint256 gracePeriod;
    }

    struct OfferingInfo {
        Lifecycle currentLifecycle;
        bool paused;
        uint256 start;
        uint256 deadline;
        uint256 finalizedTime;
        uint256 subscribed;
        uint256 raised;
        uint256 refunded;
        bool proceedsAreWithdrawn;
    }

    struct InvestorPosition {
        bool isWhitelisted;
        uint256 quantitySubscribed;
        uint256 amountPaid;
        uint256 bondBalance;
        bool hasClaimedRefund;
        bool hasClaimedCoupon1;
        bool hasClaimedCoupon2;
        bool hasRedeemedPrincipal;
        uint256 refundableAmount;
        uint256 claimableCouponTotal;
        uint256 redeemablePrincipal;
    }

    struct CouponInfo {
        uint256 dueDate;
        uint256 requiredAmount;
        uint256 fundedAmount;
        uint256 claimedAmount;
        bool isInDefault;
        uint256 defaultTimestamp;
    }

    struct PrincipalInfo {
        uint256 maturityDate;
        uint256 requiredAmount;
        uint256 fundedAmount;
        uint256 redeemedAmount;
        bool isInDefault;
        uint256 defaultTimestamp;
    }

    struct WhitelistInfo {
        WhitelistStatus status;
        bool isWhitelisted;
        uint256 requestedAt;
        uint256 reviewedAt;
    }

    // =============================================================
    // CUSTOM ERRORS
    // =============================================================

    // Roles
    error NotAdmin(address caller);
    error NotIssuer(address caller);
    error RoleCannotRegister(address account);

    // Address and configuration
    error ZeroAddress();
    error AddressIsNotContract(address account);
    error RolesMustDiffer();
    error InvalidBondTokenState();

    // Lifecycle
    error InvalidLifecycle(Lifecycle current);
    error AlreadyClosed();

    // Whitelist and pause
    error NotWhitelisted(address investor);
    error InvalidWhitelistStatus(
        address investor,
        WhitelistStatus current
    );
    error ApplicantIndexOutOfBounds(uint256 index);
    error AlreadyPaused();
    error NotPaused();
    error SubscriptionIsPaused();

    // Subscription
    error ZeroQuantity();
    error SubscriptionExpired();
    error MaxSupplyExceeded(
        uint256 requested,
        uint256 remaining
    );
    error InsufficientTokenBalance(
        uint256 required,
        uint256 available
    );
    error InsufficientAllowance(
        uint256 required,
        uint256 allowance
    );

    // Finalize and proceeds
    error CannotFinalizeYet();
    error ProceedsAlreadyWithdrawn();

    // Refund
    error NothingToRefund();
    error RefundAlreadyClaimed();

    // Coupon
    error InvalidCouponPeriod(uint8 period);
    error CouponAlreadyFunded(uint8 period);
    error CouponNotDue(uint8 period);
    error CouponNotFunded(uint8 period);
    error CouponAlreadyClaimed(uint8 period);

    // Principal
    error NotMatured();
    error PrincipalAlreadyFunded();
    error PrincipalNotFunded();
    error CouponsNotFullyClaimed();
    error PrincipalAlreadyRedeemed();

    // Default and close
    error DefaultNotEligible();
    error DefaultAlreadyRecorded();
    error CloseConditionsNotMet();

    // Native token
    error NativeTokenNotAccepted();

    // =============================================================
    // EVENTS
    // =============================================================

    event WhitelistRequested(
        address indexed investor,
        uint256 requestedAt
    );

    event WhitelistApproved(
        address indexed investor,
        address indexed admin,
        uint256 approvedAt
    );

    event WhitelistRejected(
        address indexed investor,
        address indexed admin,
        uint256 rejectedAt
    );

    event WhitelistRevoked(
        address indexed investor,
        address indexed admin,
        uint256 revokedAt
    );

    /**
     * @dev Giữ event cũ để tương thích với log/audit đã xây dựng.
     */
    event WhitelistUpdated(
        address indexed investor,
        bool approved
    );

    event SubscriptionOpened(
        uint256 start,
        uint256 deadline
    );

    event SubscriptionPaused(uint256 pausedAt);
    event SubscriptionUnpaused(uint256 unpausedAt);

    event BondSubscribed(
        address indexed investor,
        uint256 quantity,
        uint256 payment,
        uint256 investorTotalQuantity,
        uint256 totalSubscribed
    );

    event OfferingFinalized(
        bool successful,
        Lifecycle lifecycle,
        uint256 totalSubscribed,
        uint256 totalRaised,
        uint256 finalizedAt
    );

    event ProceedsWithdrawn(
        address indexed issuer,
        uint256 amount
    );

    event RefundClaimed(
        address indexed investor,
        uint256 quantity,
        uint256 amount
    );

    event CouponFunded(
        uint8 indexed period,
        uint256 amount,
        uint256 fundedAt
    );

    event CouponClaimed(
        uint8 indexed period,
        address indexed investor,
        uint256 quantity,
        uint256 amount
    );

    event PrincipalFunded(
        uint256 amount,
        uint256 fundedAt
    );

    event PrincipalRedeemed(
        address indexed investor,
        uint256 quantity,
        uint256 amount
    );

    event CouponDefaultRecorded(
        uint8 indexed period,
        uint256 recordedAt
    );

    event PrincipalDefaultRecorded(uint256 recordedAt);

    event DefaultCured(
        uint8 indexed obligationType,
        uint8 indexed period,
        uint256 curedAt
    );

    event BondMatured(
        uint256 maturity,
        uint256 markedAt
    );

    event BondClosed(
        Lifecycle previousLifecycle,
        uint256 closedAt
    );

    // =============================================================
    // ECONOMIC CONSTANTS
    // =============================================================

    string public constant BOND_NAME =
        "Demo Corporate Bond 2026";

    uint256 public constant FACE_VALUE = 100 ether;
    uint256 public constant ISSUE_PRICE = 100 ether;

    uint256 public constant MAX_BOND_SUPPLY = 100;
    uint256 public constant MINIMUM_SUBSCRIPTION = 60;

    uint256 public constant ANNUAL_COUPON_RATE_BPS = 1_000;
    uint256 public constant COUPON_PER_PERIOD = 5 ether;

    uint8 public constant COUPON_PERIOD_COUNT = 2;

    // =============================================================
    // TIME CONSTANTS
    // =============================================================

    uint256 public constant SUBSCRIPTION_DURATION = 10 minutes;
    uint256 public constant COUPON_1_DELAY = 5 minutes;
    uint256 public constant COUPON_2_DELAY = 10 minutes;
    uint256 public constant GRACE_PERIOD = 3 minutes;

    // =============================================================
    // IMMUTABLE ADDRESSES
    // =============================================================

    address public immutable admin;
    address public immutable issuer;

    IERC20 public immutable paymentToken;
    IBondToken public immutable bondToken;

    // =============================================================
    // LIFECYCLE AND OFFERING STORAGE
    // =============================================================

    Lifecycle public lifecycle;

    bool public subscriptionPaused;
    bool public proceedsWithdrawn;

    uint256 public subscriptionStart;
    uint256 public subscriptionDeadline;
    uint256 public finalizedAt;
    uint256 public maturity;

    uint256 public totalSubscribed;
    uint256 public totalRaised;
    uint256 public totalRefunded;

    // =============================================================
    // COUPON STORAGE
    // =============================================================

    mapping(uint8 => uint256) public couponDue;
    mapping(uint8 => uint256) public couponRequired;
    mapping(uint8 => uint256) public couponFunded;
    mapping(uint8 => uint256) public couponClaimedTotal;

    // =============================================================
    // PRINCIPAL STORAGE
    // =============================================================

    uint256 public principalRequired;
    uint256 public principalFunded;
    uint256 public principalRedeemedTotal;

    // =============================================================
    // INVESTOR AND WHITELIST STORAGE
    // =============================================================

    mapping(address => bool) public whitelisted;
    mapping(address => WhitelistStatus) public whitelistStatus;
    mapping(address => uint256) public whitelistRequestedAt;
    mapping(address => uint256) public whitelistReviewedAt;

    address[] private whitelistApplicants;
    mapping(address => bool) private applicantRecorded;

    mapping(address => uint256) public subscribedQuantity;
    mapping(address => uint256) public paidAmount;

    mapping(address => bool) public refundClaimed;
    mapping(uint8 => mapping(address => bool))
        public couponClaimed;
    mapping(address => bool) public principalRedeemed;

    // =============================================================
    // DEFAULT STORAGE
    // =============================================================

    mapping(uint8 => bool) public couponDefaulted;
    mapping(uint8 => uint256) public couponDefaultedAt;

    bool public principalDefaulted;
    uint256 public principalDefaultedAt;

    // =============================================================
    // CONSTRUCTOR
    // =============================================================

    constructor(
        address admin_,
        address issuer_,
        address paymentToken_,
        address bondToken_
    ) {
        if (
            admin_ == address(0) ||
            issuer_ == address(0) ||
            paymentToken_ == address(0) ||
            bondToken_ == address(0)
        ) {
            revert ZeroAddress();
        }

        if (admin_ == issuer_) {
            revert RolesMustDiffer();
        }

        if (paymentToken_.code.length == 0) {
            revert AddressIsNotContract(paymentToken_);
        }

        if (bondToken_.code.length == 0) {
            revert AddressIsNotContract(bondToken_);
        }

        IBondToken bondTokenContract =
            IBondToken(bondToken_);

        if (
            bondTokenContract.totalSupply() != 0 ||
            bondTokenContract.controller() != address(0)
        ) {
            revert InvalidBondTokenState();
        }

        admin = admin_;
        issuer = issuer_;
        paymentToken = IERC20(paymentToken_);
        bondToken = bondTokenContract;

        lifecycle = Lifecycle.Draft;
        subscriptionPaused = false;
    }

    // =============================================================
    // MODIFIERS
    // =============================================================

    modifier onlyAdmin() {
        if (msg.sender != admin) {
            revert NotAdmin(msg.sender);
        }
        _;
    }

    modifier onlyIssuer() {
        if (msg.sender != issuer) {
            revert NotIssuer(msg.sender);
        }
        _;
    }

    modifier validCouponPeriod(uint8 period) {
        if (
            period < 1 ||
            period > COUPON_PERIOD_COUNT
        ) {
            revert InvalidCouponPeriod(period);
        }
        _;
    }

    modifier whitelistLifecycleOpen() {
        if (
            lifecycle != Lifecycle.Draft &&
            lifecycle != Lifecycle.SubscriptionOpen
        ) {
            revert InvalidLifecycle(lifecycle);
        }
        _;
    }

    // =============================================================
    // WHITELIST FUNCTIONS
    // =============================================================

    /**
     * @notice Investor tự gửi yêu cầu tham gia whitelist.
     *
     * Admin và issuer không được đăng ký dưới vai trò investor.
     * Một ví bị Rejected hoặc Revoked được phép đăng ký lại.
     */
    function requestWhitelist()
        external
        whitelistLifecycleOpen
    {
        if (
            msg.sender == admin ||
            msg.sender == issuer
        ) {
            revert RoleCannotRegister(msg.sender);
        }

        WhitelistStatus current =
            whitelistStatus[msg.sender];

        if (
            current == WhitelistStatus.Pending ||
            current == WhitelistStatus.Approved
        ) {
            revert InvalidWhitelistStatus(
                msg.sender,
                current
            );
        }

        if (!applicantRecorded[msg.sender]) {
            applicantRecorded[msg.sender] = true;
            whitelistApplicants.push(msg.sender);
        }

        whitelistStatus[msg.sender] =
            WhitelistStatus.Pending;

        whitelisted[msg.sender] = false;
        whitelistRequestedAt[msg.sender] =
            block.timestamp;
        whitelistReviewedAt[msg.sender] = 0;

        emit WhitelistRequested(
            msg.sender,
            block.timestamp
        );
    }

    /**
     * @notice Admin phê duyệt một request đang Pending.
     */
    function approveWhitelist(
        address investor
    )
        external
        onlyAdmin
        whitelistLifecycleOpen
    {
        if (investor == address(0)) {
            revert ZeroAddress();
        }

        WhitelistStatus current =
            whitelistStatus[investor];

        if (current != WhitelistStatus.Pending) {
            revert InvalidWhitelistStatus(
                investor,
                current
            );
        }

        whitelistStatus[investor] =
            WhitelistStatus.Approved;
        whitelisted[investor] = true;
        whitelistReviewedAt[investor] =
            block.timestamp;

        emit WhitelistApproved(
            investor,
            msg.sender,
            block.timestamp
        );

        emit WhitelistUpdated(investor, true);
    }

    /**
     * @notice Admin từ chối một request đang Pending.
     */
    function rejectWhitelist(
        address investor
    )
        external
        onlyAdmin
        whitelistLifecycleOpen
    {
        if (investor == address(0)) {
            revert ZeroAddress();
        }

        WhitelistStatus current =
            whitelistStatus[investor];

        if (current != WhitelistStatus.Pending) {
            revert InvalidWhitelistStatus(
                investor,
                current
            );
        }

        whitelistStatus[investor] =
            WhitelistStatus.Rejected;
        whitelisted[investor] = false;
        whitelistReviewedAt[investor] =
            block.timestamp;

        emit WhitelistRejected(
            investor,
            msg.sender,
            block.timestamp
        );

        emit WhitelistUpdated(investor, false);
    }

    /**
     * @notice Admin thu hồi quyền của investor đã Approved.
     *
     * Việc revoke không làm mất các quyền tài chính đã phát sinh.
     * Investor vẫn có thể refund, claim coupon và redeem principal
     * cho vị thế đã mua trước đó.
     */
    function revokeWhitelist(
        address investor
    )
        external
        onlyAdmin
        whitelistLifecycleOpen
    {
        if (investor == address(0)) {
            revert ZeroAddress();
        }

        WhitelistStatus current =
            whitelistStatus[investor];

        if (current != WhitelistStatus.Approved) {
            revert InvalidWhitelistStatus(
                investor,
                current
            );
        }

        whitelistStatus[investor] =
            WhitelistStatus.Revoked;
        whitelisted[investor] = false;
        whitelistReviewedAt[investor] =
            block.timestamp;

        emit WhitelistRevoked(
            investor,
            msg.sender,
            block.timestamp
        );

        emit WhitelistUpdated(investor, false);
    }

    // =============================================================
    // ADMIN FUNCTIONS
    // =============================================================

    function pauseSubscription()
        external
        onlyAdmin
        whitelistLifecycleOpen
    {
        if (subscriptionPaused) {
            revert AlreadyPaused();
        }

        subscriptionPaused = true;
        emit SubscriptionPaused(block.timestamp);
    }

    function unpauseSubscription()
        external
        onlyAdmin
        whitelistLifecycleOpen
    {
        if (!subscriptionPaused) {
            revert NotPaused();
        }

        subscriptionPaused = false;
        emit SubscriptionUnpaused(block.timestamp);
    }

    // =============================================================
    // ISSUER FUNCTIONS
    // =============================================================

    function openSubscription()
        external
        onlyIssuer
    {
        if (lifecycle != Lifecycle.Draft) {
            revert InvalidLifecycle(lifecycle);
        }

        if (subscriptionPaused) {
            revert SubscriptionIsPaused();
        }

        if (bondToken.controller() != address(this)) {
            revert InvalidBondTokenState();
        }

        subscriptionStart = block.timestamp;
        subscriptionDeadline =
            block.timestamp + SUBSCRIPTION_DURATION;

        lifecycle = Lifecycle.SubscriptionOpen;

        emit SubscriptionOpened(
            subscriptionStart,
            subscriptionDeadline
        );
    }

    // =============================================================
    // INVESTOR FUNCTIONS
    // =============================================================

    function subscribe(
        uint256 quantity
    )
        external
        nonReentrant
    {
        if (lifecycle != Lifecycle.SubscriptionOpen) {
            revert InvalidLifecycle(lifecycle);
        }

        if (subscriptionPaused) {
            revert SubscriptionIsPaused();
        }

        if (!whitelisted[msg.sender]) {
            revert NotWhitelisted(msg.sender);
        }

        if (block.timestamp >= subscriptionDeadline) {
            revert SubscriptionExpired();
        }

        if (quantity == 0) {
            revert ZeroQuantity();
        }

        uint256 remainingSupply =
            MAX_BOND_SUPPLY - totalSubscribed;

        if (quantity > remainingSupply) {
            revert MaxSupplyExceeded(
                quantity,
                remainingSupply
            );
        }

        uint256 payment =
            quantity * ISSUE_PRICE;

        uint256 investorBalance =
            paymentToken.balanceOf(msg.sender);

        if (investorBalance < payment) {
            revert InsufficientTokenBalance(
                payment,
                investorBalance
            );
        }

        uint256 investorAllowance =
            paymentToken.allowance(
                msg.sender,
                address(this)
            );

        if (investorAllowance < payment) {
            revert InsufficientAllowance(
                payment,
                investorAllowance
            );
        }

        subscribedQuantity[msg.sender] += quantity;
        paidAmount[msg.sender] += payment;
        totalSubscribed += quantity;
        totalRaised += payment;

        paymentToken.safeTransferFrom(
            msg.sender,
            address(this),
            payment
        );

        bondToken.mint(
            msg.sender,
            quantity
        );

        emit BondSubscribed(
            msg.sender,
            quantity,
            payment,
            subscribedQuantity[msg.sender],
            totalSubscribed
        );
    }

    // =============================================================
    // PERMISSIONLESS FUNCTIONS
    // =============================================================

    function finalizeOffering() external {
        if (lifecycle != Lifecycle.SubscriptionOpen) {
            revert InvalidLifecycle(lifecycle);
        }

        bool soldOut =
            totalSubscribed == MAX_BOND_SUPPLY;

        bool deadlineReached =
            block.timestamp >= subscriptionDeadline;

        if (!soldOut && !deadlineReached) {
            revert CannotFinalizeYet();
        }

        finalizedAt = block.timestamp;

        bool successful =
            totalSubscribed >= MINIMUM_SUBSCRIPTION;

        if (successful) {
            lifecycle = Lifecycle.Active;

            couponDue[1] =
                finalizedAt + COUPON_1_DELAY;
            couponDue[2] =
                finalizedAt + COUPON_2_DELAY;

            maturity = couponDue[2];

            couponRequired[1] =
                totalSubscribed * COUPON_PER_PERIOD;
            couponRequired[2] =
                totalSubscribed * COUPON_PER_PERIOD;

            principalRequired =
                totalSubscribed * FACE_VALUE;
        } else {
            lifecycle = Lifecycle.Failed;
        }

        emit OfferingFinalized(
            successful,
            lifecycle,
            totalSubscribed,
            totalRaised,
            finalizedAt
        );
    }

    // =============================================================
    // PROCEEDS AND REFUND FUNCTIONS
    // =============================================================

    function withdrawProceeds()
        external
        onlyIssuer
        nonReentrant
    {
        if (
            lifecycle != Lifecycle.Active &&
            lifecycle != Lifecycle.Matured
        ) {
            revert InvalidLifecycle(lifecycle);
        }

        if (proceedsWithdrawn) {
            revert ProceedsAlreadyWithdrawn();
        }

        uint256 amount = totalRaised;
        proceedsWithdrawn = true;

        paymentToken.safeTransfer(
            issuer,
            amount
        );

        emit ProceedsWithdrawn(
            issuer,
            amount
        );
    }

    function claimRefund()
        external
        nonReentrant
    {
        if (lifecycle != Lifecycle.Failed) {
            revert InvalidLifecycle(lifecycle);
        }

        if (refundClaimed[msg.sender]) {
            revert RefundAlreadyClaimed();
        }

        uint256 refundAmount =
            paidAmount[msg.sender];

        uint256 quantity =
            subscribedQuantity[msg.sender];

        if (
            refundAmount == 0 ||
            quantity == 0
        ) {
            revert NothingToRefund();
        }

        refundClaimed[msg.sender] = true;
        totalRefunded += refundAmount;

        bondToken.burn(
            msg.sender,
            quantity
        );

        paymentToken.safeTransfer(
            msg.sender,
            refundAmount
        );

        emit RefundClaimed(
            msg.sender,
            quantity,
            refundAmount
        );
    }

    // =============================================================
    // COUPON FUNCTIONS
    // =============================================================

    function depositCoupon(
        uint8 period
    )
        external
        onlyIssuer
        validCouponPeriod(period)
        nonReentrant
    {
        if (
            lifecycle != Lifecycle.Active &&
            lifecycle != Lifecycle.Matured
        ) {
            revert InvalidLifecycle(lifecycle);
        }

        if (couponFunded[period] != 0) {
            revert CouponAlreadyFunded(period);
        }

        uint256 requiredAmount =
            couponRequired[period];

        uint256 issuerBalance =
            paymentToken.balanceOf(issuer);

        if (issuerBalance < requiredAmount) {
            revert InsufficientTokenBalance(
                requiredAmount,
                issuerBalance
            );
        }

        uint256 issuerAllowance =
            paymentToken.allowance(
                issuer,
                address(this)
            );

        if (issuerAllowance < requiredAmount) {
            revert InsufficientAllowance(
                requiredAmount,
                issuerAllowance
            );
        }

        couponFunded[period] = requiredAmount;

        bool curedDefault =
            couponDefaulted[period];

        if (curedDefault) {
            couponDefaulted[period] = false;
        }

        paymentToken.safeTransferFrom(
            issuer,
            address(this),
            requiredAmount
        );

        emit CouponFunded(
            period,
            requiredAmount,
            block.timestamp
        );

        if (curedDefault) {
            emit DefaultCured(
                1,
                period,
                block.timestamp
            );
        }
    }

    function claimCoupon(
        uint8 period
    )
        external
        validCouponPeriod(period)
        nonReentrant
    {
        if (
            lifecycle != Lifecycle.Active &&
            lifecycle != Lifecycle.Matured
        ) {
            revert InvalidLifecycle(lifecycle);
        }

        if (block.timestamp < couponDue[period]) {
            revert CouponNotDue(period);
        }

        if (
            couponFunded[period] <
            couponRequired[period]
        ) {
            revert CouponNotFunded(period);
        }

        if (couponClaimed[period][msg.sender]) {
            revert CouponAlreadyClaimed(period);
        }

        uint256 quantity =
            bondToken.balanceOf(msg.sender);

        if (quantity == 0) {
            revert ZeroQuantity();
        }

        uint256 couponAmount =
            quantity * COUPON_PER_PERIOD;

        couponClaimed[period][msg.sender] = true;
        couponClaimedTotal[period] += couponAmount;

        paymentToken.safeTransfer(
            msg.sender,
            couponAmount
        );

        emit CouponClaimed(
            period,
            msg.sender,
            quantity,
            couponAmount
        );
    }

    // =============================================================
    // PRINCIPAL AND MATURITY FUNCTIONS
    // =============================================================

    function depositPrincipal()
        external
        onlyIssuer
        nonReentrant
    {
        if (
            lifecycle != Lifecycle.Active &&
            lifecycle != Lifecycle.Matured
        ) {
            revert InvalidLifecycle(lifecycle);
        }

        if (principalFunded != 0) {
            revert PrincipalAlreadyFunded();
        }

        uint256 requiredAmount =
            principalRequired;

        uint256 issuerBalance =
            paymentToken.balanceOf(issuer);

        if (issuerBalance < requiredAmount) {
            revert InsufficientTokenBalance(
                requiredAmount,
                issuerBalance
            );
        }

        uint256 issuerAllowance =
            paymentToken.allowance(
                issuer,
                address(this)
            );

        if (issuerAllowance < requiredAmount) {
            revert InsufficientAllowance(
                requiredAmount,
                issuerAllowance
            );
        }

        principalFunded = requiredAmount;

        bool curedDefault =
            principalDefaulted;

        if (curedDefault) {
            principalDefaulted = false;
        }

        paymentToken.safeTransferFrom(
            issuer,
            address(this),
            requiredAmount
        );

        emit PrincipalFunded(
            requiredAmount,
            block.timestamp
        );

        if (curedDefault) {
            emit DefaultCured(
                2,
                0,
                block.timestamp
            );
        }
    }

    function markMatured() external {
        if (lifecycle != Lifecycle.Active) {
            revert InvalidLifecycle(lifecycle);
        }

        if (block.timestamp < maturity) {
            revert NotMatured();
        }

        _syncMaturity();
    }

    function redeemPrincipal()
        external
        nonReentrant
    {
        if (
            lifecycle != Lifecycle.Active &&
            lifecycle != Lifecycle.Matured
        ) {
            revert InvalidLifecycle(lifecycle);
        }

        _syncMaturity();

        if (lifecycle != Lifecycle.Matured) {
            revert NotMatured();
        }

        if (
            principalFunded <
            principalRequired
        ) {
            revert PrincipalNotFunded();
        }

        if (principalRedeemed[msg.sender]) {
            revert PrincipalAlreadyRedeemed();
        }

        uint256 quantity =
            bondToken.balanceOf(msg.sender);

        if (quantity == 0) {
            revert ZeroQuantity();
        }

        if (
            !couponClaimed[1][msg.sender] ||
            !couponClaimed[2][msg.sender]
        ) {
            revert CouponsNotFullyClaimed();
        }

        uint256 principalAmount =
            quantity * FACE_VALUE;

        principalRedeemed[msg.sender] = true;
        principalRedeemedTotal += principalAmount;

        bondToken.burn(
            msg.sender,
            quantity
        );

        paymentToken.safeTransfer(
            msg.sender,
            principalAmount
        );

        emit PrincipalRedeemed(
            msg.sender,
            quantity,
            principalAmount
        );
    }

    // =============================================================
    // DEFAULT AND CLOSING FUNCTIONS
    // =============================================================

    function markCouponDefault(
        uint8 period
    )
        external
        validCouponPeriod(period)
    {
        if (
            lifecycle != Lifecycle.Active &&
            lifecycle != Lifecycle.Matured
        ) {
            revert InvalidLifecycle(lifecycle);
        }

        if (couponDefaulted[period]) {
            revert DefaultAlreadyRecorded();
        }

        bool gracePeriodExpired =
            block.timestamp >=
            couponDue[period] + GRACE_PERIOD;

        bool obligationUnfunded =
            couponFunded[period] <
            couponRequired[period];

        if (
            !gracePeriodExpired ||
            !obligationUnfunded
        ) {
            revert DefaultNotEligible();
        }

        couponDefaulted[period] = true;
        couponDefaultedAt[period] =
            block.timestamp;

        emit CouponDefaultRecorded(
            period,
            block.timestamp
        );
    }

    function markPrincipalDefault() external {
        if (
            lifecycle != Lifecycle.Active &&
            lifecycle != Lifecycle.Matured
        ) {
            revert InvalidLifecycle(lifecycle);
        }

        if (principalDefaulted) {
            revert DefaultAlreadyRecorded();
        }

        bool gracePeriodExpired =
            block.timestamp >=
            maturity + GRACE_PERIOD;

        bool obligationUnfunded =
            principalFunded <
            principalRequired;

        if (
            !gracePeriodExpired ||
            !obligationUnfunded
        ) {
            revert DefaultNotEligible();
        }

        _syncMaturity();

        principalDefaulted = true;
        principalDefaultedAt =
            block.timestamp;

        emit PrincipalDefaultRecorded(
            block.timestamp
        );
    }

    function closeBond() external {
        if (lifecycle == Lifecycle.Closed) {
            revert AlreadyClosed();
        }

        Lifecycle previousLifecycle =
            lifecycle;

        uint256 outstandingBondSupply =
            bondToken.totalSupply();

        bool failedOfferingCanClose =
            lifecycle == Lifecycle.Failed &&
            totalRefunded == totalRaised &&
            outstandingBondSupply == 0;

        bool successfulOfferingCanClose =
            lifecycle == Lifecycle.Matured &&
            proceedsWithdrawn &&
            principalRedeemedTotal ==
                principalRequired &&
            outstandingBondSupply == 0;

        if (
            !failedOfferingCanClose &&
            !successfulOfferingCanClose
        ) {
            revert CloseConditionsNotMet();
        }

        lifecycle = Lifecycle.Closed;

        emit BondClosed(
            previousLifecycle,
            block.timestamp
        );
    }

    // =============================================================
    // VIEW FUNCTIONS
    // =============================================================

    function getBondInfo()
        external
        view
        returns (BondInfo memory)
    {
        return BondInfo({
            bondName: BOND_NAME,
            adminAddress: admin,
            issuerAddress: issuer,
            paymentTokenAddress: address(paymentToken),
            bondTokenAddress: address(bondToken),
            faceValue: FACE_VALUE,
            issuePrice: ISSUE_PRICE,
            maxSupply: MAX_BOND_SUPPLY,
            minimumSubscription:
                MINIMUM_SUBSCRIPTION,
            annualCouponRateBps:
                ANNUAL_COUPON_RATE_BPS,
            couponPerPeriod: COUPON_PER_PERIOD,
            gracePeriod: GRACE_PERIOD
        });
    }

    function getOfferingInfo()
        external
        view
        returns (OfferingInfo memory)
    {
        return OfferingInfo({
            currentLifecycle: lifecycle,
            paused: subscriptionPaused,
            start: subscriptionStart,
            deadline: subscriptionDeadline,
            finalizedTime: finalizedAt,
            subscribed: totalSubscribed,
            raised: totalRaised,
            refunded: totalRefunded,
            proceedsAreWithdrawn:
                proceedsWithdrawn
        });
    }

    function getInvestorPosition(
        address investor
    )
        external
        view
        returns (InvestorPosition memory)
    {
        uint256 claimableCouponTotal =
            getClaimableCoupon(investor, 1) +
            getClaimableCoupon(investor, 2);

        return InvestorPosition({
            isWhitelisted: whitelisted[investor],
            quantitySubscribed:
                subscribedQuantity[investor],
            amountPaid: paidAmount[investor],
            bondBalance:
                bondToken.balanceOf(investor),
            hasClaimedRefund:
                refundClaimed[investor],
            hasClaimedCoupon1:
                couponClaimed[1][investor],
            hasClaimedCoupon2:
                couponClaimed[2][investor],
            hasRedeemedPrincipal:
                principalRedeemed[investor],
            refundableAmount:
                getRefundAmount(investor),
            claimableCouponTotal:
                claimableCouponTotal,
            redeemablePrincipal:
                getPrincipalAmount(investor)
        });
    }

    function getCouponInfo(
        uint8 period
    )
        external
        view
        validCouponPeriod(period)
        returns (CouponInfo memory)
    {
        return CouponInfo({
            dueDate: couponDue[period],
            requiredAmount:
                couponRequired[period],
            fundedAmount:
                couponFunded[period],
            claimedAmount:
                couponClaimedTotal[period],
            isInDefault:
                couponDefaulted[period],
            defaultTimestamp:
                couponDefaultedAt[period]
        });
    }

    function getPrincipalInfo()
        external
        view
        returns (PrincipalInfo memory)
    {
        return PrincipalInfo({
            maturityDate: maturity,
            requiredAmount: principalRequired,
            fundedAmount: principalFunded,
            redeemedAmount:
                principalRedeemedTotal,
            isInDefault: principalDefaulted,
            defaultTimestamp:
                principalDefaultedAt
        });
    }

    function getWhitelistApplicantCount()
        external
        view
        returns (uint256)
    {
        return whitelistApplicants.length;
    }

    function getWhitelistApplicantAt(
        uint256 index
    )
        external
        view
        returns (address)
    {
        if (index >= whitelistApplicants.length) {
            revert ApplicantIndexOutOfBounds(index);
        }

        return whitelistApplicants[index];
    }

    function getWhitelistStatus(
        address investor
    )
        external
        view
        returns (WhitelistStatus)
    {
        return whitelistStatus[investor];
    }

    function getWhitelistInfo(
        address investor
    )
        external
        view
        returns (WhitelistInfo memory)
    {
        return WhitelistInfo({
            status: whitelistStatus[investor],
            isWhitelisted: whitelisted[investor],
            requestedAt:
                whitelistRequestedAt[investor],
            reviewedAt:
                whitelistReviewedAt[investor]
        });
    }

    // =============================================================
    // VIEW HELPERS
    // =============================================================

    function getClaimableCoupon(
        address investor,
        uint8 period
    )
        public
        view
        validCouponPeriod(period)
        returns (uint256)
    {
        bool validLifecycle =
            lifecycle == Lifecycle.Active ||
            lifecycle == Lifecycle.Matured;

        if (!validLifecycle) {
            return 0;
        }

        if (block.timestamp < couponDue[period]) {
            return 0;
        }

        if (
            couponFunded[period] <
            couponRequired[period]
        ) {
            return 0;
        }

        if (couponClaimed[period][investor]) {
            return 0;
        }

        uint256 quantity =
            bondToken.balanceOf(investor);

        if (quantity == 0) {
            return 0;
        }

        return quantity * COUPON_PER_PERIOD;
    }

    function getRefundAmount(
        address investor
    )
        public
        view
        returns (uint256)
    {
        if (lifecycle != Lifecycle.Failed) {
            return 0;
        }

        if (refundClaimed[investor]) {
            return 0;
        }

        return paidAmount[investor];
    }

    function getPrincipalAmount(
        address investor
    )
        public
        view
        returns (uint256)
    {
        bool validLifecycle =
            lifecycle == Lifecycle.Active ||
            lifecycle == Lifecycle.Matured;

        if (!validLifecycle) {
            return 0;
        }

        if (block.timestamp < maturity) {
            return 0;
        }

        if (
            principalFunded <
            principalRequired
        ) {
            return 0;
        }

        if (principalRedeemed[investor]) {
            return 0;
        }

        if (
            !couponClaimed[1][investor] ||
            !couponClaimed[2][investor]
        ) {
            return 0;
        }

        uint256 quantity =
            bondToken.balanceOf(investor);

        if (quantity == 0) {
            return 0;
        }

        return quantity * FACE_VALUE;
    }

    function isSubscriptionOpen()
        public
        view
        returns (bool)
    {
        return
            lifecycle ==
                Lifecycle.SubscriptionOpen &&
            !subscriptionPaused &&
            block.timestamp <
                subscriptionDeadline &&
            totalSubscribed <
                MAX_BOND_SUPPLY;
    }

    function isDefaulted()
        public
        view
        returns (bool)
    {
        return
            couponDefaulted[1] ||
            couponDefaulted[2] ||
            principalDefaulted;
    }

    function canFinalize()
        public
        view
        returns (bool)
    {
        if (
            lifecycle !=
            Lifecycle.SubscriptionOpen
        ) {
            return false;
        }

        bool soldOut =
            totalSubscribed ==
            MAX_BOND_SUPPLY;

        bool deadlineReached =
            block.timestamp >=
            subscriptionDeadline;

        return soldOut || deadlineReached;
    }

    function canClose()
        public
        view
        returns (bool)
    {
        uint256 outstandingBondSupply =
            bondToken.totalSupply();

        if (lifecycle == Lifecycle.Failed) {
            return
                totalRefunded == totalRaised &&
                outstandingBondSupply == 0;
        }

        if (lifecycle == Lifecycle.Matured) {
            return
                proceedsWithdrawn &&
                principalRedeemedTotal ==
                    principalRequired &&
                outstandingBondSupply == 0;
        }

        return false;
    }

    // =============================================================
    // INTERNAL FUNCTIONS
    // =============================================================

    function _syncMaturity() internal {
        if (
            lifecycle == Lifecycle.Active &&
            block.timestamp >= maturity
        ) {
            lifecycle = Lifecycle.Matured;

            emit BondMatured(
                maturity,
                block.timestamp
            );
        }
    }

    // =============================================================
    // NATIVE TOKEN RESTRICTION
    // =============================================================

    receive() external payable {
        revert NativeTokenNotAccepted();
    }
}
