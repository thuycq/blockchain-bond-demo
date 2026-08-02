const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

const { ethers } = hre;

const SEPOLIA_CHAIN_ID = 11155111n;
const GREEN_KEY = "greenBond26";
const GREEN_NAME = "GreenBond26";
const GREEN_TOKEN_NAME = "Green Bond Token 2026";
const GREEN_SYMBOL = "GBOND26";

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, value) {
    fs.writeFileSync(
        filePath,
        JSON.stringify(value, null, 2),
        "utf8"
    );
}

async function receiptInfo(transaction, label) {
    console.log(`${label}: ${transaction.hash}`);

    const receipt = await transaction.wait();

    if (!receipt || receipt.status !== 1) {
        throw new Error(`${label} failed.`);
    }

    return {
        transactionHash: transaction.hash,
        blockNumber: receipt.blockNumber,
        gasUsed: receipt.gasUsed.toString(),
    };
}

async function deploymentInfo(contract, label) {
    const transaction = contract.deploymentTransaction();

    if (!transaction) {
        throw new Error(`${label} deployment transaction not found.`);
    }

    return receiptInfo(transaction, label);
}

async function main() {
    const projectRoot = path.join(__dirname, "..");
    const deploymentFile = path.join(
        projectRoot,
        "deployment",
        "bond_series.json"
    );

    if (!fs.existsSync(deploymentFile)) {
        throw new Error(`Missing deployment file: ${deploymentFile}`);
    }

    const series = readJson(deploymentFile);
    const network = await ethers.provider.getNetwork();

    if (network.chainId !== SEPOLIA_CHAIN_ID) {
        throw new Error(
            `Wrong network. Expected Sepolia ${SEPOLIA_CHAIN_ID}, ` +
            `received ${network.chainId}.`
        );
    }

    const [deployer] = await ethers.getSigners();
    const deployerAddress = await deployer.getAddress();
    const adminAddress = series.roles.admin;
    const issuerAddress = series.roles.issuer;
    const bondUsdAddress = series.paymentToken.address;

    if (
        ethers.getAddress(deployerAddress) !==
        ethers.getAddress(adminAddress)
    ) {
        throw new Error(
            `Deployer must be configured admin ${adminAddress}.`
        );
    }

    console.log("====================================================");
    console.log("REDEPLOY FRESH GREENBOND26 - SEPOLIA");
    console.log("====================================================");
    console.log(`Admin:   ${adminAddress}`);
    console.log(`Issuer:  ${issuerAddress}`);
    console.log(`BondUSD: ${bondUsdAddress}`);

    const ProjectBondToken = await ethers.getContractFactory(
        "ProjectBondToken"
    );

    const bondToken = await ProjectBondToken.deploy(
        GREEN_TOKEN_NAME,
        GREEN_SYMBOL,
        adminAddress
    );

    await bondToken.waitForDeployment();

    const bondTokenAddress = await bondToken.getAddress();
    const bondTokenDeployment = await deploymentInfo(
        bondToken,
        "GreenBond26 BondToken deploy"
    );

    const TokenizedBond = await ethers.getContractFactory(
        "TokenizedBond"
    );

    const tokenizedBond = await TokenizedBond.deploy(
        adminAddress,
        issuerAddress,
        bondUsdAddress,
        bondTokenAddress
    );

    await tokenizedBond.waitForDeployment();

    const tokenizedBondAddress = await tokenizedBond.getAddress();
    const tokenizedBondDeployment = await deploymentInfo(
        tokenizedBond,
        "GreenBond26 TokenizedBond deploy"
    );

    const setControllerTx = await bondToken.setController(
        tokenizedBondAddress
    );
    const setController = await receiptInfo(
        setControllerTx,
        "GreenBond26 setController"
    );

    const renounceTx = await bondToken.renounceOwnership();
    const renounceOwnership = await receiptInfo(
        renounceTx,
        "GreenBond26 renounceOwnership"
    );

    const [
        lifecycle,
        totalSubscribed,
        totalRaised,
        controller,
        owner,
    ] = await Promise.all([
        tokenizedBond.lifecycle(),
        tokenizedBond.totalSubscribed(),
        tokenizedBond.totalRaised(),
        bondToken.controller(),
        bondToken.owner(),
    ]);

    if (
        lifecycle !== 0n ||
        totalSubscribed !== 0n ||
        totalRaised !== 0n
    ) {
        throw new Error("Fresh GreenBond26 deployment is not clean.");
    }

    if (
        ethers.getAddress(controller) !==
        ethers.getAddress(tokenizedBondAddress)
    ) {
        throw new Error("GreenBond26 controller mismatch.");
    }

    if (owner !== ethers.ZeroAddress) {
        throw new Error("GreenBond26 BondToken ownership was not renounced.");
    }

    const replacement = {
        key: GREEN_KEY,
        displayName: GREEN_NAME,
        symbol: GREEN_SYMBOL,
        tokenName: GREEN_TOKEN_NAME,
        tokenDecimals: 0,
        redeployedAt: new Date().toISOString(),
        contracts: {
            BondToken: {
                address: bondTokenAddress,
                ...bondTokenDeployment,
            },
            TokenizedBond: {
                address: tokenizedBondAddress,
                ...tokenizedBondDeployment,
            },
        },
        configurationTransactions: {
            setController,
            renounceOwnership,
        },
    };

    const greenIndex = series.bonds.findIndex(
        (bond) => bond.key === GREEN_KEY
    );

    if (greenIndex < 0) {
        throw new Error("greenBond26 entry not found in bond_series.json.");
    }

    const oldGreen = series.bonds[greenIndex];

    series.bonds[greenIndex] = replacement;
    series.generatedAt = new Date().toISOString();
    series.lastReplacement = {
        key: GREEN_KEY,
        oldBondToken: oldGreen.contracts.BondToken.address,
        oldTokenizedBond: oldGreen.contracts.TokenizedBond.address,
        newBondToken: bondTokenAddress,
        newTokenizedBond: tokenizedBondAddress,
    };

    writeJson(deploymentFile, series);

    console.log("\n====================================================");
    console.log("FRESH GREENBOND26 DEPLOYED");
    console.log("====================================================");
    console.log(`BondToken:     ${bondTokenAddress}`);
    console.log(`TokenizedBond: ${tokenizedBondAddress}`);
    console.log("Lifecycle:     Draft");
    console.log(`Updated:       ${deploymentFile}`);
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
