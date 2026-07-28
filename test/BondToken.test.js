const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("BondToken", function () {
    let BondToken;
    let bondToken;

    let owner;
    let controller;
    let investor1;
    let investor2;
    let outsider;

    beforeEach(async function () {
        [owner, controller, investor1, investor2, outsider] =
            await ethers.getSigners();

        BondToken = await ethers.getContractFactory("BondToken");

        bondToken = await BondToken.deploy(owner.address);
        await bondToken.waitForDeployment();
    });

    async function configureController() {
        await bondToken
            .connect(owner)
            .setController(controller.address);
    }

    describe("Deployment and metadata", function () {
        it("Should deploy with the correct token metadata", async function () {
            expect(await bondToken.name()).to.equal(
                "Demo Corporate Bond Token 2026"
            );

            expect(await bondToken.symbol()).to.equal("DBOND26");
            expect(await bondToken.decimals()).to.equal(0);
        });

        it("Should initialise owner, controller and supply correctly", async function () {
            expect(await bondToken.owner()).to.equal(owner.address);
            expect(await bondToken.controller()).to.equal(
                ethers.ZeroAddress
            );

            expect(await bondToken.totalSupply()).to.equal(0n);
        });

        it("Should reject a zero initial owner", async function () {
            await expect(
                BondToken.deploy(ethers.ZeroAddress)
            )
                .to.be.revertedWithCustomError(
                    BondToken,
                    "OwnableInvalidOwner"
                )
                .withArgs(ethers.ZeroAddress);
        });
    });

    describe("Controller configuration", function () {
        it("Should allow the owner to set the controller", async function () {
            await expect(
                bondToken
                    .connect(owner)
                    .setController(controller.address)
            )
                .to.emit(bondToken, "ControllerSet")
                .withArgs(controller.address);

            expect(await bondToken.controller()).to.equal(
                controller.address
            );
        });

        it("Should reject a zero controller address", async function () {
            await expect(
                bondToken
                    .connect(owner)
                    .setController(ethers.ZeroAddress)
            ).to.be.revertedWithCustomError(
                bondToken,
                "ZeroAddress"
            );
        });

        it("Should reject a non-owner setting the controller", async function () {
            await expect(
                bondToken
                    .connect(outsider)
                    .setController(controller.address)
            )
                .to.be.revertedWithCustomError(
                    bondToken,
                    "OwnableUnauthorizedAccount"
                )
                .withArgs(outsider.address);
        });

        it("Should prevent the controller from being set twice", async function () {
            await configureController();

            await expect(
                bondToken
                    .connect(owner)
                    .setController(outsider.address)
            )
                .to.be.revertedWithCustomError(
                    bondToken,
                    "ControllerAlreadySet"
                )
                .withArgs(controller.address);
        });
    });

    describe("Minting", function () {
        beforeEach(async function () {
            await configureController();
        });

        it("Should allow the controller to mint BondToken", async function () {
            const quantity = 10n;

            await expect(
                bondToken
                    .connect(controller)
                    .mint(investor1.address, quantity)
            )
                .to.emit(bondToken, "Transfer")
                .withArgs(
                    ethers.ZeroAddress,
                    investor1.address,
                    quantity
                );

            expect(
                await bondToken.balanceOf(investor1.address)
            ).to.equal(quantity);

            expect(await bondToken.totalSupply()).to.equal(quantity);
        });

        it("Should reject minting by a non-controller", async function () {
            await expect(
                bondToken
                    .connect(outsider)
                    .mint(investor1.address, 10n)
            )
                .to.be.revertedWithCustomError(
                    bondToken,
                    "NotController"
                )
                .withArgs(outsider.address);
        });

        it("Should reject minting to the zero address", async function () {
            await expect(
                bondToken
                    .connect(controller)
                    .mint(ethers.ZeroAddress, 10n)
            ).to.be.revertedWithCustomError(
                bondToken,
                "ZeroAddress"
            );
        });

        it("Should reject minting a zero quantity", async function () {
            await expect(
                bondToken
                    .connect(controller)
                    .mint(investor1.address, 0n)
            ).to.be.revertedWithCustomError(
                bondToken,
                "ZeroAmount"
            );
        });
    });

    describe("Burning", function () {
        beforeEach(async function () {
            await configureController();

            await bondToken
                .connect(controller)
                .mint(investor1.address, 10n);
        });

        it("Should allow the controller to burn BondToken", async function () {
            const burnQuantity = 4n;

            await expect(
                bondToken
                    .connect(controller)
                    .burn(investor1.address, burnQuantity)
            )
                .to.emit(bondToken, "Transfer")
                .withArgs(
                    investor1.address,
                    ethers.ZeroAddress,
                    burnQuantity
                );

            expect(
                await bondToken.balanceOf(investor1.address)
            ).to.equal(6n);

            expect(await bondToken.totalSupply()).to.equal(6n);
        });

        it("Should reject burning by a non-controller", async function () {
            await expect(
                bondToken
                    .connect(outsider)
                    .burn(investor1.address, 1n)
            )
                .to.be.revertedWithCustomError(
                    bondToken,
                    "NotController"
                )
                .withArgs(outsider.address);
        });

        it("Should reject invalid burn parameters", async function () {
            await expect(
                bondToken
                    .connect(controller)
                    .burn(ethers.ZeroAddress, 1n)
            ).to.be.revertedWithCustomError(
                bondToken,
                "ZeroAddress"
            );

            await expect(
                bondToken
                    .connect(controller)
                    .burn(investor1.address, 0n)
            ).to.be.revertedWithCustomError(
                bondToken,
                "ZeroAmount"
            );

            await expect(
                bondToken
                    .connect(controller)
                    .burn(investor1.address, 11n)
            ).to.be.revertedWithCustomError(
                bondToken,
                "ERC20InsufficientBalance"
            );
        });
    });

    describe("Non-transferable restrictions", function () {
        beforeEach(async function () {
            await configureController();

            await bondToken
                .connect(controller)
                .mint(investor1.address, 10n);
        });

        it("Should block direct transfers", async function () {
            await expect(
                bondToken
                    .connect(investor1)
                    .transfer(investor2.address, 1n)
            ).to.be.revertedWithCustomError(
                bondToken,
                "NonTransferable"
            );
        });

        it("Should block approvals", async function () {
            await expect(
                bondToken
                    .connect(investor1)
                    .approve(outsider.address, 1n)
            ).to.be.revertedWithCustomError(
                bondToken,
                "ApprovalDisabled"
            );
        });

        it("Should block transferFrom", async function () {
            await expect(
                bondToken
                    .connect(outsider)
                    .transferFrom(
                        investor1.address,
                        investor2.address,
                        1n
                    )
            ).to.be.revertedWithCustomError(
                bondToken,
                "NonTransferable"
            );
        });
    });

    describe("Ownership renouncement", function () {
        it("Should keep the controller operational after ownership is renounced", async function () {
            await configureController();

            await bondToken
                .connect(owner)
                .renounceOwnership();

            expect(await bondToken.owner()).to.equal(
                ethers.ZeroAddress
            );

            expect(await bondToken.controller()).to.equal(
                controller.address
            );

            await bondToken
                .connect(controller)
                .mint(investor1.address, 5n);

            expect(
                await bondToken.balanceOf(investor1.address)
            ).to.equal(5n);

            await bondToken
                .connect(controller)
                .burn(investor1.address, 2n);

            expect(
                await bondToken.balanceOf(investor1.address)
            ).to.equal(3n);

            expect(await bondToken.totalSupply()).to.equal(3n);
        });
    });
});