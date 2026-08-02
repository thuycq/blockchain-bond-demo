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
    {
        key: "eduBond26",
        displayName: "EduBond26",
        tokenName: "Education Bond Token 2026",
        symbol: "EDUB26",
    },
];

function readJson(filePath) {
    return JSON.parse(
        fs.readFileSync(filePath, "utf8")
    );
}

function writeJson(filePath, value) {
    fs.mkdirSync(
        path.dirname(filePath),
        { recursive: true }
    );

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

async function deployProjectBond({
    project,
    adminAddress,
    issuerAddress,
    bondUsdAddress,
}) {
    console.log("\n====================================================");
    console.log(`DEPLOYING ${project.displayName}`);
    console.log("====================================================");

    const ProjectBondToken =
        await ethers.getContractFactory(
            "ProjectBondToken"
        );

    const bondToken =
        await ProjectBondToken.deploy(
            project.tokenName,
            project.symbol,
            adminAddress
        );

    await bondToken.waitForDeployment();

    const bondTokenAddress =
        await bondToken.getAddress();

    const bondTokenDeployment =
        await deploymentInfo(
            bondToken,
            `${project.displayName} BondToken deploy`
        );

    const TokenizedBond =
        await ethers.getContractFactory(
            "TokenizedBond"
        );

    const tokenizedBond =
        await TokenizedBond.deploy(
            adminAddress,
            issuerAddress,
            bondUsdAddress,
            bondTokenAddress
        );

    await tokenizedBond.waitForDeployment();

    const tokenizedBondAddress =
        await tokenizedBond.getAddress();

    const tokenizedBondDeployment =
        await deploymentInfo(
            tokenizedBond,
            `${project.displayName} TokenizedBond deploy`
        );

    const setControllerTx =
        await bondToken.setController(
            tokenizedBondAddress
        );

    const setController =
        await receiptInfo(
            setControllerTx,
            `${project.displayName} setController`
        );

    const renounceTx =
        await bondToken.renounceOwnership();

    const renounceOwnership =
        await receiptInfo(
            renounceTx,
            `${project.displayName} renounceOwnership`
        );

    const [
        tokenName,
        tokenSymbol,
        tokenDecimals,
        tokenOwner,
        controller,
        lifecycle,
        totalSubscribed,
        totalRaised,
    ] = await Promise.all([
        bondToken.name(),
        bondToken.symbol(),
        bondToken.decimals(),
        bondToken.owner(),
        bondToken.controller(),
        tokenizedBond.lifecycle(),
        tokenizedBond.totalSubscribed(),
        tokenizedBond.totalRaised(),
    ]);

    if (tokenOwner !== ethers.ZeroAddress) {
        throw new Error(
            `${project.displayName}: BondToken owner was not renounced.`
        );
    }

    if (
        ethers.getAddress(controller) !==
        ethers.getAddress(tokenizedBondAddress)
    ) {
        throw new Error(
            `${project.displayName}: controller mismatch.`
        );
    }

    if (
        lifecycle !== 0n ||
        totalSubscribed !== 0n ||
        totalRaised !== 0n
    ) {
        throw new Error(
            `${project.displayName}: deployment is not clean.`
        );
    }

    console.log(`BondToken:     ${bondTokenAddress}`);
    console.log(`TokenizedBond: ${tokenizedBondAddress}`);
    console.log(`Token name:    ${tokenName}`);
    console.log(`Token symbol:  ${tokenSymbol}`);
    console.log(`Lifecycle:     Draft`);

    return {
        key: project.key,
        displayName: project.displayName,
        symbol: tokenSymbol,
        tokenName,
        tokenDecimals: Number(tokenDecimals),
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
    const deploymentDir = path.join(
        projectRoot,
        "deployment"
    );
    const baseFile = path.join(
        deploymentDir,
        "sepolia.json"
    );
    const outputFile = path.join(
        deploymentDir,
        "bond_series.json"
    );

    if (!fs.existsSync(baseFile)) {
        throw new Error(
            `Missing base deployment file: ${baseFile}`
        );
    }

    const base = readJson(baseFile);
    const network = await ethers.provider.getNetwork();

    if (network.chainId !== SEPOLIA_CHAIN_ID) {
        throw new Error(
            `Wrong network. Expected Sepolia ${SEPOLIA_CHAIN_ID}, ` +
            `received ${network.chainId}.`
        );
    }

    const [deployer] = await ethers.getSigners();
    const adminAddress = await deployer.getAddress();
    const issuerAddress = base.roles.issuer;
    const bondUsdAddress =
        base.contracts.BondUSDToken.address;

    if (
        ethers.getAddress(adminAddress) !==
        ethers.getAddress(base.roles.admin)
    ) {
        throw new Error(
            `Deployer must be configured admin ${base.roles.admin}.`
        );
    }

    const paymentCode =
        await ethers.provider.getCode(
            bondUsdAddress
        );

    if (paymentCode === "0x") {
        throw new Error(
            `BondUSD contract not found at ${bondUsdAddress}.`
        );
    }

    console.log("====================================================");
    console.log("DEPLOY THREE FRESH BOND OFFERINGS - SEPOLIA");
    console.log("====================================================");
    console.log(`Admin:   ${adminAddress}`);
    console.log(`Issuer:  ${issuerAddress}`);
    console.log(`BondUSD: ${bondUsdAddress}`);

    const freshBonds = [];

    for (const project of PROJECTS) {
        freshBonds.push(
            await deployProjectBond({
                project,
                adminAddress,
                issuerAddress,
                bondUsdAddress,
            })
        );
    }

    const originalBond = {
        key: "demoBond26",
        displayName: "DemoBond26",
        symbol: "DBOND26",
        tokenName: "Demo Corporate Bond Token 2026",
        contracts: {
            BondToken:
                base.contracts.BondToken,
            TokenizedBond:
                base.contracts.TokenizedBond,
        },
        configurationTransactions:
            base.configurationTransactions,
    };

    const series = {
        version: "v2-four-project-bonds",
        network: "sepolia",
        chainId: Number(network.chainId),
        generatedAt: new Date().toISOString(),
        roles: base.roles,
        paymentToken:
            base.contracts.BondUSDToken,
        bonds: [
            originalBond,
            ...freshBonds,
        ],
    };

    writeJson(outputFile, series);

    console.log("\n====================================================");
    console.log("ALL THREE FRESH BONDS DEPLOYED");
    console.log("====================================================");
    console.log(`Saved: ${outputFile}`);

    for (const bond of freshBonds) {
        console.log(`\n${bond.displayName}`);
        console.log(
            `  BondToken:     ${bond.contracts.BondToken.address}`
        );
        console.log(
            `  TokenizedBond: ${bond.contracts.TokenizedBond.address}`
        );
    }
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
