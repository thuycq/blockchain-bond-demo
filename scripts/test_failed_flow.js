const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

const { ethers } = hre;

const ISSUE_PRICE = ethers.parseEther("100");
const INVESTOR_INITIAL_BALANCE = ethers.parseEther("20000");
const ISSUER_INITIAL_BALANCE = ethers.parseEther("30000");
const QUANTITY_1 = 20n;
const QUANTITY_2 = 30n;

function ensureDirectory(directoryPath) {
    fs.mkdirSync(directoryPath, { recursive: true });
}

function writeJson(filePath, value) {
    ensureDirectory(path.dirname(filePath));
    fs.writeFileSync(filePath, JSON.stringify(value, null, 2));
}

async function tx(transactionPromise, label) {
    const transaction = await transactionPromise;
    const receipt = await transaction.wait();
    console.log(`✓ ${label}`);
    return receipt;
}

async function increaseTo(timestamp) {
    const target = Number(timestamp);
    const latestBlock = await ethers.provider.getBlock("latest");

    if (target <= latestBlock.timestamp) {
        await ethers.provider.send("evm_mine", []);
        return;
    }

    await ethers.provider.send("evm_setNextBlockTimestamp", [target]);
    await ethers.provider.send("evm_mine", []);
}

function assertEqual(actual, expected, label) {
    if (actual !== expected) {
        throw new Error(
            `${label}: expected ${expected.toString()}, received ${actual.toString()}`
        );
    }
}

async function deploySuite() {
    const [deployer, admin, issuer, investor1, investor2, outsider] =
        await ethers.getSigners();

    const MockBondUSD = await ethers.getContractFactory("MockBondUSD", deployer);
    const paymentToken = await MockBondUSD.deploy(deployer.address);
    await paymentToken.waitForDeployment();

    const BondToken = await ethers.getContractFactory("BondToken", deployer);
    const bondToken = await BondToken.deploy(deployer.address);
    await bondToken.waitForDeployment();

    const TokenizedBond = await ethers.getContractFactory(
        "TokenizedBond",
        deployer
    );
    const tokenizedBond = await TokenizedBond.deploy(
        admin.address,
        issuer.address,
        await paymentToken.getAddress(),
        await bondToken.getAddress()
    );
    await tokenizedBond.waitForDeployment();

    await tx(
        bondToken.setController(await tokenizedBond.getAddress()),
        "Set BondToken controller"
    );
    await tx(bondToken.renounceOwnership(), "Renounce BondToken ownership");

    await tx(
        paymentToken.mint(investor1.address, INVESTOR_INITIAL_BALANCE),
        "Fund Investor 1"
    );
    await tx(
        paymentToken.mint(investor2.address, INVESTOR_INITIAL_BALANCE),
        "Fund Investor 2"
    );
    await tx(
        paymentToken.mint(issuer.address, ISSUER_INITIAL_BALANCE),
        "Fund Issuer"
    );

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

async function saveScenario(context) {
    const {
        deployer,
        admin,
        issuer,
        investor1,
        investor2,
        outsider,
        paymentToken,
        bondToken,
        tokenizedBond,
    } = context;

    const network = await ethers.provider.getNetwork();
    const offering = await tokenizedBond.getOfferingInfo();

    const record = {
        schemaVersion: 1,
        scenario: "failed",
        createdAt: new Date().toISOString(),
        network: {
            hardhatNetworkName: hre.network.name,
            chainId: network.chainId.toString(),
        },
        contracts: {
            paymentToken: await paymentToken.getAddress(),
            bondToken: await bondToken.getAddress(),
            tokenizedBond: await tokenizedBond.getAddress(),
        },
        roles: {
            deployer: deployer.address,
            admin: admin.address,
            issuer: issuer.address,
            investor1: investor1.address,
            investor2: investor2.address,
            outsider: outsider.address,
        },
        state: {
            lifecycle: offering.currentLifecycle.toString(),
            totalSubscribed: offering.subscribed.toString(),
            totalRaised: offering.raised.toString(),
            totalRefunded: offering.refunded.toString(),
            proceedsWithdrawn: offering.proceedsAreWithdrawn,
            bondTokenTotalSupply: (await bondToken.totalSupply()).toString(),
            contractBondUSDBalance: (
                await paymentToken.balanceOf(await tokenizedBond.getAddress())
            ).toString(),
        },
    };

    const deploymentDirectory = path.join(process.cwd(), "deployment", "local");
    writeJson(path.join(deploymentDirectory, "failed.json"), record);
    writeJson(path.join(deploymentDirectory, "latest.json"), record);
}

async function main() {
    console.log("\n=== FAILED OFFERING FLOW ===");
    const context = await deploySuite();
    const {
        admin,
        issuer,
        investor1,
        investor2,
        outsider,
        paymentToken,
        bondToken,
        tokenizedBond,
    } = context;

    const tokenizedBondAddress = await tokenizedBond.getAddress();
    const totalQuantity = QUANTITY_1 + QUANTITY_2;
    const totalRaised = totalQuantity * ISSUE_PRICE;

    await tx(
        tokenizedBond.connect(admin).setWhitelist(investor1.address, true),
        "Whitelist Investor 1"
    );
    await tx(
        tokenizedBond.connect(admin).setWhitelist(investor2.address, true),
        "Whitelist Investor 2"
    );
    await tx(
        tokenizedBond.connect(issuer).openSubscription(),
        "Open subscription"
    );

    await tx(
        paymentToken
            .connect(investor1)
            .approve(tokenizedBondAddress, QUANTITY_1 * ISSUE_PRICE),
        "Investor 1 approves BONDUSD"
    );
    await tx(
        tokenizedBond.connect(investor1).subscribe(QUANTITY_1),
        "Investor 1 subscribes 20 bonds"
    );

    await tx(
        paymentToken
            .connect(investor2)
            .approve(tokenizedBondAddress, QUANTITY_2 * ISSUE_PRICE),
        "Investor 2 approves BONDUSD"
    );
    await tx(
        tokenizedBond.connect(investor2).subscribe(QUANTITY_2),
        "Investor 2 subscribes 30 bonds"
    );

    assertEqual(await tokenizedBond.totalSubscribed(), totalQuantity, "Subscribed");
    assertEqual(await tokenizedBond.totalRaised(), totalRaised, "Raised");

    await increaseTo(await tokenizedBond.subscriptionDeadline());
    await tx(
        tokenizedBond.connect(outsider).finalizeOffering(),
        "Finalize failed offering"
    );
    assertEqual(await tokenizedBond.lifecycle(), 2n, "Lifecycle Failed");

    await tx(
        tokenizedBond.connect(investor1).claimRefund(),
        "Investor 1 claims refund"
    );
    await tx(
        tokenizedBond.connect(investor2).claimRefund(),
        "Investor 2 claims refund"
    );

    assertEqual(await tokenizedBond.totalRefunded(), totalRaised, "Refunded");
    assertEqual(await bondToken.totalSupply(), 0n, "BondToken supply");
    assertEqual(
        await paymentToken.balanceOf(tokenizedBondAddress),
        0n,
        "Contract BONDUSD balance"
    );
    assertEqual(
        await paymentToken.balanceOf(investor1.address),
        INVESTOR_INITIAL_BALANCE,
        "Investor 1 restored balance"
    );
    assertEqual(
        await paymentToken.balanceOf(investor2.address),
        INVESTOR_INITIAL_BALANCE,
        "Investor 2 restored balance"
    );

    await tx(tokenizedBond.connect(outsider).closeBond(), "Close failed bond");
    assertEqual(await tokenizedBond.lifecycle(), 5n, "Lifecycle Closed");

    await saveScenario(context);

    console.log("\n=== FAILED FLOW COMPLETED ===");
    console.log(`Total subscribed: ${totalQuantity} bonds`);
    console.log(`Total refunded:   ${ethers.formatEther(totalRaised)} BONDUSD`);
    console.log("Final lifecycle:  Closed");
    console.log("Saved: deployment/local/failed.json");
}

main().catch((error) => {
    console.error("\nFailed-offering flow failed:");
    console.error(error);
    process.exitCode = 1;
});
