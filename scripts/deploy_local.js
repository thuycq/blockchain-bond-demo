const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

const { ethers, artifacts } = hre;

const INVESTOR_INITIAL_BALANCE = ethers.parseEther("20000");
const ISSUER_INITIAL_BALANCE = ethers.parseEther("30000");

function ensureDirectory(directoryPath) {
    fs.mkdirSync(directoryPath, { recursive: true });
}

function writeJson(filePath, value) {
    ensureDirectory(path.dirname(filePath));
    fs.writeFileSync(filePath, JSON.stringify(value, null, 2));
}

async function waitForTransaction(transaction, label) {
    const receipt = await transaction.wait();
    console.log(`✓ ${label}: ${receipt.hash}`);
    return receipt;
}

async function exportAbis() {
    const abiDirectory = path.join(process.cwd(), "deployment", "abi");
    ensureDirectory(abiDirectory);

    for (const contractName of ["MockBondUSD", "BondToken", "TokenizedBond"]) {
        const artifact = await artifacts.readArtifact(contractName);
        writeJson(
            path.join(abiDirectory, `${contractName}.json`),
            {
                contractName,
                abi: artifact.abi,
            }
        );
    }

    console.log(`✓ ABI exported to ${abiDirectory}`);
}

async function snapshotState(paymentToken, bondToken, tokenizedBond) {
    const offering = await tokenizedBond.getOfferingInfo();

    return {
        lifecycle: offering.currentLifecycle.toString(),
        subscriptionPaused: offering.paused,
        subscriptionStart: offering.start.toString(),
        subscriptionDeadline: offering.deadline.toString(),
        finalizedAt: offering.finalizedTime.toString(),
        totalSubscribed: offering.subscribed.toString(),
        totalRaised: offering.raised.toString(),
        totalRefunded: offering.refunded.toString(),
        proceedsWithdrawn: offering.proceedsAreWithdrawn,
        bondTokenTotalSupply: (await bondToken.totalSupply()).toString(),
        contractBondUSDBalance: (
            await paymentToken.balanceOf(await tokenizedBond.getAddress())
        ).toString(),
    };
}

async function main() {
    const [deployer, admin, issuer, investor1, investor2, outsider] =
        await ethers.getSigners();

    console.log("\n=== DEPLOY LOCAL BASE ENVIRONMENT ===");
    console.log(`Network:  ${hre.network.name}`);
    console.log(`Deployer: ${deployer.address}`);
    console.log(`Admin:    ${admin.address}`);
    console.log(`Issuer:   ${issuer.address}`);
    console.log(`Investor1:${investor1.address}`);
    console.log(`Investor2:${investor2.address}`);
    console.log(`Outsider: ${outsider.address}\n`);

    const MockBondUSD = await ethers.getContractFactory("MockBondUSD", deployer);
    const paymentToken = await MockBondUSD.deploy(deployer.address);
    await paymentToken.waitForDeployment();
    console.log(`✓ MockBondUSD deployed: ${await paymentToken.getAddress()}`);

    const BondToken = await ethers.getContractFactory("BondToken", deployer);
    const bondToken = await BondToken.deploy(deployer.address);
    await bondToken.waitForDeployment();
    console.log(`✓ BondToken deployed:   ${await bondToken.getAddress()}`);

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
    console.log(`✓ TokenizedBond deployed: ${await tokenizedBond.getAddress()}`);

    await waitForTransaction(
        await bondToken.setController(await tokenizedBond.getAddress()),
        "Set TokenizedBond as BondToken controller"
    );

    await waitForTransaction(
        await bondToken.renounceOwnership(),
        "Renounce BondToken ownership"
    );

    await waitForTransaction(
        await paymentToken.mint(investor1.address, INVESTOR_INITIAL_BALANCE),
        "Mint 20,000 BONDUSD to Investor 1"
    );

    await waitForTransaction(
        await paymentToken.mint(investor2.address, INVESTOR_INITIAL_BALANCE),
        "Mint 20,000 BONDUSD to Investor 2"
    );

    await waitForTransaction(
        await paymentToken.mint(issuer.address, ISSUER_INITIAL_BALANCE),
        "Mint 30,000 BONDUSD to Issuer"
    );

    const network = await ethers.provider.getNetwork();
    const deploymentRecord = {
        schemaVersion: 1,
        scenario: "base",
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
        funding: {
            investor1BondUSD: INVESTOR_INITIAL_BALANCE.toString(),
            investor2BondUSD: INVESTOR_INITIAL_BALANCE.toString(),
            issuerBondUSD: ISSUER_INITIAL_BALANCE.toString(),
        },
        state: await snapshotState(paymentToken, bondToken, tokenizedBond),
    };

    const deploymentDirectory = path.join(process.cwd(), "deployment", "local");
    writeJson(path.join(deploymentDirectory, "base.json"), deploymentRecord);
    writeJson(path.join(deploymentDirectory, "latest.json"), deploymentRecord);
    await exportAbis();

    console.log("\n=== BASE DEPLOYMENT COMPLETE ===");
    console.log(`Saved: ${path.join(deploymentDirectory, "base.json")}`);
    console.log("Lifecycle remains Draft so this deployment can be inspected manually.");
}

main().catch((error) => {
    console.error("\nDeployment failed:");
    console.error(error);
    process.exitCode = 1;
});
