const { expect } = require("chai");
const {
    loadFixture,
    time,
} = require("@nomicfoundation/hardhat-network-helpers");
const { ethers } = require("hardhat");

describe("TokenizedBond", function () {
    const FACE_VALUE = ethers.parseEther("100");
    const ISSUE_PRICE = ethers.parseEther("100");
    const COUPON_PER_PERIOD = ethers.parseEther("5");
    const MAX_SUPPLY = 100n;
    const MIN_SUBSCRIPTION = 60n;

    const INVESTOR_BALANCE = ethers.parseEther("20000");
    const ISSUER_BALANCE = ethers.parseEther("30000");

    const Lifecycle = {
        Draft: 0n,
        SubscriptionOpen: 1n,
        Failed: 2n,
        Active: 3n,
        Matured: 4n,
        Closed: 5n,
    };

    const WhitelistStatus = {
        None: 0n,
        Pending: 1n,
        Approved: 2n,
        Rejected: 3n,
        Revoked: 4n,
    };

    async function deployFixture() {
        const [
            deployer,
            admin,
            issuer,
            investor1,
            investor2,
            outsider,
        ] = await ethers.getSigners();

        const MockBondUSD =
            await ethers.getContractFactory("MockBondUSD");

        const paymentToken =
            await MockBondUSD
                .connect(deployer)
                .deploy(deployer.address);

        await paymentToken.waitForDeployment();

        const BondToken =
            await ethers.getContractFactory("BondToken");

        const bondToken =
            await BondToken
                .connect(deployer)
                .deploy(deployer.address);

        await bondToken.waitForDeployment();

        const TokenizedBond =
            await ethers.getContractFactory("TokenizedBond");

        const tokenizedBond =
            await TokenizedBond
                .connect(deployer)
                .deploy(
                    admin.address,
                    issuer.address,
                    await paymentToken.getAddress(),
                    await bondToken.getAddress()
                );

        await tokenizedBond.waitForDeployment();

        await (
            await bondToken
                .connect(deployer)
                .setController(
                    await tokenizedBond.getAddress()
                )
        ).wait();

        await (
            await bondToken
                .connect(deployer)
                .renounceOwnership()
        ).wait();

        await (
            await paymentToken
                .connect(deployer)
                .mint(
                    investor1.address,
                    INVESTOR_BALANCE
                )
        ).wait();

        await (
            await paymentToken
                .connect(deployer)
                .mint(
                    investor2.address,
                    INVESTOR_BALANCE
                )
        ).wait();

        await (
            await paymentToken
                .connect(deployer)
                .mint(
                    issuer.address,
                    ISSUER_BALANCE
                )
        ).wait();

        return {
            deployer,
            admin,
            issuer,
            investor1,
            investor2,
            outsider,
            paymentToken,
            bondToken,
            tokenizedBond,
        };
    }

    async function approveInvestor(
        context,
        investor
    ) {
        const {
            admin,
            tokenizedBond,
        } = context;

        await tokenizedBond
            .connect(investor)
            .requestWhitelist();

        await tokenizedBond
            .connect(admin)
            .approveWhitelist(
                investor.address
            );
    }

    async function openOffering(
        context,
        investors
    ) {
        const {
            issuer,
            tokenizedBond,
        } = context;

        for (const investor of investors) {
            await approveInvestor(
                context,
                investor
            );
        }

        await tokenizedBond
            .connect(issuer)
            .openSubscription();
    }

    async function subscribe(
        context,
        investor,
        quantity
    ) {
        const {
            paymentToken,
            tokenizedBond,
        } = context;

        const payment =
            quantity * ISSUE_PRICE;

        await paymentToken
            .connect(investor)
            .approve(
                await tokenizedBond.getAddress(),
                payment
            );

        await tokenizedBond
            .connect(investor)
            .subscribe(quantity);
    }

    async function prepareOffering(
        context,
        subscriptions
    ) {
        await openOffering(
            context,
            subscriptions.map(
                ([investor]) => investor
            )
        );

        for (
            const [
                investor,
                quantity,
            ] of subscriptions
        ) {
            await subscribe(
                context,
                investor,
                quantity
            );
        }
    }

    async function moveToDeadline(
        tokenizedBond
    ) {
        await time.increaseTo(
            await tokenizedBond
                .subscriptionDeadline()
        );
    }

    async function prepareActiveOffering(
        context
    ) {
        const {
            issuer,
            investor1,
            investor2,
            tokenizedBond,
        } = context;

        const quantity1 = 30n;
        const quantity2 = 40n;
        const total =
            quantity1 + quantity2;

        await prepareOffering(
            context,
            [
                [investor1, quantity1],
                [investor2, quantity2],
            ]
        );

        await moveToDeadline(
            tokenizedBond
        );

        await tokenizedBond
            .finalizeOffering();

        await tokenizedBond
            .connect(issuer)
            .withdrawProceeds();

        return {
            quantity1,
            quantity2,
            total,
            couponRequired:
                total * COUPON_PER_PERIOD,
            principalRequired:
                total * FACE_VALUE,
        };
    }

    async function fundCoupon(
        context,
        period,
        amount
    ) {
        const {
            issuer,
            paymentToken,
            tokenizedBond,
        } = context;

        await paymentToken
            .connect(issuer)
            .approve(
                await tokenizedBond.getAddress(),
                amount
            );

        await tokenizedBond
            .connect(issuer)
            .depositCoupon(period);
    }

    async function fundPrincipal(
        context,
        amount
    ) {
        const {
            issuer,
            paymentToken,
            tokenizedBond,
        } = context;

        await paymentToken
            .connect(issuer)
            .approve(
                await tokenizedBond.getAddress(),
                amount
            );

        await tokenizedBond
            .connect(issuer)
            .depositPrincipal();
    }

    describe("Deployment", function () {
        it("stores roles and starts from a clean Draft state", async function () {
            const {
                admin,
                issuer,
                investor1,
                tokenizedBond,
            } = await loadFixture(
                deployFixture
            );

            expect(
                await tokenizedBond.admin()
            ).to.equal(admin.address);

            expect(
                await tokenizedBond.issuer()
            ).to.equal(issuer.address);

            expect(
                await tokenizedBond.lifecycle()
            ).to.equal(Lifecycle.Draft);

            expect(
                await tokenizedBond
                    .getWhitelistApplicantCount()
            ).to.equal(0n);

            expect(
                await tokenizedBond
                    .getWhitelistStatus(
                        investor1.address
                    )
            ).to.equal(
                WhitelistStatus.None
            );

            expect(
                await tokenizedBond
                    .whitelisted(
                        investor1.address
                    )
            ).to.equal(false);
        });

        it("stores economic constants and controller correctly", async function () {
            const {
                bondToken,
                tokenizedBond,
            } = await loadFixture(
                deployFixture
            );

            expect(
                await tokenizedBond.FACE_VALUE()
            ).to.equal(FACE_VALUE);

            expect(
                await tokenizedBond.ISSUE_PRICE()
            ).to.equal(ISSUE_PRICE);

            expect(
                await tokenizedBond
                    .MAX_BOND_SUPPLY()
            ).to.equal(MAX_SUPPLY);

            expect(
                await tokenizedBond
                    .MINIMUM_SUBSCRIPTION()
            ).to.equal(
                MIN_SUBSCRIPTION
            );

            expect(
                await bondToken.controller()
            ).to.equal(
                await tokenizedBond.getAddress()
            );

            expect(
                await bondToken.owner()
            ).to.equal(
                ethers.ZeroAddress
            );
        });
    });

    describe(
        "Whitelist self-registration",
        function () {
            it("records an investor request as Pending", async function () {
                const {
                    investor1,
                    tokenizedBond,
                } = await loadFixture(
                    deployFixture
                );

                await expect(
                    tokenizedBond
                        .connect(investor1)
                        .requestWhitelist()
                ).to.emit(
                    tokenizedBond,
                    "WhitelistRequested"
                );

                expect(
                    await tokenizedBond
                        .getWhitelistStatus(
                            investor1.address
                        )
                ).to.equal(
                    WhitelistStatus.Pending
                );

                expect(
                    await tokenizedBond
                        .getWhitelistApplicantCount()
                ).to.equal(1n);

                expect(
                    await tokenizedBond
                        .getWhitelistApplicantAt(0)
                ).to.equal(
                    investor1.address
                );

                const info =
                    await tokenizedBond
                        .getWhitelistInfo(
                            investor1.address
                        );

                expect(
                    info.isWhitelisted
                ).to.equal(false);

                expect(
                    info.requestedAt
                ).to.be.greaterThan(0n);

                expect(
                    info.reviewedAt
                ).to.equal(0n);
            });

            it("rejects duplicate Pending requests", async function () {
                const {
                    investor1,
                    tokenizedBond,
                } = await loadFixture(
                    deployFixture
                );

                await tokenizedBond
                    .connect(investor1)
                    .requestWhitelist();

                await expect(
                    tokenizedBond
                        .connect(investor1)
                        .requestWhitelist()
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "InvalidWhitelistStatus"
                    )
                    .withArgs(
                        investor1.address,
                        WhitelistStatus.Pending
                    );
            });

            it("prevents admin and issuer from registering as investors", async function () {
                const {
                    admin,
                    issuer,
                    tokenizedBond,
                } = await loadFixture(
                    deployFixture
                );

                await expect(
                    tokenizedBond
                        .connect(admin)
                        .requestWhitelist()
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "RoleCannotRegister"
                    )
                    .withArgs(admin.address);

                await expect(
                    tokenizedBond
                        .connect(issuer)
                        .requestWhitelist()
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "RoleCannotRegister"
                    )
                    .withArgs(issuer.address);
            });

            it("allows admin to approve a Pending request", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    admin,
                    investor1,
                    tokenizedBond,
                } = context;

                await tokenizedBond
                    .connect(investor1)
                    .requestWhitelist();

                await expect(
                    tokenizedBond
                        .connect(admin)
                        .approveWhitelist(
                            investor1.address
                        )
                ).to.emit(
                    tokenizedBond,
                    "WhitelistApproved"
                );

                expect(
                    await tokenizedBond
                        .getWhitelistStatus(
                            investor1.address
                        )
                ).to.equal(
                    WhitelistStatus.Approved
                );

                expect(
                    await tokenizedBond
                        .whitelisted(
                            investor1.address
                        )
                ).to.equal(true);
            });

            it("allows rejection, re-request and approval without duplicating the applicant", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    admin,
                    investor1,
                    tokenizedBond,
                } = context;

                await tokenizedBond
                    .connect(investor1)
                    .requestWhitelist();

                await tokenizedBond
                    .connect(admin)
                    .rejectWhitelist(
                        investor1.address
                    );

                expect(
                    await tokenizedBond
                        .getWhitelistStatus(
                            investor1.address
                        )
                ).to.equal(
                    WhitelistStatus.Rejected
                );

                await tokenizedBond
                    .connect(investor1)
                    .requestWhitelist();

                await tokenizedBond
                    .connect(admin)
                    .approveWhitelist(
                        investor1.address
                    );

                expect(
                    await tokenizedBond
                        .getWhitelistApplicantCount()
                ).to.equal(1n);

                expect(
                    await tokenizedBond
                        .whitelisted(
                            investor1.address
                        )
                ).to.equal(true);
            });

            it("allows revocation and a new request", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    admin,
                    investor1,
                    tokenizedBond,
                } = context;

                await approveInvestor(
                    context,
                    investor1
                );

                await expect(
                    tokenizedBond
                        .connect(admin)
                        .revokeWhitelist(
                            investor1.address
                        )
                ).to.emit(
                    tokenizedBond,
                    "WhitelistRevoked"
                );

                expect(
                    await tokenizedBond
                        .getWhitelistStatus(
                            investor1.address
                        )
                ).to.equal(
                    WhitelistStatus.Revoked
                );

                await tokenizedBond
                    .connect(investor1)
                    .requestWhitelist();

                expect(
                    await tokenizedBond
                        .getWhitelistStatus(
                            investor1.address
                        )
                ).to.equal(
                    WhitelistStatus.Pending
                );
            });

            it("rejects decisions by non-admin accounts", async function () {
                const {
                    issuer,
                    investor1,
                    tokenizedBond,
                } = await loadFixture(
                    deployFixture
                );

                await tokenizedBond
                    .connect(investor1)
                    .requestWhitelist();

                await expect(
                    tokenizedBond
                        .connect(issuer)
                        .approveWhitelist(
                            investor1.address
                        )
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "NotAdmin"
                    )
                    .withArgs(issuer.address);
            });

            it("rejects invalid decision states and applicant indexes", async function () {
                const {
                    admin,
                    investor1,
                    tokenizedBond,
                } = await loadFixture(
                    deployFixture
                );

                await expect(
                    tokenizedBond
                        .connect(admin)
                        .approveWhitelist(
                            investor1.address
                        )
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "InvalidWhitelistStatus"
                    )
                    .withArgs(
                        investor1.address,
                        WhitelistStatus.None
                    );

                await expect(
                    tokenizedBond
                        .getWhitelistApplicantAt(0)
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "ApplicantIndexOutOfBounds"
                    )
                    .withArgs(0n);
            });
        }
    );

    describe(
        "Opening and subscription",
        function () {
            it("allows issuer to open and admin to pause or unpause", async function () {
                const {
                    admin,
                    issuer,
                    tokenizedBond,
                } = await loadFixture(
                    deployFixture
                );

                await tokenizedBond
                    .connect(admin)
                    .pauseSubscription();

                await expect(
                    tokenizedBond
                        .connect(issuer)
                        .openSubscription()
                ).to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "SubscriptionIsPaused"
                    );

                await tokenizedBond
                    .connect(admin)
                    .unpauseSubscription();

                await tokenizedBond
                    .connect(issuer)
                    .openSubscription();

                expect(
                    await tokenizedBond.lifecycle()
                ).to.equal(
                    Lifecycle.SubscriptionOpen
                );
            });

            it("allows an Approved investor to subscribe", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    paymentToken,
                    bondToken,
                    tokenizedBond,
                } = context;

                await openOffering(
                    context,
                    [investor1]
                );

                const quantity = 10n;
                const payment =
                    quantity * ISSUE_PRICE;

                const before =
                    await paymentToken.balanceOf(
                        investor1.address
                    );

                await expect(
                    paymentToken
                        .connect(investor1)
                        .approve(
                            await tokenizedBond
                                .getAddress(),
                            payment
                        )
                ).to.emit(
                    paymentToken,
                    "Approval"
                );

                await expect(
                    tokenizedBond
                        .connect(investor1)
                        .subscribe(quantity)
                )
                    .to.emit(
                        tokenizedBond,
                        "BondSubscribed"
                    )
                    .withArgs(
                        investor1.address,
                        quantity,
                        payment,
                        quantity,
                        quantity
                    );

                expect(
                    await bondToken.balanceOf(
                        investor1.address
                    )
                ).to.equal(quantity);

                expect(
                    await paymentToken.balanceOf(
                        investor1.address
                    )
                ).to.equal(
                    before - payment
                );
            });

            it("rejects Pending, Rejected and Revoked investors", async function () {
                const {
                    admin,
                    issuer,
                    investor1,
                    investor2,
                    outsider,
                    tokenizedBond,
                } = await loadFixture(
                    deployFixture
                );

                await tokenizedBond
                    .connect(investor1)
                    .requestWhitelist();

                await tokenizedBond
                    .connect(investor2)
                    .requestWhitelist();

                await tokenizedBond
                    .connect(admin)
                    .rejectWhitelist(
                        investor2.address
                    );

                await tokenizedBond
                    .connect(outsider)
                    .requestWhitelist();

                await tokenizedBond
                    .connect(admin)
                    .approveWhitelist(
                        outsider.address
                    );

                await tokenizedBond
                    .connect(admin)
                    .revokeWhitelist(
                        outsider.address
                    );

                await tokenizedBond
                    .connect(issuer)
                    .openSubscription();

                for (
                    const investor of [
                        investor1,
                        investor2,
                        outsider,
                    ]
                ) {
                    await expect(
                        tokenizedBond
                            .connect(investor)
                            .subscribe(1n)
                    )
                        .to.be
                        .revertedWithCustomError(
                            tokenizedBond,
                            "NotWhitelisted"
                        )
                        .withArgs(
                            investor.address
                        );
                }
            });

            it("rejects zero quantity, insufficient allowance and insufficient balance", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    outsider,
                    tokenizedBond,
                } = context;

                await openOffering(
                    context,
                    [
                        investor1,
                        outsider,
                    ]
                );

                await expect(
                    tokenizedBond
                        .connect(investor1)
                        .subscribe(0n)
                ).to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "ZeroQuantity"
                    );

                await expect(
                    tokenizedBond
                        .connect(investor1)
                        .subscribe(1n)
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "InsufficientAllowance"
                    )
                    .withArgs(
                        ISSUE_PRICE,
                        0n
                    );

                await expect(
                    tokenizedBond
                        .connect(outsider)
                        .subscribe(1n)
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "InsufficientTokenBalance"
                    )
                    .withArgs(
                        ISSUE_PRICE,
                        0n
                    );
            });

            it("rejects supply overflow and subscriptions after deadline", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    investor2,
                    paymentToken,
                    tokenizedBond,
                } = context;

                await openOffering(
                    context,
                    [
                        investor1,
                        investor2,
                    ]
                );

                await subscribe(
                    context,
                    investor1,
                    90n
                );

                await paymentToken
                    .connect(investor2)
                    .approve(
                        await tokenizedBond
                            .getAddress(),
                        11n * ISSUE_PRICE
                    );

                await expect(
                    tokenizedBond
                        .connect(investor2)
                        .subscribe(11n)
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "MaxSupplyExceeded"
                    )
                    .withArgs(
                        11n,
                        10n
                    );

                await moveToDeadline(
                    tokenizedBond
                );

                await expect(
                    tokenizedBond
                        .connect(investor2)
                        .subscribe(1n)
                ).to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "SubscriptionExpired"
                    );
            });

            it("revocation blocks new purchases but preserves an existing position", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    admin,
                    investor1,
                    bondToken,
                    tokenizedBond,
                } = context;

                await openOffering(
                    context,
                    [investor1]
                );

                await subscribe(
                    context,
                    investor1,
                    10n
                );

                await tokenizedBond
                    .connect(admin)
                    .revokeWhitelist(
                        investor1.address
                    );

                await expect(
                    tokenizedBond
                        .connect(investor1)
                        .subscribe(1n)
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "NotWhitelisted"
                    )
                    .withArgs(
                        investor1.address
                    );

                expect(
                    await bondToken.balanceOf(
                        investor1.address
                    )
                ).to.equal(10n);
            });
        }
    );

    describe(
        "Finalization and refunds",
        function () {
            it("finalizes as Active when the minimum is reached", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    tokenizedBond,
                } = context;

                await prepareOffering(
                    context,
                    [[
                        investor1,
                        MIN_SUBSCRIPTION,
                    ]]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                expect(
                    await tokenizedBond.lifecycle()
                ).to.equal(
                    Lifecycle.Active
                );

                expect(
                    await tokenizedBond
                        .couponRequired(1)
                ).to.equal(
                    MIN_SUBSCRIPTION *
                    COUPON_PER_PERIOD
                );

                expect(
                    await tokenizedBond
                        .principalRequired()
                ).to.equal(
                    MIN_SUBSCRIPTION *
                    FACE_VALUE
                );
            });

            it("finalizes as Failed and refunds investors", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    paymentToken,
                    bondToken,
                    tokenizedBond,
                } = context;

                await prepareOffering(
                    context,
                    [[investor1, 20n]]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                expect(
                    await tokenizedBond.lifecycle()
                ).to.equal(
                    Lifecycle.Failed
                );

                await tokenizedBond
                    .connect(investor1)
                    .claimRefund();

                expect(
                    await paymentToken.balanceOf(
                        investor1.address
                    )
                ).to.equal(
                    INVESTOR_BALANCE
                );

                expect(
                    await bondToken.balanceOf(
                        investor1.address
                    )
                ).to.equal(0n);
            });

            it("preserves refund rights after revocation and closes the failed bond", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    admin,
                    investor1,
                    tokenizedBond,
                } = context;

                await prepareOffering(
                    context,
                    [[investor1, 20n]]
                );

                await tokenizedBond
                    .connect(admin)
                    .revokeWhitelist(
                        investor1.address
                    );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                await tokenizedBond
                    .connect(investor1)
                    .claimRefund();

                expect(
                    await tokenizedBond.canClose()
                ).to.equal(true);

                await tokenizedBond
                    .closeBond();

                expect(
                    await tokenizedBond.lifecycle()
                ).to.equal(
                    Lifecycle.Closed
                );
            });
        }
    );

    describe(
        "Coupon, principal, default and closing",
        function () {
            it("completes the successful lifecycle", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    investor2,
                    bondToken,
                    tokenizedBond,
                } = context;

                const {
                    couponRequired,
                    principalRequired,
                } = await prepareActiveOffering(
                    context
                );

                await fundCoupon(
                    context,
                    1,
                    couponRequired
                );

                await fundCoupon(
                    context,
                    2,
                    couponRequired
                );

                await fundPrincipal(
                    context,
                    principalRequired
                );

                await time.increaseTo(
                    await tokenizedBond
                        .couponDue(1)
                );

                await tokenizedBond
                    .connect(investor1)
                    .claimCoupon(1);

                await tokenizedBond
                    .connect(investor2)
                    .claimCoupon(1);

                await time.increaseTo(
                    await tokenizedBond
                        .maturity()
                );

                await tokenizedBond
                    .connect(investor1)
                    .claimCoupon(2);

                await tokenizedBond
                    .connect(investor2)
                    .claimCoupon(2);

                await tokenizedBond
                    .markMatured();

                await tokenizedBond
                    .connect(investor1)
                    .redeemPrincipal();

                await tokenizedBond
                    .connect(investor2)
                    .redeemPrincipal();

                expect(
                    await bondToken.totalSupply()
                ).to.equal(0n);

                expect(
                    await tokenizedBond.canClose()
                ).to.equal(true);

                await tokenizedBond
                    .closeBond();

                expect(
                    await tokenizedBond.lifecycle()
                ).to.equal(
                    Lifecycle.Closed
                );
            });

            it("records and cures coupon default", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    tokenizedBond,
                } = context;

                const {
                    couponRequired,
                } = await prepareActiveOffering(
                    context
                );

                const due =
                    await tokenizedBond
                        .couponDue(1);

                const grace =
                    await tokenizedBond
                        .GRACE_PERIOD();

                await time.increaseTo(
                    due + grace
                );

                await tokenizedBond
                    .markCouponDefault(1);

                expect(
                    await tokenizedBond
                        .isDefaulted()
                ).to.equal(true);

                await fundCoupon(
                    context,
                    1,
                    couponRequired
                );

                expect(
                    await tokenizedBond
                        .isDefaulted()
                ).to.equal(false);
            });

            it("records and cures principal default", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    tokenizedBond,
                } = context;

                const {
                    principalRequired,
                } = await prepareActiveOffering(
                    context
                );

                const maturity =
                    await tokenizedBond
                        .maturity();

                const grace =
                    await tokenizedBond
                        .GRACE_PERIOD();

                await time.increaseTo(
                    maturity + grace
                );

                await tokenizedBond
                    .markPrincipalDefault();

                expect(
                    await tokenizedBond
                        .principalDefaulted()
                ).to.equal(true);

                expect(
                    await tokenizedBond.lifecycle()
                ).to.equal(
                    Lifecycle.Matured
                );

                await fundPrincipal(
                    context,
                    principalRequired
                );

                expect(
                    await tokenizedBond
                        .principalDefaulted()
                ).to.equal(false);
            });

            it("rejects direct ETH transfers", async function () {
                const {
                    outsider,
                    tokenizedBond,
                } = await loadFixture(
                    deployFixture
                );

                await expect(
                    outsider.sendTransaction({
                        to:
                            await tokenizedBond
                                .getAddress(),
                        value:
                            ethers.parseEther(
                                "0.01"
                            ),
                    })
                ).to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "NativeTokenNotAccepted"
                    );
            });
        }
    );
});
