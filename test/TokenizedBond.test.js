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

    const MAX_BOND_SUPPLY = 100n;
    const MINIMUM_SUBSCRIPTION = 60n;

    const INVESTOR_INITIAL_BALANCE =
        ethers.parseEther("20000");

    const ISSUER_INITIAL_BALANCE =
        ethers.parseEther("30000");

    async function deployFixture() {
        const [
            deployer,
            admin,
            issuer,
            investor1,
            investor2,
            outsider,
        ] = await ethers.getSigners();

        // Deploy MockBondUSD
        const MockBondUSD =
            await ethers.getContractFactory(
                "MockBondUSD"
            );

        const paymentToken =
            await MockBondUSD
                .connect(deployer)
                .deploy(deployer.address);

        await paymentToken.waitForDeployment();

        // Deploy BondToken
        const BondToken =
            await ethers.getContractFactory(
                "BondToken"
            );

        const bondToken =
            await BondToken
                .connect(deployer)
                .deploy(deployer.address);

        await bondToken.waitForDeployment();

        // Deploy TokenizedBond
        const TokenizedBond =
            await ethers.getContractFactory(
                "TokenizedBond"
            );

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

        // Set TokenizedBond as BondToken controller
        await (
            await bondToken
                .connect(deployer)
                .setController(
                    await tokenizedBond.getAddress()
                )
        ).wait();

        // Permanently remove BondToken owner
        await (
            await bondToken
                .connect(deployer)
                .renounceOwnership()
        ).wait();

        // Fund demo accounts
        await (
            await paymentToken
                .connect(deployer)
                .mint(
                    investor1.address,
                    INVESTOR_INITIAL_BALANCE
                )
        ).wait();

        await (
            await paymentToken
                .connect(deployer)
                .mint(
                    investor2.address,
                    INVESTOR_INITIAL_BALANCE
                )
        ).wait();

        await (
            await paymentToken
                .connect(deployer)
                .mint(
                    issuer.address,
                    ISSUER_INITIAL_BALANCE
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

    async function deployWithoutControllerFixture() {
        const [
            deployer,
            admin,
            issuer,
            investor1,
        ] = await ethers.getSigners();

        const MockBondUSD =
            await ethers.getContractFactory(
                "MockBondUSD"
            );

        const paymentToken =
            await MockBondUSD
                .connect(deployer)
                .deploy(deployer.address);

        await paymentToken.waitForDeployment();

        const BondToken =
            await ethers.getContractFactory(
                "BondToken"
            );

        const bondToken =
            await BondToken
                .connect(deployer)
                .deploy(deployer.address);

        await bondToken.waitForDeployment();

        const TokenizedBond =
            await ethers.getContractFactory(
                "TokenizedBond"
            );

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

        return {
            deployer,
            admin,
            issuer,
            investor1,
            paymentToken,
            bondToken,
            tokenizedBond,
        };
    }

    describe("Deployment and configuration", function () {
        it("stores the correct roles and contract addresses", async function () {
            const {
                admin,
                issuer,
                paymentToken,
                bondToken,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            expect(await tokenizedBond.admin())
                .to.equal(admin.address);

            expect(await tokenizedBond.issuer())
                .to.equal(issuer.address);

            expect(await tokenizedBond.paymentToken())
                .to.equal(
                    await paymentToken.getAddress()
                );

            expect(await tokenizedBond.bondToken())
                .to.equal(
                    await bondToken.getAddress()
                );
        });

        it("starts in Draft lifecycle", async function () {
            const {
                tokenizedBond,
            } = await loadFixture(deployFixture);

            expect(await tokenizedBond.lifecycle())
                .to.equal(0n);

            expect(
                await tokenizedBond.subscriptionPaused()
            ).to.equal(false);

            expect(
                await tokenizedBond.totalSubscribed()
            ).to.equal(0n);

            expect(
                await tokenizedBond.totalRaised()
            ).to.equal(0n);
        });

        it("stores the correct economic constants", async function () {
            const {
                tokenizedBond,
            } = await loadFixture(deployFixture);

            expect(
                await tokenizedBond.BOND_NAME()
            ).to.equal(
                "Demo Corporate Bond 2026"
            );

            expect(
                await tokenizedBond.FACE_VALUE()
            ).to.equal(FACE_VALUE);

            expect(
                await tokenizedBond.ISSUE_PRICE()
            ).to.equal(ISSUE_PRICE);

            expect(
                await tokenizedBond.MAX_BOND_SUPPLY()
            ).to.equal(MAX_BOND_SUPPLY);

            expect(
                await tokenizedBond.MINIMUM_SUBSCRIPTION()
            ).to.equal(MINIMUM_SUBSCRIPTION);

            expect(
                await tokenizedBond.COUPON_PER_PERIOD()
            ).to.equal(COUPON_PER_PERIOD);

            expect(
                await tokenizedBond.COUPON_PERIOD_COUNT()
            ).to.equal(2n);
        });

        it("sets TokenizedBond as controller and removes BondToken ownership", async function () {
            const {
                bondToken,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            expect(await bondToken.controller())
                .to.equal(
                    await tokenizedBond.getAddress()
                );

            expect(await bondToken.owner())
                .to.equal(ethers.ZeroAddress);
        });

        it("rejects identical admin and issuer roles", async function () {
            const {
                admin,
                paymentToken,
                bondToken,
            } = await loadFixture(
                deployWithoutControllerFixture
            );

            const TokenizedBond =
                await ethers.getContractFactory(
                    "TokenizedBond"
                );

            await expect(
                TokenizedBond.deploy(
                    admin.address,
                    admin.address,
                    await paymentToken.getAddress(),
                    await bondToken.getAddress()
                )
            ).to.be.revertedWithCustomError(
                TokenizedBond,
                "RolesMustDiffer"
            );
        });

        it("rejects zero addresses", async function () {
            const {
                issuer,
                paymentToken,
                bondToken,
            } = await loadFixture(
                deployWithoutControllerFixture
            );

            const TokenizedBond =
                await ethers.getContractFactory(
                    "TokenizedBond"
                );

            await expect(
                TokenizedBond.deploy(
                    ethers.ZeroAddress,
                    issuer.address,
                    await paymentToken.getAddress(),
                    await bondToken.getAddress()
                )
            ).to.be.revertedWithCustomError(
                TokenizedBond,
                "ZeroAddress"
            );
        });
    });

    describe("Whitelist and subscription administration", function () {
        it("allows admin to whitelist an investor", async function () {
            const {
                admin,
                investor1,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await expect(
                tokenizedBond
                    .connect(admin)
                    .setWhitelist(
                        investor1.address,
                        true
                    )
            )
                .to.emit(
                    tokenizedBond,
                    "WhitelistUpdated"
                )
                .withArgs(
                    investor1.address,
                    true
                );

            expect(
                await tokenizedBond.whitelisted(
                    investor1.address
                )
            ).to.equal(true);
        });

        it("allows admin to remove an investor from whitelist", async function () {
            const {
                admin,
                investor1,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor1.address,
                    true
                );

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor1.address,
                    false
                );

            expect(
                await tokenizedBond.whitelisted(
                    investor1.address
                )
            ).to.equal(false);
        });

        it("rejects whitelist updates from non-admin accounts", async function () {
            const {
                issuer,
                investor1,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .setWhitelist(
                        investor1.address,
                        true
                    )
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "NotAdmin"
                )
                .withArgs(issuer.address);
        });

        it("rejects the zero address in whitelist", async function () {
            const {
                admin,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await expect(
                tokenizedBond
                    .connect(admin)
                    .setWhitelist(
                        ethers.ZeroAddress,
                        true
                    )
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "ZeroAddress"
            );
        });

        it("allows admin to pause and unpause subscription", async function () {
            const {
                admin,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await expect(
                tokenizedBond
                    .connect(admin)
                    .pauseSubscription()
            ).to.emit(
                tokenizedBond,
                "SubscriptionPaused"
            );

            expect(
                await tokenizedBond.subscriptionPaused()
            ).to.equal(true);

            await expect(
                tokenizedBond
                    .connect(admin)
                    .unpauseSubscription()
            ).to.emit(
                tokenizedBond,
                "SubscriptionUnpaused"
            );

            expect(
                await tokenizedBond.subscriptionPaused()
            ).to.equal(false);
        });

        it("rejects duplicate pause and invalid unpause", async function () {
            const {
                admin,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await expect(
                tokenizedBond
                    .connect(admin)
                    .unpauseSubscription()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "NotPaused"
            );

            await tokenizedBond
                .connect(admin)
                .pauseSubscription();

            await expect(
                tokenizedBond
                    .connect(admin)
                    .pauseSubscription()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "AlreadyPaused"
            );
        });
    });

    describe("Opening subscription", function () {
        it("allows issuer to open subscription", async function () {
            const {
                issuer,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .openSubscription()
            ).to.emit(
                tokenizedBond,
                "SubscriptionOpened"
            );

            expect(await tokenizedBond.lifecycle())
                .to.equal(1n);

            const start =
                await tokenizedBond.subscriptionStart();

            const deadline =
                await tokenizedBond.subscriptionDeadline();

            const duration =
                await tokenizedBond
                    .SUBSCRIPTION_DURATION();

            expect(deadline - start)
                .to.equal(duration);

            expect(
                await tokenizedBond
                    .isSubscriptionOpen()
            ).to.equal(true);
        });

        it("rejects opening by a non-issuer account", async function () {
            const {
                admin,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await expect(
                tokenizedBond
                    .connect(admin)
                    .openSubscription()
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "NotIssuer"
                )
                .withArgs(admin.address);
        });

        it("rejects opening while subscription is paused", async function () {
            const {
                admin,
                issuer,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await tokenizedBond
                .connect(admin)
                .pauseSubscription();

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .openSubscription()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "SubscriptionIsPaused"
            );
        });

        it("rejects opening before BondToken controller is configured", async function () {
            const {
                issuer,
                tokenizedBond,
            } = await loadFixture(
                deployWithoutControllerFixture
            );

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .openSubscription()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "InvalidBondTokenState"
            );
        });

        it("rejects opening subscription twice", async function () {
            const {
                issuer,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .openSubscription()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "InvalidLifecycle"
            );
        });
    });
    
    describe("Investor subscription", function () {
        async function prepareSubscription(
            context,
            investors
        ) {
            const {
                admin,
                issuer,
                tokenizedBond,
            } = context;

            for (const investor of investors) {
                await tokenizedBond
                    .connect(admin)
                    .setWhitelist(
                        investor.address,
                        true
                    );
            }

            await tokenizedBond
                .connect(issuer)
                .openSubscription();
        }

        it("allows a whitelisted investor to subscribe", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                paymentToken,
                bondToken,
                tokenizedBond,
            } = context;

            await prepareSubscription(
                context,
                [investor1]
            );

            const quantity = 10n;
            const payment =
                quantity * ISSUE_PRICE;

            const investorBalanceBefore =
                await paymentToken.balanceOf(
                    investor1.address
                );

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    payment
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
                await tokenizedBond
                    .subscribedQuantity(
                        investor1.address
                    )
            ).to.equal(quantity);

            expect(
                await tokenizedBond.paidAmount(
                    investor1.address
                )
            ).to.equal(payment);

            expect(
                await tokenizedBond.totalSubscribed()
            ).to.equal(quantity);

            expect(
                await tokenizedBond.totalRaised()
            ).to.equal(payment);

            expect(
                await bondToken.balanceOf(
                    investor1.address
                )
            ).to.equal(quantity);

            expect(
                await bondToken.totalSupply()
            ).to.equal(quantity);

            expect(
                await paymentToken.balanceOf(
                    await tokenizedBond.getAddress()
                )
            ).to.equal(payment);

            expect(
                await paymentToken.balanceOf(
                    investor1.address
                )
            ).to.equal(
                investorBalanceBefore - payment
            );
        });

        it("accumulates multiple subscriptions from the same investor", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                paymentToken,
                bondToken,
                tokenizedBond,
            } = context;

            await prepareSubscription(
                context,
                [investor1]
            );

            const firstQuantity = 10n;
            const secondQuantity = 5n;

            const totalQuantity =
                firstQuantity + secondQuantity;

            const totalPayment =
                totalQuantity * ISSUE_PRICE;

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    totalPayment
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(firstQuantity);

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .subscribe(secondQuantity)
            )
                .to.emit(
                    tokenizedBond,
                    "BondSubscribed"
                )
                .withArgs(
                    investor1.address,
                    secondQuantity,
                    secondQuantity * ISSUE_PRICE,
                    totalQuantity,
                    totalQuantity
                );

            expect(
                await tokenizedBond
                    .subscribedQuantity(
                        investor1.address
                    )
            ).to.equal(totalQuantity);

            expect(
                await tokenizedBond.paidAmount(
                    investor1.address
                )
            ).to.equal(totalPayment);

            expect(
                await bondToken.balanceOf(
                    investor1.address
                )
            ).to.equal(totalQuantity);

            expect(
                await tokenizedBond.totalSubscribed()
            ).to.equal(totalQuantity);
        });

        it("rejects subscription before the offering is opened", async function () {
            const {
                investor1,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .subscribe(1n)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InvalidLifecycle"
                )
                .withArgs(0n);
        });

        it("rejects a non-whitelisted investor", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    ISSUE_PRICE
                );

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .subscribe(1n)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "NotWhitelisted"
                )
                .withArgs(investor1.address);
        });

        it("rejects subscription while paused", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                admin,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            await prepareSubscription(
                context,
                [investor1]
            );

            await tokenizedBond
                .connect(admin)
                .pauseSubscription();

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    ISSUE_PRICE
                );

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .subscribe(1n)
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "SubscriptionIsPaused"
            );
        });

        it("rejects a zero subscription quantity", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                tokenizedBond,
            } = context;

            await prepareSubscription(
                context,
                [investor1]
            );

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .subscribe(0n)
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "ZeroQuantity"
            );
        });

        it("rejects an investor with insufficient BondUSD balance", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                paymentToken,
                tokenizedBond,
            } = context;

            await prepareSubscription(
                context,
                [outsider]
            );

            expect(
                await paymentToken.balanceOf(
                    outsider.address
                )
            ).to.equal(0n);

            await paymentToken
                .connect(outsider)
                .approve(
                    await tokenizedBond.getAddress(),
                    ISSUE_PRICE
                );

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .subscribe(1n)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InsufficientTokenBalance"
                )
                .withArgs(
                    ISSUE_PRICE,
                    0n
                );
        });

        it("rejects an investor with insufficient allowance", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                tokenizedBond,
            } = context;

            await prepareSubscription(
                context,
                [investor1]
            );

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .subscribe(1n)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InsufficientAllowance"
                )
                .withArgs(
                    ISSUE_PRICE,
                    0n
                );
        });

        it("rejects a quantity exceeding the remaining supply", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                investor2,
                paymentToken,
                tokenizedBond,
            } = context;

            await prepareSubscription(
                context,
                [investor1, investor2]
            );

            const investor1Quantity = 90n;
            const investor2Quantity = 11n;

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    investor1Quantity *
                        ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(investor1Quantity);

            await paymentToken
                .connect(investor2)
                .approve(
                    await tokenizedBond.getAddress(),
                    investor2Quantity *
                        ISSUE_PRICE
                );

            await expect(
                tokenizedBond
                    .connect(investor2)
                    .subscribe(investor2Quantity)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "MaxSupplyExceeded"
                )
                .withArgs(
                    investor2Quantity,
                    10n
                );

            expect(
                await tokenizedBond.totalSubscribed()
            ).to.equal(90n);
        });

        it("rejects subscription after the deadline", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            await prepareSubscription(
                context,
                [investor1]
            );

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    ISSUE_PRICE
                );

            const deadline =
                await tokenizedBond
                    .subscriptionDeadline();

            await time.increaseTo(deadline);

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .subscribe(1n)
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "SubscriptionExpired"
            );
        });

        it("marks the subscription unavailable after selling the maximum supply", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                paymentToken,
                bondToken,
                tokenizedBond,
            } = context;

            await prepareSubscription(
                context,
                [investor1]
            );

            const payment =
                MAX_BOND_SUPPLY *
                ISSUE_PRICE;

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    payment
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(MAX_BOND_SUPPLY);

            expect(
                await tokenizedBond.totalSubscribed()
            ).to.equal(MAX_BOND_SUPPLY);

            expect(
                await bondToken.totalSupply()
            ).to.equal(MAX_BOND_SUPPLY);

            expect(
                await tokenizedBond
                    .isSubscriptionOpen()
            ).to.equal(false);

            expect(
                await tokenizedBond.canFinalize()
            ).to.equal(true);
        });

        it("prevents additional subscriptions after removal from whitelist", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                admin,
                investor1,
                paymentToken,
                bondToken,
                tokenizedBond,
            } = context;

            await prepareSubscription(
                context,
                [investor1]
            );

            const allowance =
                20n * ISSUE_PRICE;

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    allowance
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(10n);

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor1.address,
                    false
                );

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .subscribe(5n)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "NotWhitelisted"
                )
                .withArgs(investor1.address);

            expect(
                await bondToken.balanceOf(
                    investor1.address
                )
            ).to.equal(10n);

            expect(
                await tokenizedBond
                    .subscribedQuantity(
                        investor1.address
                    )
            ).to.equal(10n);
        });
    });
    
    describe(
        "Finalization, proceeds and refunds",
        function () {
            async function prepareOffering(
                context,
                subscriptions
            ) {
                const {
                    admin,
                    issuer,
                    paymentToken,
                    tokenizedBond,
                } = context;

                for (
                    const [investor] of subscriptions
                ) {
                    await tokenizedBond
                        .connect(admin)
                        .setWhitelist(
                            investor.address,
                            true
                        );
                }

                await tokenizedBond
                    .connect(issuer)
                    .openSubscription();

                for (
                    const [
                        investor,
                        quantity,
                    ] of subscriptions
                ) {
                    const payment =
                        quantity * ISSUE_PRICE;

                    await paymentToken
                        .connect(investor)
                        .approve(
                            await tokenizedBond
                                .getAddress(),
                            payment
                        );

                    await tokenizedBond
                        .connect(investor)
                        .subscribe(quantity);
                }
            }

            async function moveToDeadline(
                tokenizedBond
            ) {
                const deadline =
                    await tokenizedBond
                        .subscriptionDeadline();

                await time.increaseTo(deadline);
            }

            it("rejects finalization before the deadline when the offering is not sold out", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    outsider,
                    tokenizedBond,
                } = context;

                await prepareOffering(
                    context,
                    [[investor1, 10n]]
                );

                expect(
                    await tokenizedBond.canFinalize()
                ).to.equal(false);

                await expect(
                    tokenizedBond
                        .connect(outsider)
                        .finalizeOffering()
                ).to.be.revertedWithCustomError(
                    tokenizedBond,
                    "CannotFinalizeYet"
                );
            });

            it("allows any account to finalize immediately when the offering is sold out", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    outsider,
                    tokenizedBond,
                } = context;

                await prepareOffering(
                    context,
                    [[
                        investor1,
                        MAX_BOND_SUPPLY,
                    ]]
                );

                await expect(
                    tokenizedBond
                        .connect(outsider)
                        .finalizeOffering()
                ).to.emit(
                    tokenizedBond,
                    "OfferingFinalized"
                );

                expect(
                    await tokenizedBond.lifecycle()
                ).to.equal(3n);

                expect(
                    await tokenizedBond
                        .totalSubscribed()
                ).to.equal(MAX_BOND_SUPPLY);
            });

            it("finalizes successfully after the deadline when the minimum subscription is reached", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    outsider,
                    tokenizedBond,
                } = context;

                await prepareOffering(
                    context,
                    [[
                        investor1,
                        MINIMUM_SUBSCRIPTION,
                    ]]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                expect(
                    await tokenizedBond.canFinalize()
                ).to.equal(true);

                await tokenizedBond
                    .connect(outsider)
                    .finalizeOffering();

                expect(
                    await tokenizedBond.lifecycle()
                ).to.equal(3n);

                expect(
                    await tokenizedBond
                        .finalizedAt()
                ).to.be.greaterThan(0n);
            });

            it("calculates coupon, principal and maturity obligations correctly", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    investor2,
                    tokenizedBond,
                } = context;

                const quantity1 = 30n;
                const quantity2 = 40n;
                const totalQuantity =
                    quantity1 + quantity2;

                await prepareOffering(
                    context,
                    [
                        [
                            investor1,
                            quantity1,
                        ],
                        [
                            investor2,
                            quantity2,
                        ],
                    ]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                const finalizedAt =
                    await tokenizedBond
                        .finalizedAt();

                const coupon1Delay =
                    await tokenizedBond
                        .COUPON_1_DELAY();

                const coupon2Delay =
                    await tokenizedBond
                        .COUPON_2_DELAY();

                const couponRequired =
                    totalQuantity *
                    COUPON_PER_PERIOD;

                const principalRequired =
                    totalQuantity *
                    FACE_VALUE;

                expect(
                    await tokenizedBond
                        .couponDue(1)
                ).to.equal(
                    finalizedAt +
                        coupon1Delay
                );

                expect(
                    await tokenizedBond
                        .couponDue(2)
                ).to.equal(
                    finalizedAt +
                        coupon2Delay
                );

                expect(
                    await tokenizedBond.maturity()
                ).to.equal(
                    finalizedAt +
                        coupon2Delay
                );

                expect(
                    await tokenizedBond
                        .couponRequired(1)
                ).to.equal(couponRequired);

                expect(
                    await tokenizedBond
                        .couponRequired(2)
                ).to.equal(couponRequired);

                expect(
                    await tokenizedBond
                        .principalRequired()
                ).to.equal(
                    principalRequired
                );
            });

            it("finalizes as Failed when the minimum subscription is not reached", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    outsider,
                    tokenizedBond,
                } = context;

                const quantity = 40n;

                await prepareOffering(
                    context,
                    [[investor1, quantity]]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await expect(
                    tokenizedBond
                        .connect(outsider)
                        .finalizeOffering()
                ).to.emit(
                    tokenizedBond,
                    "OfferingFinalized"
                );

                expect(
                    await tokenizedBond.lifecycle()
                ).to.equal(2n);

                expect(
                    await tokenizedBond
                        .couponRequired(1)
                ).to.equal(0n);

                expect(
                    await tokenizedBond
                        .couponRequired(2)
                ).to.equal(0n);

                expect(
                    await tokenizedBond
                        .principalRequired()
                ).to.equal(0n);
            });

            it("rejects finalization more than once", async function () {
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
                        MINIMUM_SUBSCRIPTION,
                    ]]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                await expect(
                    tokenizedBond
                        .finalizeOffering()
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "InvalidLifecycle"
                    )
                    .withArgs(3n);
            });

            it("allows issuer to withdraw proceeds after a successful offering", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    issuer,
                    investor1,
                    paymentToken,
                    tokenizedBond,
                } = context;

                const quantity =
                    MINIMUM_SUBSCRIPTION;

                const raisedAmount =
                    quantity * ISSUE_PRICE;

                await prepareOffering(
                    context,
                    [[investor1, quantity]]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                const issuerBalanceBefore =
                    await paymentToken
                        .balanceOf(
                            issuer.address
                        );

                await expect(
                    tokenizedBond
                        .connect(issuer)
                        .withdrawProceeds()
                )
                    .to.emit(
                        tokenizedBond,
                        "ProceedsWithdrawn"
                    )
                    .withArgs(
                        issuer.address,
                        raisedAmount
                    );

                expect(
                    await tokenizedBond
                        .proceedsWithdrawn()
                ).to.equal(true);

                expect(
                    await paymentToken
                        .balanceOf(
                            issuer.address
                        )
                ).to.equal(
                    issuerBalanceBefore +
                        raisedAmount
                );

                expect(
                    await paymentToken
                        .balanceOf(
                            await tokenizedBond
                                .getAddress()
                        )
                ).to.equal(0n);
            });

            it("rejects proceeds withdrawal by a non-issuer account", async function () {
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
                    [[
                        investor1,
                        MINIMUM_SUBSCRIPTION,
                    ]]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                await expect(
                    tokenizedBond
                        .connect(admin)
                        .withdrawProceeds()
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "NotIssuer"
                    )
                    .withArgs(admin.address);
            });

            it("rejects proceeds withdrawal after a failed offering", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    issuer,
                    investor1,
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

                await expect(
                    tokenizedBond
                        .connect(issuer)
                        .withdrawProceeds()
                )
                    .to.be
                    .revertedWithCustomError(
                        tokenizedBond,
                        "InvalidLifecycle"
                    )
                    .withArgs(2n);
            });

            it("rejects a second proceeds withdrawal", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    issuer,
                    investor1,
                    tokenizedBond,
                } = context;

                await prepareOffering(
                    context,
                    [[
                        investor1,
                        MINIMUM_SUBSCRIPTION,
                    ]]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                await tokenizedBond
                    .connect(issuer)
                    .withdrawProceeds();

                await expect(
                    tokenizedBond
                        .connect(issuer)
                        .withdrawProceeds()
                ).to.be.revertedWithCustomError(
                    tokenizedBond,
                    "ProceedsAlreadyWithdrawn"
                );
            });

            it("allows an investor to claim a refund after a failed offering", async function () {
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

                const quantity = 20n;
                const refundAmount =
                    quantity * ISSUE_PRICE;

                const initialBalance =
                    await paymentToken
                        .balanceOf(
                            investor1.address
                        );

                await prepareOffering(
                    context,
                    [[investor1, quantity]]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                await expect(
                    tokenizedBond
                        .connect(investor1)
                        .claimRefund()
                )
                    .to.emit(
                        tokenizedBond,
                        "RefundClaimed"
                    )
                    .withArgs(
                        investor1.address,
                        quantity,
                        refundAmount
                    );

                expect(
                    await paymentToken
                        .balanceOf(
                            investor1.address
                        )
                ).to.equal(initialBalance);

                expect(
                    await bondToken.balanceOf(
                        investor1.address
                    )
                ).to.equal(0n);

                expect(
                    await bondToken.totalSupply()
                ).to.equal(0n);

                expect(
                    await tokenizedBond
                        .refundClaimed(
                            investor1.address
                        )
                ).to.equal(true);

                expect(
                    await tokenizedBond
                        .totalRefunded()
                ).to.equal(refundAmount);
            });

            it("preserves refund rights after an investor is removed from whitelist", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    admin,
                    investor1,
                    paymentToken,
                    tokenizedBond,
                } = context;

                const quantity = 20n;
                const refundAmount =
                    quantity * ISSUE_PRICE;

                await prepareOffering(
                    context,
                    [[investor1, quantity]]
                );

                await tokenizedBond
                    .connect(admin)
                    .setWhitelist(
                        investor1.address,
                        false
                    );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                expect(
                    await tokenizedBond.whitelisted(
                        investor1.address
                    )
                ).to.equal(false);

                await tokenizedBond
                    .connect(investor1)
                    .claimRefund();

                expect(
                    await paymentToken.balanceOf(
                        investor1.address
                    )
                ).to.equal(
                    INVESTOR_INITIAL_BALANCE
                );

                expect(
                    await tokenizedBond
                        .totalRefunded()
                ).to.equal(refundAmount);
            });

            it("rejects duplicate refund claims", async function () {
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
                    [[investor1, 20n]]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                await tokenizedBond
                    .connect(investor1)
                    .claimRefund();

                await expect(
                    tokenizedBond
                        .connect(investor1)
                        .claimRefund()
                ).to.be.revertedWithCustomError(
                    tokenizedBond,
                    "RefundAlreadyClaimed"
                );
            });

            it("rejects refund claims from accounts without a position", async function () {
                const context =
                    await loadFixture(
                        deployFixture
                    );

                const {
                    investor1,
                    outsider,
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

                await expect(
                    tokenizedBond
                        .connect(outsider)
                        .claimRefund()
                ).to.be.revertedWithCustomError(
                    tokenizedBond,
                    "NothingToRefund"
                );
            });

            it("becomes closable after all failed-offering refunds are completed", async function () {
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

                await prepareOffering(
                    context,
                    [
                        [investor1, 20n],
                        [investor2, 30n],
                    ]
                );

                await moveToDeadline(
                    tokenizedBond
                );

                await tokenizedBond
                    .finalizeOffering();

                expect(
                    await tokenizedBond.canClose()
                ).to.equal(false);

                await tokenizedBond
                    .connect(investor1)
                    .claimRefund();

                expect(
                    await tokenizedBond.canClose()
                ).to.equal(false);

                await tokenizedBond
                    .connect(investor2)
                    .claimRefund();

                expect(
                    await tokenizedBond
                        .totalRefunded()
                ).to.equal(
                    await tokenizedBond
                        .totalRaised()
                );

                expect(
                    await bondToken.totalSupply()
                ).to.equal(0n);

                expect(
                    await tokenizedBond.canClose()
                ).to.equal(true);
            });
        }
    );

    describe("Coupon funding and claims", function () {
        async function prepareActiveOffering(
            context
        ) {
            const {
                admin,
                issuer,
                investor1,
                investor2,
                paymentToken,
                tokenizedBond,
            } = context;

            const quantity1 = 30n;
            const quantity2 = 40n;

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor1.address,
                    true
                );

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor2.address,
                    true
                );

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    quantity1 * ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(quantity1);

            await paymentToken
                .connect(investor2)
                .approve(
                    await tokenizedBond.getAddress(),
                    quantity2 * ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor2)
                .subscribe(quantity2);

            const deadline =
                await tokenizedBond
                    .subscriptionDeadline();

            await time.increaseTo(deadline);

            await tokenizedBond
                .finalizeOffering();

            // Tách proceeds khỏi tiền coupon để test rõ ràng hơn.
            await tokenizedBond
                .connect(issuer)
                .withdrawProceeds();

            return {
                quantity1,
                quantity2,
                totalQuantity:
                    quantity1 + quantity2,
                couponRequired:
                    (quantity1 + quantity2) *
                    COUPON_PER_PERIOD,
            };
        }

        it("allows issuer to fund a coupon before its due date", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveOffering(
                context
            );

            const issuerBalanceBefore =
                await paymentToken.balanceOf(
                    issuer.address
                );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .depositCoupon(1)
            )
                .to.emit(
                    tokenizedBond,
                    "CouponFunded"
                );

            expect(
                await tokenizedBond
                    .couponFunded(1)
            ).to.equal(couponRequired);

            expect(
                await paymentToken.balanceOf(
                    issuer.address
                )
            ).to.equal(
                issuerBalanceBefore -
                    couponRequired
            );

            expect(
                await paymentToken.balanceOf(
                    await tokenizedBond.getAddress()
                )
            ).to.equal(couponRequired);
        });

        it("rejects coupon funding by a non-issuer account", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            await prepareActiveOffering(context);

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .depositCoupon(1)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "NotIssuer"
                )
                .withArgs(outsider.address);
        });

        it("rejects an invalid coupon period", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                tokenizedBond,
            } = context;

            await prepareActiveOffering(context);

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .depositCoupon(0)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InvalidCouponPeriod"
                )
                .withArgs(0n);

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .depositCoupon(3)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InvalidCouponPeriod"
                )
                .withArgs(3n);
        });

        it("rejects coupon funding with insufficient allowance", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveOffering(
                context
            );

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .depositCoupon(1)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InsufficientAllowance"
                )
                .withArgs(
                    couponRequired,
                    0n
                );
        });

        it("rejects coupon funding when issuer has insufficient balance", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                outsider,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveOffering(
                context
            );

            const issuerBalance =
                await paymentToken.balanceOf(
                    issuer.address
                );

            await paymentToken
                .connect(issuer)
                .transfer(
                    outsider.address,
                    issuerBalance
                );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .depositCoupon(1)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InsufficientTokenBalance"
                )
                .withArgs(
                    couponRequired,
                    0n
                );
        });

        it("rejects funding the same coupon period twice", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveOffering(
                context
            );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(1);

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .depositCoupon(1)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "CouponAlreadyFunded"
                )
                .withArgs(1n);
        });

        it("rejects coupon claims before the due date", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveOffering(
                context
            );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(1);

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .claimCoupon(1)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "CouponNotDue"
                )
                .withArgs(1n);
        });

        it("rejects coupon claims when the obligation is not funded", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                tokenizedBond,
            } = context;

            await prepareActiveOffering(context);

            const couponDue =
                await tokenizedBond.couponDue(1);

            await time.increaseTo(couponDue);

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .claimCoupon(1)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "CouponNotFunded"
                )
                .withArgs(1n);
        });

        it("allows an investor to claim the correct coupon amount", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                quantity1,
                couponRequired,
            } = await prepareActiveOffering(
                context
            );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(1);

            const couponDue =
                await tokenizedBond.couponDue(1);

            await time.increaseTo(couponDue);

            const expectedCoupon =
                quantity1 *
                COUPON_PER_PERIOD;

            const balanceBefore =
                await paymentToken.balanceOf(
                    investor1.address
                );

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .claimCoupon(1)
            )
                .to.emit(
                    tokenizedBond,
                    "CouponClaimed"
                )
                .withArgs(
                    1n,
                    investor1.address,
                    quantity1,
                    expectedCoupon
                );

            expect(
                await tokenizedBond.couponClaimed(
                    1,
                    investor1.address
                )
            ).to.equal(true);

            expect(
                await tokenizedBond
                    .couponClaimedTotal(1)
            ).to.equal(expectedCoupon);

            expect(
                await paymentToken.balanceOf(
                    investor1.address
                )
            ).to.equal(
                balanceBefore +
                    expectedCoupon
            );
        });

        it("pays both investors without exceeding the funded coupon amount", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                investor1,
                investor2,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveOffering(
                context
            );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(1);

            const couponDue =
                await tokenizedBond.couponDue(1);

            await time.increaseTo(couponDue);

            await tokenizedBond
                .connect(investor1)
                .claimCoupon(1);

            await tokenizedBond
                .connect(investor2)
                .claimCoupon(1);

            expect(
                await tokenizedBond
                    .couponClaimedTotal(1)
            ).to.equal(couponRequired);

            expect(
                await paymentToken.balanceOf(
                    await tokenizedBond.getAddress()
                )
            ).to.equal(0n);
        });

        it("rejects duplicate coupon claims", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveOffering(
                context
            );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(1);

            const couponDue =
                await tokenizedBond.couponDue(1);

            await time.increaseTo(couponDue);

            await tokenizedBond
                .connect(investor1)
                .claimCoupon(1);

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .claimCoupon(1)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "CouponAlreadyClaimed"
                )
                .withArgs(1n);
        });

        it("rejects coupon claims from accounts without BondToken", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                outsider,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveOffering(
                context
            );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(1);

            const couponDue =
                await tokenizedBond.couponDue(1);

            await time.increaseTo(couponDue);

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .claimCoupon(1)
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "ZeroQuantity"
            );
        });

        it("preserves coupon rights after an investor is removed from whitelist", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                admin,
                issuer,
                investor1,
                investor2,
                paymentToken,
                tokenizedBond,
            } = context;

            const quantity1 = 30n;
            const quantity2 = 40n;
            const totalQuantity =
                quantity1 + quantity2;

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor1.address,
                    true
                );

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor2.address,
                    true
                );

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    quantity1 * ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(quantity1);

            await paymentToken
                .connect(investor2)
                .approve(
                    await tokenizedBond.getAddress(),
                    quantity2 * ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor2)
                .subscribe(quantity2);

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor1.address,
                    false
                );

            const deadline =
                await tokenizedBond
                    .subscriptionDeadline();

            await time.increaseTo(deadline);

            await tokenizedBond
                .finalizeOffering();

            await tokenizedBond
                .connect(issuer)
                .withdrawProceeds();

            const couponRequired =
                totalQuantity *
                COUPON_PER_PERIOD;

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(1);

            const couponDue =
                await tokenizedBond.couponDue(1);

            await time.increaseTo(couponDue);

            expect(
                await tokenizedBond.whitelisted(
                    investor1.address
                )
            ).to.equal(false);

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .claimCoupon(1)
            ).to.emit(
                tokenizedBond,
                "CouponClaimed"
            );
        });

        it("handles coupon period 2 independently from period 1", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                quantity1,
                couponRequired,
            } = await prepareActiveOffering(
                context
            );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(2);

            const couponDue2 =
                await tokenizedBond.couponDue(2);

            await time.increaseTo(couponDue2);

            const expectedCoupon =
                quantity1 *
                COUPON_PER_PERIOD;

            await tokenizedBond
                .connect(investor1)
                .claimCoupon(2);

            expect(
                await tokenizedBond.couponClaimed(
                    2,
                    investor1.address
                )
            ).to.equal(true);

            expect(
                await tokenizedBond.couponClaimed(
                    1,
                    investor1.address
                )
            ).to.equal(false);

            expect(
                await tokenizedBond
                    .couponClaimedTotal(2)
            ).to.equal(expectedCoupon);
        });
    });
    
    describe("Principal and maturity", function () {
        async function prepareActiveBond(
            context,
            options = {}
        ) {
            const {
                admin,
                issuer,
                investor1,
                investor2,
                paymentToken,
                tokenizedBond,
            } = context;

            const withdrawProceeds =
                options.withdrawProceeds ?? true;

            const quantity1 = 30n;
            const quantity2 = 40n;
            const totalQuantity =
                quantity1 + quantity2;

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor1.address,
                    true
                );

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor2.address,
                    true
                );

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    quantity1 * ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(quantity1);

            await paymentToken
                .connect(investor2)
                .approve(
                    await tokenizedBond.getAddress(),
                    quantity2 * ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor2)
                .subscribe(quantity2);

            const deadline =
                await tokenizedBond
                    .subscriptionDeadline();

            await time.increaseTo(deadline);

            await tokenizedBond
                .finalizeOffering();

            if (withdrawProceeds) {
                await tokenizedBond
                    .connect(issuer)
                    .withdrawProceeds();
            }

            return {
                quantity1,
                quantity2,
                totalQuantity,
                couponRequired:
                    totalQuantity *
                    COUPON_PER_PERIOD,
                principalRequired:
                    totalQuantity *
                    FACE_VALUE,
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

        async function fundAllObligations(
            context,
            couponRequired,
            principalRequired
        ) {
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
        }

        async function moveToMaturity(
            tokenizedBond
        ) {
            const maturity =
                await tokenizedBond.maturity();

            await time.increaseTo(maturity);
        }

        async function claimBothCoupons(
            context,
            investor
        ) {
            const {
                tokenizedBond,
            } = context;

            await tokenizedBond
                .connect(investor)
                .claimCoupon(1);

            await tokenizedBond
                .connect(investor)
                .claimCoupon(2);
        }

        it("allows issuer to fund principal before maturity", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                principalRequired,
            } = await prepareActiveBond(context);

            const issuerBalanceBefore =
                await paymentToken.balanceOf(
                    issuer.address
                );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    principalRequired
                );

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .depositPrincipal()
            ).to.emit(
                tokenizedBond,
                "PrincipalFunded"
            );

            expect(
                await tokenizedBond
                    .principalFunded()
            ).to.equal(principalRequired);

            expect(
                await paymentToken.balanceOf(
                    issuer.address
                )
            ).to.equal(
                issuerBalanceBefore -
                    principalRequired
            );

            expect(
                await paymentToken.balanceOf(
                    await tokenizedBond.getAddress()
                )
            ).to.equal(principalRequired);
        });

        it("rejects principal funding by a non-issuer account", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            await prepareActiveBond(context);

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .depositPrincipal()
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "NotIssuer"
                )
                .withArgs(outsider.address);
        });

        it("rejects principal funding with insufficient allowance", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                tokenizedBond,
            } = context;

            const {
                principalRequired,
            } = await prepareActiveBond(context);

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .depositPrincipal()
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InsufficientAllowance"
                )
                .withArgs(
                    principalRequired,
                    0n
                );
        });

        it("rejects principal funding when issuer has insufficient balance", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                outsider,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                principalRequired,
            } = await prepareActiveBond(context);

            const issuerBalance =
                await paymentToken.balanceOf(
                    issuer.address
                );

            await paymentToken
                .connect(issuer)
                .transfer(
                    outsider.address,
                    issuerBalance
                );

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    principalRequired
                );

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .depositPrincipal()
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InsufficientTokenBalance"
                )
                .withArgs(
                    principalRequired,
                    0n
                );
        });

        it("rejects funding principal twice", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                principalRequired,
            } = await prepareActiveBond(context);

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    principalRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositPrincipal();

            await expect(
                tokenizedBond
                    .connect(issuer)
                    .depositPrincipal()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "PrincipalAlreadyFunded"
            );
        });

        it("rejects marking the bond as matured before maturity", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            await prepareActiveBond(context);

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .markMatured()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "NotMatured"
            );
        });

        it("allows any account to mark the bond as matured after maturity", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            await prepareActiveBond(context);

            await moveToMaturity(
                tokenizedBond
            );

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .markMatured()
            ).to.emit(
                tokenizedBond,
                "BondMatured"
            );

            expect(
                await tokenizedBond.lifecycle()
            ).to.equal(4n);
        });

        it("automatically synchronizes maturity during principal redemption", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
                principalRequired,
            } = await prepareActiveBond(context);

            await fundAllObligations(
                context,
                couponRequired,
                principalRequired
            );

            await moveToMaturity(
                tokenizedBond
            );

            expect(
                await tokenizedBond.lifecycle()
            ).to.equal(3n);

            await claimBothCoupons(
                context,
                investor1
            );

            await tokenizedBond
                .connect(investor1)
                .redeemPrincipal();

            expect(
                await tokenizedBond.lifecycle()
            ).to.equal(4n);
        });

        it("rejects principal redemption before maturity", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
                principalRequired,
            } = await prepareActiveBond(context);

            await fundAllObligations(
                context,
                couponRequired,
                principalRequired
            );

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .redeemPrincipal()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "NotMatured"
            );
        });

        it("rejects redemption when principal is not funded", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveBond(context);

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

            await moveToMaturity(
                tokenizedBond
            );

            await claimBothCoupons(
                context,
                investor1
            );

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .redeemPrincipal()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "PrincipalNotFunded"
            );
        });

        it("rejects redemption before both coupons are claimed", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
                principalRequired,
            } = await prepareActiveBond(context);

            await fundAllObligations(
                context,
                couponRequired,
                principalRequired
            );

            await moveToMaturity(
                tokenizedBond
            );

            await tokenizedBond
                .connect(investor1)
                .claimCoupon(1);

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .redeemPrincipal()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "CouponsNotFullyClaimed"
            );
        });

        it("pays the correct principal and burns the investor BondToken", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                paymentToken,
                bondToken,
                tokenizedBond,
            } = context;

            const {
                quantity1,
                couponRequired,
                principalRequired,
            } = await prepareActiveBond(context);

            await fundAllObligations(
                context,
                couponRequired,
                principalRequired
            );

            await moveToMaturity(
                tokenizedBond
            );

            await claimBothCoupons(
                context,
                investor1
            );

            const expectedPrincipal =
                quantity1 * FACE_VALUE;

            const balanceBefore =
                await paymentToken.balanceOf(
                    investor1.address
                );

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .redeemPrincipal()
            )
                .to.emit(
                    tokenizedBond,
                    "PrincipalRedeemed"
                )
                .withArgs(
                    investor1.address,
                    quantity1,
                    expectedPrincipal
                );

            expect(
                await paymentToken.balanceOf(
                    investor1.address
                )
            ).to.equal(
                balanceBefore +
                    expectedPrincipal
            );

            expect(
                await bondToken.balanceOf(
                    investor1.address
                )
            ).to.equal(0n);

            expect(
                await bondToken.totalSupply()
            ).to.equal(40n);

            expect(
                await tokenizedBond
                    .principalRedeemed(
                        investor1.address
                    )
            ).to.equal(true);

            expect(
                await tokenizedBond
                    .principalRedeemedTotal()
            ).to.equal(expectedPrincipal);
        });

        it("rejects duplicate principal redemption", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
                principalRequired,
            } = await prepareActiveBond(context);

            await fundAllObligations(
                context,
                couponRequired,
                principalRequired
            );

            await moveToMaturity(
                tokenizedBond
            );

            await claimBothCoupons(
                context,
                investor1
            );

            await tokenizedBond
                .connect(investor1)
                .redeemPrincipal();

            await expect(
                tokenizedBond
                    .connect(investor1)
                    .redeemPrincipal()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "PrincipalAlreadyRedeemed"
            );
        });

        it("becomes closable after every investor redeems principal", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                investor2,
                bondToken,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
                principalRequired,
            } = await prepareActiveBond(context);

            await fundAllObligations(
                context,
                couponRequired,
                principalRequired
            );

            await moveToMaturity(
                tokenizedBond
            );

            await claimBothCoupons(
                context,
                investor1
            );

            await claimBothCoupons(
                context,
                investor2
            );

            await tokenizedBond
                .connect(investor1)
                .redeemPrincipal();

            expect(
                await tokenizedBond.canClose()
            ).to.equal(false);

            await tokenizedBond
                .connect(investor2)
                .redeemPrincipal();

            expect(
                await tokenizedBond
                    .principalRedeemedTotal()
            ).to.equal(principalRequired);

            expect(
                await bondToken.totalSupply()
            ).to.equal(0n);

            expect(
                await tokenizedBond.canClose()
            ).to.equal(true);
        });

        it("does not allow closing a successful bond before issuer withdraws proceeds", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                investor1,
                investor2,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
                principalRequired,
            } = await prepareActiveBond(
                context,
                {
                    withdrawProceeds: false,
                }
            );

            await fundAllObligations(
                context,
                couponRequired,
                principalRequired
            );

            await moveToMaturity(
                tokenizedBond
            );

            await claimBothCoupons(
                context,
                investor1
            );

            await claimBothCoupons(
                context,
                investor2
            );

            await tokenizedBond
                .connect(investor1)
                .redeemPrincipal();

            await tokenizedBond
                .connect(investor2)
                .redeemPrincipal();

            expect(
                await tokenizedBond
                    .proceedsWithdrawn()
            ).to.equal(false);

            expect(
                await tokenizedBond.canClose()
            ).to.equal(false);

            await expect(
                tokenizedBond.closeBond()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "CloseConditionsNotMet"
            );

            await tokenizedBond
                .connect(issuer)
                .withdrawProceeds();

            expect(
                await tokenizedBond.canClose()
            ).to.equal(true);
        });
    });
    describe("Default recording and cure", function () {
        async function prepareActiveBond(context) {
            const {
                admin,
                issuer,
                investor1,
                investor2,
                paymentToken,
                tokenizedBond,
            } = context;

            const quantity1 = 30n;
            const quantity2 = 40n;
            const totalQuantity = quantity1 + quantity2;

            await tokenizedBond
                .connect(admin)
                .setWhitelist(investor1.address, true);

            await tokenizedBond
                .connect(admin)
                .setWhitelist(investor2.address, true);

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    quantity1 * ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(quantity1);

            await paymentToken
                .connect(investor2)
                .approve(
                    await tokenizedBond.getAddress(),
                    quantity2 * ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor2)
                .subscribe(quantity2);

            const deadline =
                await tokenizedBond.subscriptionDeadline();

            await time.increaseTo(deadline);
            await tokenizedBond.finalizeOffering();

            await tokenizedBond
                .connect(issuer)
                .withdrawProceeds();

            return {
                quantity1,
                quantity2,
                totalQuantity,
                couponRequired:
                    totalQuantity * COUPON_PER_PERIOD,
                principalRequired:
                    totalQuantity * FACE_VALUE,
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

            return tokenizedBond
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

            return tokenizedBond
                .connect(issuer)
                .depositPrincipal();
        }

        it("rejects coupon default before the grace period expires", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            await prepareActiveBond(context);

            const couponDue =
                await tokenizedBond.couponDue(1);

            const gracePeriod =
                await tokenizedBond.GRACE_PERIOD();

            await time.increaseTo(
                couponDue + gracePeriod - 10n
            );

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .markCouponDefault(1)
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "DefaultNotEligible"
            );
        });

        it("records coupon default after the grace period", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            await prepareActiveBond(context);

            const couponDue =
                await tokenizedBond.couponDue(1);

            const gracePeriod =
                await tokenizedBond.GRACE_PERIOD();

            await time.increaseTo(
                couponDue + gracePeriod
            );

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .markCouponDefault(1)
            ).to.emit(
                tokenizedBond,
                "CouponDefaultRecorded"
            );

            expect(
                await tokenizedBond
                    .couponDefaulted(1)
            ).to.equal(true);

            expect(
                await tokenizedBond
                    .couponDefaultedAt(1)
            ).to.be.greaterThan(0n);

            expect(
                await tokenizedBond.isDefaulted()
            ).to.equal(true);

            expect(
                await tokenizedBond.lifecycle()
            ).to.equal(3n);
        });

        it("rejects coupon default when the obligation was funded", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveBond(context);

            await fundCoupon(
                context,
                1,
                couponRequired
            );

            const couponDue =
                await tokenizedBond.couponDue(1);

            const gracePeriod =
                await tokenizedBond.GRACE_PERIOD();

            await time.increaseTo(
                couponDue + gracePeriod
            );

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .markCouponDefault(1)
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "DefaultNotEligible"
            );
        });

        it("rejects recording the same coupon default twice", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            await prepareActiveBond(context);

            const couponDue =
                await tokenizedBond.couponDue(1);

            const gracePeriod =
                await tokenizedBond.GRACE_PERIOD();

            await time.increaseTo(
                couponDue + gracePeriod
            );

            await tokenizedBond
                .connect(outsider)
                .markCouponDefault(1);

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .markCouponDefault(1)
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "DefaultAlreadyRecorded"
            );
        });

        it("cures coupon default when issuer funds late", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveBond(context);

            const couponDue =
                await tokenizedBond.couponDue(1);

            const gracePeriod =
                await tokenizedBond.GRACE_PERIOD();

            await time.increaseTo(
                couponDue + gracePeriod
            );

            await tokenizedBond
                .connect(outsider)
                .markCouponDefault(1);

            const defaultTimestamp =
                await tokenizedBond
                    .couponDefaultedAt(1);

            await expect(
                fundCoupon(
                    context,
                    1,
                    couponRequired
                )
            ).to.emit(
                tokenizedBond,
                "DefaultCured"
            );

            expect(
                await tokenizedBond
                    .couponDefaulted(1)
            ).to.equal(false);

            expect(
                await tokenizedBond
                    .couponDefaultedAt(1)
            ).to.equal(defaultTimestamp);

            expect(
                await tokenizedBond.isDefaulted()
            ).to.equal(false);
        });

        it("tracks coupon period 2 default independently", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            const {
                couponRequired,
            } = await prepareActiveBond(context);

            await fundCoupon(
                context,
                1,
                couponRequired
            );

            const couponDue2 =
                await tokenizedBond.couponDue(2);

            const gracePeriod =
                await tokenizedBond.GRACE_PERIOD();

            await time.increaseTo(
                couponDue2 + gracePeriod
            );

            await tokenizedBond
                .connect(outsider)
                .markCouponDefault(2);

            expect(
                await tokenizedBond
                    .couponDefaulted(1)
            ).to.equal(false);

            expect(
                await tokenizedBond
                    .couponDefaulted(2)
            ).to.equal(true);
        });

        it("rejects principal default before the grace period expires", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            await prepareActiveBond(context);

            const maturity =
                await tokenizedBond.maturity();

            const gracePeriod =
                await tokenizedBond.GRACE_PERIOD();

            await time.increaseTo(
                maturity + gracePeriod - 10n
            );

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .markPrincipalDefault()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "DefaultNotEligible"
            );
        });

        it("records principal default and synchronizes maturity", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            await prepareActiveBond(context);

            const maturity =
                await tokenizedBond.maturity();

            const gracePeriod =
                await tokenizedBond.GRACE_PERIOD();

            await time.increaseTo(
                maturity + gracePeriod
            );

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .markPrincipalDefault()
            ).to.emit(
                tokenizedBond,
                "PrincipalDefaultRecorded"
            );

            expect(
                await tokenizedBond
                    .principalDefaulted()
            ).to.equal(true);

            expect(
                await tokenizedBond
                    .principalDefaultedAt()
            ).to.be.greaterThan(0n);

            expect(
                await tokenizedBond.lifecycle()
            ).to.equal(4n);

            expect(
                await tokenizedBond.isDefaulted()
            ).to.equal(true);
        });

        it("rejects principal default when principal was funded", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            const {
                principalRequired,
            } = await prepareActiveBond(context);

            await fundPrincipal(
                context,
                principalRequired
            );

            const maturity =
                await tokenizedBond.maturity();

            const gracePeriod =
                await tokenizedBond.GRACE_PERIOD();

            await time.increaseTo(
                maturity + gracePeriod
            );

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .markPrincipalDefault()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "DefaultNotEligible"
            );
        });

        it("cures principal default when issuer funds late", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            const {
                principalRequired,
            } = await prepareActiveBond(context);

            const maturity =
                await tokenizedBond.maturity();

            const gracePeriod =
                await tokenizedBond.GRACE_PERIOD();

            await time.increaseTo(
                maturity + gracePeriod
            );

            await tokenizedBond
                .connect(outsider)
                .markPrincipalDefault();

            const defaultTimestamp =
                await tokenizedBond
                    .principalDefaultedAt();

            await expect(
                fundPrincipal(
                    context,
                    principalRequired
                )
            ).to.emit(
                tokenizedBond,
                "DefaultCured"
            );

            expect(
                await tokenizedBond
                    .principalDefaulted()
            ).to.equal(false);

            expect(
                await tokenizedBond
                    .principalDefaultedAt()
            ).to.equal(defaultTimestamp);

            expect(
                await tokenizedBond.isDefaulted()
            ).to.equal(false);
        });
    });

    describe("Closing lifecycle", function () {
        async function prepareFailedBond(context) {
            const {
                admin,
                issuer,
                investor1,
                investor2,
                paymentToken,
                tokenizedBond,
            } = context;

            const quantity1 = 20n;
            const quantity2 = 30n;

            for (const investor of [
                investor1,
                investor2,
            ]) {
                await tokenizedBond
                    .connect(admin)
                    .setWhitelist(
                        investor.address,
                        true
                    );
            }

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            for (const [investor, quantity] of [
                [investor1, quantity1],
                [investor2, quantity2],
            ]) {
                await paymentToken
                    .connect(investor)
                    .approve(
                        await tokenizedBond.getAddress(),
                        quantity * ISSUE_PRICE
                    );

                await tokenizedBond
                    .connect(investor)
                    .subscribe(quantity);
            }

            const deadline =
                await tokenizedBond
                    .subscriptionDeadline();

            await time.increaseTo(deadline);
            await tokenizedBond.finalizeOffering();
        }

        async function prepareCompletedBond(context) {
            const {
                admin,
                issuer,
                investor1,
                investor2,
                paymentToken,
                tokenizedBond,
            } = context;

            const quantity1 = 30n;
            const quantity2 = 40n;
            const totalQuantity =
                quantity1 + quantity2;

            for (const investor of [
                investor1,
                investor2,
            ]) {
                await tokenizedBond
                    .connect(admin)
                    .setWhitelist(
                        investor.address,
                        true
                    );
            }

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            for (const [investor, quantity] of [
                [investor1, quantity1],
                [investor2, quantity2],
            ]) {
                await paymentToken
                    .connect(investor)
                    .approve(
                        await tokenizedBond.getAddress(),
                        quantity * ISSUE_PRICE
                    );

                await tokenizedBond
                    .connect(investor)
                    .subscribe(quantity);
            }

            const deadline =
                await tokenizedBond
                    .subscriptionDeadline();

            await time.increaseTo(deadline);
            await tokenizedBond.finalizeOffering();

            await tokenizedBond
                .connect(issuer)
                .withdrawProceeds();

            const couponRequired =
                totalQuantity * COUPON_PER_PERIOD;

            const principalRequired =
                totalQuantity * FACE_VALUE;

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(1);

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(2);

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    principalRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositPrincipal();

            const maturity =
                await tokenizedBond.maturity();

            await time.increaseTo(maturity);

            for (const investor of [
                investor1,
                investor2,
            ]) {
                await tokenizedBond
                    .connect(investor)
                    .claimCoupon(1);

                await tokenizedBond
                    .connect(investor)
                    .claimCoupon(2);

                await tokenizedBond
                    .connect(investor)
                    .redeemPrincipal();
            }
        }

        it("rejects closing an active bond before obligations are completed", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            const {
                admin,
                issuer,
                investor1,
                paymentToken,
            } = context;

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor1.address,
                    true
                );

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            const quantity = 60n;

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    quantity * ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(quantity);

            const deadline =
                await tokenizedBond
                    .subscriptionDeadline();

            await time.increaseTo(deadline);
            await tokenizedBond.finalizeOffering();

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .closeBond()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "CloseConditionsNotMet"
            );
        });

        it("rejects closing a failed bond before every refund", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                outsider,
                tokenizedBond,
            } = context;

            await prepareFailedBond(context);

            await tokenizedBond
                .connect(investor1)
                .claimRefund();

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .closeBond()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "CloseConditionsNotMet"
            );
        });

        it("allows any account to close a failed bond after every refund", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                investor2,
                outsider,
                tokenizedBond,
            } = context;

            await prepareFailedBond(context);

            await tokenizedBond
                .connect(investor1)
                .claimRefund();

            await tokenizedBond
                .connect(investor2)
                .claimRefund();

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .closeBond()
            ).to.emit(
                tokenizedBond,
                "BondClosed"
            );

            expect(
                await tokenizedBond.lifecycle()
            ).to.equal(5n);
        });

        it("allows any account to close a fully completed successful bond", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                outsider,
                tokenizedBond,
            } = context;

            await prepareCompletedBond(context);

            expect(
                await tokenizedBond.canClose()
            ).to.equal(true);

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .closeBond()
            ).to.emit(
                tokenizedBond,
                "BondClosed"
            );

            expect(
                await tokenizedBond.lifecycle()
            ).to.equal(5n);
        });

        it("rejects closing the bond twice", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                investor1,
                investor2,
                outsider,
                tokenizedBond,
            } = context;

            await prepareFailedBond(context);

            await tokenizedBond
                .connect(investor1)
                .claimRefund();

            await tokenizedBond
                .connect(investor2)
                .claimRefund();

            await tokenizedBond
                .connect(outsider)
                .closeBond();

            await expect(
                tokenizedBond
                    .connect(outsider)
                    .closeBond()
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "AlreadyClosed"
            );
        });
    });

    describe("View functions and native token restriction", function () {
        async function prepareActiveBond(context) {
            const {
                admin,
                issuer,
                investor1,
                investor2,
                paymentToken,
                tokenizedBond,
            } = context;

            const quantity1 = 30n;
            const quantity2 = 40n;
            const totalQuantity =
                quantity1 + quantity2;

            for (const investor of [
                investor1,
                investor2,
            ]) {
                await tokenizedBond
                    .connect(admin)
                    .setWhitelist(
                        investor.address,
                        true
                    );
            }

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            for (const [investor, quantity] of [
                [investor1, quantity1],
                [investor2, quantity2],
            ]) {
                await paymentToken
                    .connect(investor)
                    .approve(
                        await tokenizedBond.getAddress(),
                        quantity * ISSUE_PRICE
                    );

                await tokenizedBond
                    .connect(investor)
                    .subscribe(quantity);
            }

            const deadline =
                await tokenizedBond
                    .subscriptionDeadline();

            await time.increaseTo(deadline);
            await tokenizedBond.finalizeOffering();

            await tokenizedBond
                .connect(issuer)
                .withdrawProceeds();

            return {
                quantity1,
                quantity2,
                totalQuantity,
                couponRequired:
                    totalQuantity * COUPON_PER_PERIOD,
                principalRequired:
                    totalQuantity * FACE_VALUE,
            };
        }

        it("returns the complete bond configuration", async function () {
            const {
                admin,
                issuer,
                paymentToken,
                bondToken,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            const info =
                await tokenizedBond.getBondInfo();

            expect(info.bondName).to.equal(
                "Demo Corporate Bond 2026"
            );

            expect(info.adminAddress).to.equal(
                admin.address
            );

            expect(info.issuerAddress).to.equal(
                issuer.address
            );

            expect(
                info.paymentTokenAddress
            ).to.equal(
                await paymentToken.getAddress()
            );

            expect(info.bondTokenAddress).to.equal(
                await bondToken.getAddress()
            );

            expect(info.faceValue).to.equal(
                FACE_VALUE
            );

            expect(info.issuePrice).to.equal(
                ISSUE_PRICE
            );

            expect(info.maxSupply).to.equal(100n);
            expect(info.minimumSubscription)
                .to.equal(60n);
            expect(info.couponPerPeriod).to.equal(
                COUPON_PER_PERIOD
            );
        });

        it("returns current offering information", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                tokenizedBond,
            } = context;

            const {
                totalQuantity,
            } = await prepareActiveBond(context);

            const info =
                await tokenizedBond.getOfferingInfo();

            expect(info.currentLifecycle).to.equal(3n);
            expect(info.paused).to.equal(false);
            expect(info.start).to.be.greaterThan(0n);
            expect(info.deadline).to.be.greaterThan(
                info.start
            );
            expect(info.finalizedTime).to.be.greaterThan(
                0n
            );
            expect(info.subscribed).to.equal(
                totalQuantity
            );
            expect(info.raised).to.equal(
                totalQuantity * ISSUE_PRICE
            );
            expect(info.refunded).to.equal(0n);
            expect(
                info.proceedsAreWithdrawn
            ).to.equal(true);
        });

        it("reports refund information in an investor position", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                admin,
                issuer,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            const quantity = 20n;
            const payment = quantity * ISSUE_PRICE;

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor1.address,
                    true
                );

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    payment
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(quantity);

            const deadline =
                await tokenizedBond
                    .subscriptionDeadline();

            await time.increaseTo(deadline);
            await tokenizedBond.finalizeOffering();

            const position =
                await tokenizedBond
                    .getInvestorPosition(
                        investor1.address
                    );

            expect(position.isWhitelisted).to.equal(true);
            expect(position.quantitySubscribed)
                .to.equal(quantity);
            expect(position.amountPaid).to.equal(payment);
            expect(position.bondBalance).to.equal(quantity);
            expect(position.hasClaimedRefund)
                .to.equal(false);
            expect(position.refundableAmount)
                .to.equal(payment);
            expect(position.claimableCouponTotal)
                .to.equal(0n);
            expect(position.redeemablePrincipal)
                .to.equal(0n);

            expect(
                await tokenizedBond.getRefundAmount(
                    investor1.address
                )
            ).to.equal(payment);
        });

        it("updates claimable coupon views as conditions change", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                quantity1,
                couponRequired,
            } = await prepareActiveBond(context);

            expect(
                await tokenizedBond
                    .getClaimableCoupon(
                        investor1.address,
                        1
                    )
            ).to.equal(0n);

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(1);

            expect(
                await tokenizedBond
                    .getClaimableCoupon(
                        investor1.address,
                        1
                    )
            ).to.equal(0n);

            const couponDue =
                await tokenizedBond.couponDue(1);

            await time.increaseTo(couponDue);

            const expectedCoupon =
                quantity1 * COUPON_PER_PERIOD;

            expect(
                await tokenizedBond
                    .getClaimableCoupon(
                        investor1.address,
                        1
                    )
            ).to.equal(expectedCoupon);

            const position =
                await tokenizedBond
                    .getInvestorPosition(
                        investor1.address
                    );

            expect(position.claimableCouponTotal)
                .to.equal(expectedCoupon);

            await tokenizedBond
                .connect(investor1)
                .claimCoupon(1);

            expect(
                await tokenizedBond
                    .getClaimableCoupon(
                        investor1.address,
                        1
                    )
            ).to.equal(0n);
        });

        it("returns coupon information", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                quantity1,
                couponRequired,
            } = await prepareActiveBond(context);

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    couponRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositCoupon(1);

            const couponDue =
                await tokenizedBond.couponDue(1);

            await time.increaseTo(couponDue);

            await tokenizedBond
                .connect(investor1)
                .claimCoupon(1);

            const info =
                await tokenizedBond.getCouponInfo(1);

            expect(info.dueDate).to.equal(couponDue);
            expect(info.requiredAmount).to.equal(
                couponRequired
            );
            expect(info.fundedAmount).to.equal(
                couponRequired
            );
            expect(info.claimedAmount).to.equal(
                quantity1 * COUPON_PER_PERIOD
            );
            expect(info.isInDefault).to.equal(false);
            expect(info.defaultTimestamp).to.equal(0n);
        });

        it("returns principal information", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                principalRequired,
            } = await prepareActiveBond(context);

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    principalRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositPrincipal();

            const info =
                await tokenizedBond.getPrincipalInfo();

            expect(info.maturityDate).to.equal(
                await tokenizedBond.maturity()
            );
            expect(info.requiredAmount).to.equal(
                principalRequired
            );
            expect(info.fundedAmount).to.equal(
                principalRequired
            );
            expect(info.redeemedAmount).to.equal(0n);
            expect(info.isInDefault).to.equal(false);
            expect(info.defaultTimestamp).to.equal(0n);
        });

        it("updates redeemable principal views after all conditions are met", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                issuer,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            const {
                quantity1,
                couponRequired,
                principalRequired,
            } = await prepareActiveBond(context);

            for (const period of [1, 2]) {
                await paymentToken
                    .connect(issuer)
                    .approve(
                        await tokenizedBond.getAddress(),
                        couponRequired
                    );

                await tokenizedBond
                    .connect(issuer)
                    .depositCoupon(period);
            }

            await paymentToken
                .connect(issuer)
                .approve(
                    await tokenizedBond.getAddress(),
                    principalRequired
                );

            await tokenizedBond
                .connect(issuer)
                .depositPrincipal();

            const maturity =
                await tokenizedBond.maturity();

            await time.increaseTo(maturity);

            expect(
                await tokenizedBond.getPrincipalAmount(
                    investor1.address
                )
            ).to.equal(0n);

            await tokenizedBond
                .connect(investor1)
                .claimCoupon(1);

            await tokenizedBond
                .connect(investor1)
                .claimCoupon(2);

            const expectedPrincipal =
                quantity1 * FACE_VALUE;

            expect(
                await tokenizedBond.getPrincipalAmount(
                    investor1.address
                )
            ).to.equal(expectedPrincipal);

            const position =
                await tokenizedBond
                    .getInvestorPosition(
                        investor1.address
                    );

            expect(position.redeemablePrincipal)
                .to.equal(expectedPrincipal);

            await tokenizedBond
                .connect(investor1)
                .redeemPrincipal();

            expect(
                await tokenizedBond.getPrincipalAmount(
                    investor1.address
                )
            ).to.equal(0n);
        });

        it("reports subscription and finalization helper states", async function () {
            const context =
                await loadFixture(deployFixture);

            const {
                admin,
                issuer,
                investor1,
                paymentToken,
                tokenizedBond,
            } = context;

            expect(
                await tokenizedBond.isSubscriptionOpen()
            ).to.equal(false);

            expect(
                await tokenizedBond.canFinalize()
            ).to.equal(false);

            await tokenizedBond
                .connect(admin)
                .setWhitelist(
                    investor1.address,
                    true
                );

            await tokenizedBond
                .connect(issuer)
                .openSubscription();

            expect(
                await tokenizedBond.isSubscriptionOpen()
            ).to.equal(true);

            const quantity = 10n;

            await paymentToken
                .connect(investor1)
                .approve(
                    await tokenizedBond.getAddress(),
                    quantity * ISSUE_PRICE
                );

            await tokenizedBond
                .connect(investor1)
                .subscribe(quantity);

            expect(
                await tokenizedBond.canFinalize()
            ).to.equal(false);

            const deadline =
                await tokenizedBond
                    .subscriptionDeadline();

            await time.increaseTo(deadline);

            expect(
                await tokenizedBond.isSubscriptionOpen()
            ).to.equal(false);

            expect(
                await tokenizedBond.canFinalize()
            ).to.equal(true);

            await tokenizedBond.finalizeOffering();

            expect(
                await tokenizedBond.canFinalize()
            ).to.equal(false);
        });

        it("rejects invalid coupon periods in view functions", async function () {
            const {
                investor1,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await expect(
                tokenizedBond.getCouponInfo(0)
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InvalidCouponPeriod"
                )
                .withArgs(0n);

            await expect(
                tokenizedBond.getClaimableCoupon(
                    investor1.address,
                    3
                )
            )
                .to.be.revertedWithCustomError(
                    tokenizedBond,
                    "InvalidCouponPeriod"
                )
                .withArgs(3n);
        });

        it("rejects direct ETH transfers", async function () {
            const {
                outsider,
                tokenizedBond,
            } = await loadFixture(deployFixture);

            await expect(
                outsider.sendTransaction({
                    to: await tokenizedBond.getAddress(),
                    value: 1n,
                })
            ).to.be.revertedWithCustomError(
                tokenizedBond,
                "NativeTokenNotAccepted"
            );
        });
    });
    
});