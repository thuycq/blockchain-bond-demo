const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

const { ethers, artifacts } = hre;

// ============================================================
// SEPOLIA CONFIGURATION
// ============================================================

const EXPECTED_ADMIN =
    "0x09428D10764503E9158374e556398b409d37381E";

const ISSUER_ADDRESS =
    "0x9D4C235100Ddfd5d61326769e16b2BB9dE04074e";

const BOND_USD_ADDRESS =
    "0xcDe41c009D3fFd58CaA9a4CC561155c2616B7D7D";

const SEPOLIA_CHAIN_ID = 11155111n;

const BOND_USD_VALIDATION_ABI = [
    "function name() external view returns (string)",
    "function symbol() external view returns (string)",
    "function decimals() external view returns (uint8)",
    "function owner() external view returns (address)",
    "function totalSupply() external view returns (uint256)",
];

// ============================================================
// HELPERS
// ============================================================

function assertAddressEqual(actual, expected, label) {
    const actualChecksum = ethers.getAddress(actual);
    const expectedChecksum = ethers.getAddress(expected);

    if (actualChecksum !== expectedChecksum) {
        throw new Error(
            `${label} mismatch.\n` +
            `Expected: ${expectedChecksum}\n` +
            `Actual:   ${actualChecksum}`
        );
    }
}

function assertEqual(actual, expected, label) {
    if (actual !== expected) {
        throw new Error(
            `${label} mismatch.\n` +
            `Expected: ${expected}\n` +
            `Actual:   ${actual}`
        );
    }
}

async function waitForSuccess(transaction, label) {
    console.log(`${label} tx:`, transaction.hash);

    const receipt = await transaction.wait();

    if (!receipt || receipt.status !== 1) {
        throw new Error(`${label} transaction failed.`);
    }

    return {
        transactionHash: transaction.hash,
        blockNumber: receipt.blockNumber,
        gasUsed: receipt.gasUsed.toString(),
    };
}

async function getDeploymentDetails(contract) {
    const deploymentTx =
        contract.deploymentTransaction();

    if (!deploymentTx) {
        throw new Error(
            "Deployment transaction was not found."
        );
    }

    const receipt = await deploymentTx.wait();

    if (!receipt || receipt.status !== 1) {
        throw new Error(
            "Contract deployment transaction failed."
        );
    }

    return {
        transactionHash: deploymentTx.hash,
        blockNumber: receipt.blockNumber,
        gasUsed: receipt.gasUsed.toString(),
    };
}

function saveJson(filePath, data) {
    fs.mkdirSync(
        path.dirname(filePath),
        { recursive: true }
    );

    fs.writeFileSync(
        filePath,
        JSON.stringify(data, null, 2),
        "utf8"
    );
}

function archiveExistingDeployment(
    deploymentFile,
    deploymentDirectory
) {
    if (!fs.existsSync(deploymentFile)) {
        return null;
    }

    const archiveDirectory =
        path.join(
            deploymentDirectory,
            "archive"
        );

    fs.mkdirSync(
        archiveDirectory,
        { recursive: true }
    );

    const timestamp =
        new Date()
            .toISOString()
            .replace(/[:.]/g, "-");

    const archiveFile =
        path.join(
            archiveDirectory,
            `sepolia-${timestamp}.json`
        );

    fs.copyFileSync(
        deploymentFile,
        archiveFile
    );

    return archiveFile;
}

// ============================================================
// MAIN
// ============================================================

async function main() {
    console.log(
        "===================================================="
    );
    console.log(
        "BOND 7 - CLEAN V2 DEPLOYMENT TO ETHEREUM SEPOLIA"
    );
    console.log(
        "===================================================="
    );

    // --------------------------------------------------------
    // 1. Validate network and deployer
    // --------------------------------------------------------

    const network =
        await ethers.provider.getNetwork();

    if (network.chainId !== SEPOLIA_CHAIN_ID) {
        throw new Error(
            `Wrong network. Expected Sepolia chain ID ` +
            `${SEPOLIA_CHAIN_ID}, received ` +
            `${network.chainId}.`
        );
    }

    const [deployer] =
        await ethers.getSigners();

    if (!deployer) {
        throw new Error(
            "No deployer signer is available."
        );
    }

    const adminAddress =
        await deployer.getAddress();

    const deployerBalance =
        await ethers.provider.getBalance(
            adminAddress
        );

    assertAddressEqual(
        adminAddress,
        EXPECTED_ADMIN,
        "Deployer/Admin address"
    );

    if (
        ethers.getAddress(adminAddress) ===
        ethers.getAddress(ISSUER_ADDRESS)
    ) {
        throw new Error(
            "Admin and Issuer must be different."
        );
    }

    console.log("\n1. Network and roles");
    console.log("Network:          Sepolia");
    console.log(
        "Chain ID:        ",
        network.chainId.toString()
    );
    console.log(
        "Deployer/Admin:  ",
        adminAddress
    );
    console.log(
        "Issuer:          ",
        ISSUER_ADDRESS
    );
    console.log(
        "Deployer balance:",
        ethers.formatEther(deployerBalance),
        "Sepolia ETH"
    );

    // --------------------------------------------------------
    // 2. Validate existing BondUSD
    // --------------------------------------------------------

    const bondUsdCode =
        await ethers.provider.getCode(
            BOND_USD_ADDRESS
        );

    if (bondUsdCode === "0x") {
        throw new Error(
            `No contract exists at BondUSD address: ` +
            `${BOND_USD_ADDRESS}`
        );
    }

    const bondUSD =
        new ethers.Contract(
            BOND_USD_ADDRESS,
            BOND_USD_VALIDATION_ABI,
            deployer
        );

    const [
        bondUsdName,
        bondUsdSymbol,
        bondUsdDecimals,
        bondUsdOwner,
        bondUsdTotalSupply,
    ] = await Promise.all([
        bondUSD.name(),
        bondUSD.symbol(),
        bondUSD.decimals(),
        bondUSD.owner(),
        bondUSD.totalSupply(),
    ]);

    console.log(
        "\n2. Existing BondUSD validation"
    );
    console.log(
        "BondUSD address:  ",
        BOND_USD_ADDRESS
    );
    console.log(
        "Name:             ",
        bondUsdName
    );
    console.log(
        "Symbol:           ",
        bondUsdSymbol
    );
    console.log(
        "Decimals:         ",
        bondUsdDecimals.toString()
    );
    console.log(
        "Owner:            ",
        bondUsdOwner
    );
    console.log(
        "Total supply:     ",
        ethers.formatUnits(
            bondUsdTotalSupply,
            bondUsdDecimals
        ),
        bondUsdSymbol
    );

    // --------------------------------------------------------
    // 3. Deploy BondToken
    // --------------------------------------------------------

    console.log(
        "\n3. Deploying BondToken..."
    );

    const BondToken =
        await ethers.getContractFactory(
            "BondToken"
        );

    const bondToken =
        await BondToken.deploy(
            adminAddress
        );

    await bondToken.waitForDeployment();

    const bondTokenAddress =
        await bondToken.getAddress();

    const bondTokenDeployment =
        await getDeploymentDetails(
            bondToken
        );

    console.log(
        "BondToken deployed to:",
        bondTokenAddress
    );

    const [
        bondTokenOwnerBefore,
        controllerBefore,
        supplyBefore,
    ] = await Promise.all([
        bondToken.owner(),
        bondToken.controller(),
        bondToken.totalSupply(),
    ]);

    assertAddressEqual(
        bondTokenOwnerBefore,
        adminAddress,
        "BondToken initial owner"
    );

    assertEqual(
        controllerBefore,
        ethers.ZeroAddress,
        "BondToken initial controller"
    );

    assertEqual(
        supplyBefore,
        0n,
        "BondToken initial supply"
    );

    // --------------------------------------------------------
    // 4. Deploy TokenizedBond
    // --------------------------------------------------------

    console.log(
        "\n4. Deploying TokenizedBond..."
    );

    const TokenizedBond =
        await ethers.getContractFactory(
            "TokenizedBond"
        );

    const tokenizedBond =
        await TokenizedBond.deploy(
            adminAddress,
            ISSUER_ADDRESS,
            BOND_USD_ADDRESS,
            bondTokenAddress
        );

    await tokenizedBond.waitForDeployment();

    const tokenizedBondAddress =
        await tokenizedBond.getAddress();

    const tokenizedBondDeployment =
        await getDeploymentDetails(
            tokenizedBond
        );

    console.log(
        "TokenizedBond deployed to:",
        tokenizedBondAddress
    );

    const [
        configuredAdmin,
        configuredIssuer,
        configuredPaymentToken,
        configuredBondToken,
    ] = await Promise.all([
        tokenizedBond.admin(),
        tokenizedBond.issuer(),
        tokenizedBond.paymentToken(),
        tokenizedBond.bondToken(),
    ]);

    assertAddressEqual(
        configuredAdmin,
        adminAddress,
        "TokenizedBond admin"
    );

    assertAddressEqual(
        configuredIssuer,
        ISSUER_ADDRESS,
        "TokenizedBond issuer"
    );

    assertAddressEqual(
        configuredPaymentToken,
        BOND_USD_ADDRESS,
        "TokenizedBond payment token"
    );

    assertAddressEqual(
        configuredBondToken,
        bondTokenAddress,
        "TokenizedBond bond token"
    );

    // --------------------------------------------------------
    // 5. Configure BondToken controller
    // --------------------------------------------------------

    console.log(
        "\n5. Setting TokenizedBond as controller..."
    );

    const setControllerTx =
        await bondToken.setController(
            tokenizedBondAddress
        );

    const setControllerResult =
        await waitForSuccess(
            setControllerTx,
            "setController"
        );

    assertAddressEqual(
        await bondToken.controller(),
        tokenizedBondAddress,
        "BondToken controller"
    );

    // --------------------------------------------------------
    // 6. Renounce BondToken ownership
    // --------------------------------------------------------

    console.log(
        "\n6. Renouncing BondToken ownership..."
    );

    const renounceTx =
        await bondToken
            .renounceOwnership();

    const renounceResult =
        await waitForSuccess(
            renounceTx,
            "renounceOwnership"
        );

    assertEqual(
        await bondToken.owner(),
        ethers.ZeroAddress,
        "BondToken final owner"
    );

    // --------------------------------------------------------
    // 7. Validate clean initial state
    // --------------------------------------------------------

    const [
        lifecycle,
        subscriptionPaused,
        subscriptionStart,
        subscriptionDeadline,
        totalSubscribed,
        totalRaised,
        totalRefunded,
        proceedsWithdrawn,
        applicantCount,
        finalBondSupply,
        finalController,
        finalOwner,
    ] = await Promise.all([
        tokenizedBond.lifecycle(),
        tokenizedBond.subscriptionPaused(),
        tokenizedBond.subscriptionStart(),
        tokenizedBond.subscriptionDeadline(),
        tokenizedBond.totalSubscribed(),
        tokenizedBond.totalRaised(),
        tokenizedBond.totalRefunded(),
        tokenizedBond.proceedsWithdrawn(),
        tokenizedBond
            .getWhitelistApplicantCount(),
        bondToken.totalSupply(),
        bondToken.controller(),
        bondToken.owner(),
    ]);

    assertEqual(
        lifecycle,
        0n,
        "Initial lifecycle"
    );

    assertEqual(
        subscriptionPaused,
        false,
        "Initial subscriptionPaused"
    );

    assertEqual(
        subscriptionStart,
        0n,
        "Initial subscriptionStart"
    );

    assertEqual(
        subscriptionDeadline,
        0n,
        "Initial subscriptionDeadline"
    );

    assertEqual(
        totalSubscribed,
        0n,
        "Initial totalSubscribed"
    );

    assertEqual(
        totalRaised,
        0n,
        "Initial totalRaised"
    );

    assertEqual(
        totalRefunded,
        0n,
        "Initial totalRefunded"
    );

    assertEqual(
        proceedsWithdrawn,
        false,
        "Initial proceedsWithdrawn"
    );

    assertEqual(
        applicantCount,
        0n,
        "Initial whitelist applicant count"
    );

    assertEqual(
        finalBondSupply,
        0n,
        "Initial BondToken supply"
    );

    assertAddressEqual(
        finalController,
        tokenizedBondAddress,
        "Final controller"
    );

    assertEqual(
        finalOwner,
        ethers.ZeroAddress,
        "Final BondToken owner"
    );

    console.log(
        "\n7. Clean initial state"
    );
    console.log(
        "Lifecycle:             Draft"
    );
    console.log(
        "Subscription paused:   false"
    );
    console.log(
        "Subscription start:    0"
    );
    console.log(
        "Subscription deadline: 0"
    );
    console.log(
        "Whitelist applicants:  0"
    );
    console.log(
        "Total subscribed:      0"
    );
    console.log(
        "Total raised:          0"
    );
    console.log(
        "BondToken supply:      0"
    );

    // --------------------------------------------------------
    // 8. Export ABI and deployment metadata
    // --------------------------------------------------------

    const deploymentDirectory =
        path.join(
            __dirname,
            "..",
            "deployment"
        );

    const abiDirectory =
        path.join(
            deploymentDirectory,
            "abi"
        );

    const deploymentFile =
        path.join(
            deploymentDirectory,
            "sepolia.json"
        );

    const archivedFile =
        archiveExistingDeployment(
            deploymentFile,
            deploymentDirectory
        );

    const bondTokenArtifact =
        await artifacts.readArtifact(
            "BondToken"
        );

    const tokenizedBondArtifact =
        await artifacts.readArtifact(
            "TokenizedBond"
        );

    saveJson(
        path.join(
            abiDirectory,
            "BondToken.json"
        ),
        bondTokenArtifact.abi
    );

    saveJson(
        path.join(
            abiDirectory,
            "TokenizedBond.json"
        ),
        tokenizedBondArtifact.abi
    );

    const deploymentData = {
        version:
            "v2-whitelist-self-registration",
        cleanDeployment: true,
        network: "sepolia",
        chainId: Number(network.chainId),
        deployedAt: new Date().toISOString(),

        roles: {
            deployer:
                ethers.getAddress(
                    adminAddress
                ),
            admin:
                ethers.getAddress(
                    adminAddress
                ),
            issuer:
                ethers.getAddress(
                    ISSUER_ADDRESS
                ),
            bondUsdOwner:
                ethers.getAddress(
                    bondUsdOwner
                ),
        },

        contracts: {
            BondUSDToken: {
                address:
                    ethers.getAddress(
                        BOND_USD_ADDRESS
                    ),
                name: bondUsdName,
                symbol: bondUsdSymbol,
                decimals:
                    Number(
                        bondUsdDecimals
                    ),
            },

            BondToken: {
                address:
                    ethers.getAddress(
                        bondTokenAddress
                    ),
                deploymentTransactionHash:
                    bondTokenDeployment
                        .transactionHash,
                deploymentBlock:
                    bondTokenDeployment
                        .blockNumber,
                deploymentGasUsed:
                    bondTokenDeployment
                        .gasUsed,
            },

            TokenizedBond: {
                address:
                    ethers.getAddress(
                        tokenizedBondAddress
                    ),
                deploymentTransactionHash:
                    tokenizedBondDeployment
                        .transactionHash,
                deploymentBlock:
                    tokenizedBondDeployment
                        .blockNumber,
                deploymentGasUsed:
                    tokenizedBondDeployment
                        .gasUsed,
            },
        },

        configurationTransactions: {
            setController:
                setControllerResult,
            renounceOwnership:
                renounceResult,
        },

        initialState: {
            lifecycle:
                lifecycle.toString(),
            lifecycleName: "Draft",
            subscriptionPaused,
            subscriptionStart:
                subscriptionStart.toString(),
            subscriptionDeadline:
                subscriptionDeadline.toString(),
            totalSubscribed:
                totalSubscribed.toString(),
            totalRaised:
                totalRaised.toString(),
            totalRefunded:
                totalRefunded.toString(),
            proceedsWithdrawn,
            whitelistApplicantCount:
                applicantCount.toString(),
            whitelistInitiallyEmpty:
                applicantCount === 0n,
            bondTokenOwner:
                finalOwner,
            bondTokenController:
                ethers.getAddress(
                    finalController
                ),
            bondTokenTotalSupply:
                finalBondSupply.toString(),
        },
    };

    saveJson(
        deploymentFile,
        deploymentData
    );

    console.log(
        "\n8. Files generated"
    );

    if (archivedFile) {
        console.log(
            "Previous deployment archived:",
            archivedFile
        );
    }

    console.log(
        "Deployment file:",
        deploymentFile
    );

    console.log(
        "BondToken ABI:",
        path.join(
            abiDirectory,
            "BondToken.json"
        )
    );

    console.log(
        "TokenizedBond ABI:",
        path.join(
            abiDirectory,
            "TokenizedBond.json"
        )
    );

    console.log(
        "\n===================================================="
    );
    console.log(
        "CLEAN SEPOLIA V2 DEPLOYMENT COMPLETED"
    );
    console.log(
        "===================================================="
    );
    console.log(
        "BondUSDToken: ",
        BOND_USD_ADDRESS
    );
    console.log(
        "BondToken:    ",
        bondTokenAddress
    );
    console.log(
        "TokenizedBond:",
        tokenizedBondAddress
    );
    console.log(
        "Admin:        ",
        adminAddress
    );
    console.log(
        "Issuer:       ",
        ISSUER_ADDRESS
    );
    console.log(
        "Applicants:   0"
    );
    console.log(
        "Lifecycle:    Draft"
    );
    console.log(
        "===================================================="
    );
}

main()
    .then(() => {
        process.exitCode = 0;
    })
    .catch((error) => {
        console.error(
            "\nCLEAN DEPLOYMENT FAILED"
        );
        console.error(error);
        process.exitCode = 1;
    });
