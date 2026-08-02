const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

const { ethers } = hre;

const SEPOLIA_CHAIN_ID = 11155111n;

const PROJECTS = [
    {
        key: "greenBond26",
        displayName: "GreenBond26",
        tokenName: "Green Bond Token 2026",
        symbol: "GBOND26",
    },
    {
        key: "energyBond26",
        displayName: "EnergyBond26",
        tokenName: "Energy Bond Token 2026",
        symbol: "EBOND26",
    },
];

function readJson(filePath) {
    return JSON.parse(
        fs.readFileSync(filePath, "utf8")
    );
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
        throw new Error(
            `${label} deployment transaction not found.`
        );
    }

    return receiptInfo(transaction, label);
}

async function deployFreshBond({
    project,
    adminAddress,
    issuerAddress,
    bondUsdAddress,
}) {
    console.log("\n====================================================");
    console.log(`REDEPLOYING FRESH ${project.displayName.toUpperCase()}`);
    console.log("====================================================");

    const ProjectBondToken = await ethers.getContractFactory(
        "ProjectBondToken"
    );

    const bondToken = await ProjectBondToken.deploy(
        project.tokenName,
        project.symbol,
        adminAddress
    );

    await bondToken.waitForDeployment();

    const bondTokenAddress = await bondToken.getAddress();
    const bondTokenDeployment = await deploymentInfo(
        bondToken,
        `${project.displayName} BondToken deploy`
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
        `${project.displayName} TokenizedBond deploy`
    );

    const setControllerTx = await bondToken.setController(
        tokenizedBondAddress
    );
    const setController = await receiptInfo(
        setControllerTx,
        `${project.displayName} setController`
    );

    const renounceTx = await bondToken.renounceOwnership();
    const renounceOwnership = await receiptInfo(
        renounceTx,
        `${project.displayName} renounceOwnership`
    );

    const [
        lifecycle,
        totalSubscribed,
        totalRaised,
        controller,
        owner,
        tokenName,
        tokenSymbol,
        tokenDecimals,
    ] = await Promise.all([
        tokenizedBond.lifecycle(),
        tokenizedBond.totalSubscribed(),
        tokenizedBond.totalRaised(),
        bondToken.controller(),
        bondToken.owner(),
        bondToken.name(),
        bondToken.symbol(),
        bondToken.decimals(),
    ]);

    if (
        lifecycle !== 0n ||
        totalSubscribed !== 0n ||
        totalRaised !== 0n
    ) {
        throw new Error(
            `${project.displayName} deployment is not clean.`
        );
    }

    if (
        ethers.getAddress(controller) !==
        ethers.getAddress(tokenizedBondAddress)
    ) {
        throw new Error(
            `${project.displayName} controller mismatch.`
        );
    }

    if (owner !== ethers.ZeroAddress) {
        throw new Error(
            `${project.displayName} BondToken ownership was not renounced.`
        );
    }

    return {
        key: project.key,
        displayName: project.displayName,
        symbol: tokenSymbol,
        tokenName,
        tokenDecimals: Number(tokenDecimals),
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
}

async function main() {
    const projectRoot = path.join(__dirname, "..");
    const deploymentFile = path.join(
        projectRoot,
        "deployment",
        "bond_series.json"
    );

    if (!fs.existsSync(deploymentFile)) {
        throw new Error(
            `Missing deployment file: ${deploymentFile}`
        );
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

    const paymentCode = await ethers.provider.getCode(
        bondUsdAddress
    );

    if (paymentCode === "0x") {
        throw new Error(
            `BondUSD contract not found at ${bondUsdAddress}.`
        );
    }

    console.log("====================================================");
    console.log("REDEPLOY GREENBOND26 + ENERGYBOND26 - SEPOLIA");
    console.log("====================================================");
    console.log(`Admin:   ${adminAddress}`);
    console.log(`Issuer:  ${issuerAddress}`);
    console.log(`BondUSD: ${bondUsdAddress}`);

    const replacements = [];

    for (const project of PROJECTS) {
        const existingIndex = series.bonds.findIndex(
            (bond) => bond.key === project.key
        );

        if (existingIndex < 0) {
            throw new Error(
                `${project.key} entry not found in bond_series.json.`
            );
        }

        const oldBond = series.bonds[existingIndex];
        const freshBond = await deployFreshBond({
            project,
            adminAddress,
            issuerAddress,
            bondUsdAddress,
        });

        series.bonds[existingIndex] = freshBond;

        replacements.push({
            key: project.key,
            oldBondToken:
                oldBond.contracts.BondToken.address,
            oldTokenizedBond:
                oldBond.contracts.TokenizedBond.address,
            newBondToken:
                freshBond.contracts.BondToken.address,
            newTokenizedBond:
                freshBond.contracts.TokenizedBond.address,
        });
    }

    series.generatedAt = new Date().toISOString();
    series.lastReplacements = replacements;

    writeJson(deploymentFile, series);

    console.log("\n====================================================");
    console.log("FRESH GREENBOND26 + ENERGYBOND26 DEPLOYED");
    console.log("====================================================");

    for (const replacement of replacements) {
        console.log(`\n${replacement.key}`);
        console.log(
            `  BondToken:     ${replacement.newBondToken}`
        );
        console.log(
            `  TokenizedBond: ${replacement.newTokenizedBond}`
        );
        console.log("  Lifecycle:     Draft");
    }

    console.log(`\nUpdated: ${deploymentFile}`);
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
