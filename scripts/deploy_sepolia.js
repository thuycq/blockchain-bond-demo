const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

const { ethers, artifacts } = hre;

// ============================================================
// SEPOLIA ADDRESSES
// ============================================================

const EXPECTED_ADMIN =
    "0x09428D10764503E9158374e556398b409d37381E";

const ISSUER_ADDRESS =
    "0x9D4C235100Ddfd5d61326769e16b2BB9dE04074e";

const INVESTOR_1_ADDRESS =
    "0x054d225D719B6326b45c50f3dd3c5275234d96C3";

const INVESTOR_2_ADDRESS =
    "0x6426d2Bd9b9c21218f805C5C54A7c7FAB3a6DEc2";

const BOND_USD_ADDRESS =
    "0xcDe41c009D3fFd58CaA9a4CC561155c2616B7D7D";

const SEPOLIA_CHAIN_ID = 11155111n;

// Minimal ABI used only to validate the existing BondUSD contract.
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

async function getDeploymentDetails(contract) {
    const deploymentTx = contract.deploymentTransaction();

    if (!deploymentTx) {
        throw new Error("Deployment transaction was not found.");
    }

    const receipt = await deploymentTx.wait();

    if (!receipt || receipt.status !== 1) {
        throw new Error("Contract deployment transaction failed.");
    }

    return {
        transactionHash: deploymentTx.hash,
        blockNumber: receipt.blockNumber,
        gasUsed: receipt.gasUsed.toString(),
    };
}

function saveJson(filePath, data) {
    fs.mkdirSync(path.dirname(filePath), {
        recursive: true,
    });

    fs.writeFileSync(
        filePath,
        JSON.stringify(data, null, 2),
        "utf8"
    );
}

// ============================================================
// MAIN
// ============================================================

async function main() {
    console.log("====================================================");
    console.log("BOND 5 - DEPLOY TO ETHEREUM SEPOLIA");
    console.log("====================================================");

    // --------------------------------------------------------
    // 1. Validate network and deployer
    // --------------------------------------------------------

    const network = await ethers.provider.getNetwork();

    if (network.chainId !== SEPOLIA_CHAIN_ID) {
        throw new Error(
            `Wrong network. Expected Sepolia chain ID ` +
            `${SEPOLIA_CHAIN_ID}, received ${network.chainId}.`
        );
    }

    const [deployer] = await ethers.getSigners();

    if (!deployer) {
        throw new Error("No deployer signer is available.");
    }

    const adminAddress = await deployer.getAddress();
    const deployerBalance =
        await ethers.provider.getBalance(adminAddress);

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
            "Admin and Issuer must be different addresses."
        );
    }

    console.log("\n1. Network and roles");
    console.log("Network:          Sepolia");
    console.log("Chain ID:        ", network.chainId.toString());
    console.log("Deployer/Admin:  ", adminAddress);
    console.log("Issuer:          ", ISSUER_ADDRESS);
    console.log(
        "Deployer balance:",
        ethers.formatEther(deployerBalance),
        "Sepolia ETH"
    );

    // --------------------------------------------------------
    // 2. Validate existing BondUSD
    // --------------------------------------------------------

    const bondUsdCode =
        await ethers.provider.getCode(BOND_USD_ADDRESS);

    if (bondUsdCode === "0x") {
        throw new Error(
            `No contract exists at BondUSD address: ` +
            `${BOND_USD_ADDRESS}`
        );
    }

    const bondUSD = new ethers.Contract(
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

    if (
        ethers.getAddress(bondUsdOwner) ===
        ethers.getAddress(ISSUER_ADDRESS)
    ) {
        throw new Error(
            "Issuer must not be the BondUSD owner."
        );
    }

    console.log("\n2. Existing BondUSD validation");
    console.log("BondUSD address:  ", BOND_USD_ADDRESS);
    console.log("Name:             ", bondUsdName);
    console.log("Symbol:           ", bondUsdSymbol);
    console.log("Decimals:         ", bondUsdDecimals.toString());
    console.log("Owner:            ", bondUsdOwner);
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

    console.log("\n3. Deploying BondToken...");

    const BondToken =
        await ethers.getContractFactory("BondToken");

    const bondToken = await BondToken.deploy(adminAddress);

    console.log(
        "BondToken deployment tx:",
        bondToken.deploymentTransaction().hash
    );

    await bondToken.waitForDeployment();

    const bondTokenAddress =
        await bondToken.getAddress();

    const bondTokenDeployment =
        await getDeploymentDetails(bondToken);

    console.log(
        "BondToken deployed to:",
        bondTokenAddress
    );

    // --------------------------------------------------------
    // 4. Validate BondToken initial state
    // --------------------------------------------------------

    const bondTokenOwnerBefore =
        await bondToken.owner();

    const controllerBefore =
        await bondToken.controller();

    const supplyBefore =
        await bondToken.totalSupply();

    assertAddressEqual(
        bondTokenOwnerBefore,
        adminAddress,
        "BondToken initial owner"
    );

    if (controllerBefore !== ethers.ZeroAddress) {
        throw new Error(
            `BondToken controller must initially be zero. ` +
            `Actual: ${controllerBefore}`
        );
    }

    if (supplyBefore !== 0n) {
        throw new Error(
            `BondToken total supply must initially be zero. ` +
            `Actual: ${supplyBefore}`
        );
    }

    console.log("BondToken owner:   ", bondTokenOwnerBefore);
    console.log("Controller before: ", controllerBefore);
    console.log("Total supply:      ", supplyBefore.toString());

    // --------------------------------------------------------
    // 5. Deploy TokenizedBond
    // Constructor:
    // admin, issuer, paymentToken, bondToken
    // --------------------------------------------------------

    console.log("\n4. Deploying TokenizedBond...");

    const TokenizedBond =
        await ethers.getContractFactory("TokenizedBond");

    const tokenizedBond = await TokenizedBond.deploy(
        adminAddress,
        ISSUER_ADDRESS,
        BOND_USD_ADDRESS,
        bondTokenAddress
    );

    console.log(
        "TokenizedBond deployment tx:",
        tokenizedBond.deploymentTransaction().hash
    );

    await tokenizedBond.waitForDeployment();

    const tokenizedBondAddress =
        await tokenizedBond.getAddress();

    const tokenizedBondDeployment =
        await getDeploymentDetails(tokenizedBond);

    console.log(
        "TokenizedBond deployed to:",
        tokenizedBondAddress
    );

    // --------------------------------------------------------
    // 6. Validate TokenizedBond configuration
    // --------------------------------------------------------

    const configuredAdmin =
        await tokenizedBond.admin();

    const configuredIssuer =
        await tokenizedBond.issuer();

    const configuredPaymentToken =
        await tokenizedBond.paymentToken();

    const configuredBondToken =
        await tokenizedBond.bondToken();

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

    console.log("\n5. TokenizedBond configuration");
    console.log("Admin:            ", configuredAdmin);
    console.log("Issuer:           ", configuredIssuer);
    console.log("Payment token:    ", configuredPaymentToken);
    console.log("Bond token:       ", configuredBondToken);

    // --------------------------------------------------------
    // 7. Set TokenizedBond as BondToken controller
    // --------------------------------------------------------

    console.log(
        "\n6. Setting TokenizedBond as BondToken controller..."
    );

    const setControllerTx =
        await bondToken.setController(tokenizedBondAddress);

    console.log(
        "setController tx:",
        setControllerTx.hash
    );

    const setControllerReceipt =
        await setControllerTx.wait();

    if (
        !setControllerReceipt ||
        setControllerReceipt.status !== 1
    ) {
        throw new Error(
            "setController transaction failed."
        );
    }

    const controllerAfter =
        await bondToken.controller();

    assertAddressEqual(
        controllerAfter,
        tokenizedBondAddress,
        "BondToken controller"
    );

    console.log(
        "Controller confirmed:",
        controllerAfter
    );

    // --------------------------------------------------------
    // 8. Final safety checks before renouncing ownership
    // --------------------------------------------------------

    console.log(
        "\n7. Running final checks before renounceOwnership..."
    );

    const finalSupplyBeforeRenounce =
        await bondToken.totalSupply();

    const finalControllerBeforeRenounce =
        await bondToken.controller();

    const tokenizedBondReference =
        await tokenizedBond.bondToken();

    if (finalSupplyBeforeRenounce !== 0n) {
        throw new Error(
            "BondToken supply changed before offering."
        );
    }

    assertAddressEqual(
        finalControllerBeforeRenounce,
        tokenizedBondAddress,
        "Final controller check"
    );

    assertAddressEqual(
        tokenizedBondReference,
        bondTokenAddress,
        "Final TokenizedBond reference check"
    );

    console.log("Controller check:  OK");
    console.log("BondToken ref:     OK");
    console.log("Total supply:      0");
    console.log("Ready to renounce: YES");

    // --------------------------------------------------------
    // 9. Renounce BondToken ownership
    // This action is irreversible.
    // --------------------------------------------------------

    console.log(
        "\n8. Renouncing BondToken ownership..."
    );

    const renounceTx =
        await bondToken.renounceOwnership();

    console.log(
        "renounceOwnership tx:",
        renounceTx.hash
    );

    const renounceReceipt =
        await renounceTx.wait();

    if (
        !renounceReceipt ||
        renounceReceipt.status !== 1
    ) {
        throw new Error(
            "renounceOwnership transaction failed."
        );
    }

    const finalOwner =
        await bondToken.owner();

    if (finalOwner !== ethers.ZeroAddress) {
        throw new Error(
            `BondToken ownership was not renounced. ` +
            `Current owner: ${finalOwner}`
        );
    }

    console.log(
        "BondToken final owner:",
        finalOwner
    );

    // --------------------------------------------------------
    // 10. Read initial system state
    // --------------------------------------------------------

    const lifecycle =
        await tokenizedBond.lifecycle();

    const subscriptionPaused =
        await tokenizedBond.subscriptionPaused();

    const finalBondSupply =
        await bondToken.totalSupply();

    const finalController =
        await bondToken.controller();

    console.log("\n9. Initial system state");
    console.log("Lifecycle:         ", lifecycle.toString());
    console.log(
        "Subscription paused:",
        subscriptionPaused
    );
    console.log(
        "BondToken supply:  ",
        finalBondSupply.toString()
    );
    console.log("Controller:        ", finalController);

    // --------------------------------------------------------
    // 11. Export ABI and deployment information
    // --------------------------------------------------------

    const deploymentDirectory =
        path.join(__dirname, "..", "deployment");

    const abiDirectory =
        path.join(deploymentDirectory, "abi");

    fs.mkdirSync(abiDirectory, {
        recursive: true,
    });

    const bondTokenArtifact =
        await artifacts.readArtifact("BondToken");

    const tokenizedBondArtifact =
        await artifacts.readArtifact("TokenizedBond");

    saveJson(
        path.join(abiDirectory, "BondToken.json"),
        bondTokenArtifact.abi
    );

    saveJson(
        path.join(abiDirectory, "TokenizedBond.json"),
        tokenizedBondArtifact.abi
    );

    const deploymentData = {
        network: "sepolia",
        chainId: Number(network.chainId),
        deployedAt: new Date().toISOString(),

        roles: {
            deployer: adminAddress,
            admin: adminAddress,
            issuer: ethers.getAddress(ISSUER_ADDRESS),
            investor1: ethers.getAddress(
                INVESTOR_1_ADDRESS
            ),
            investor2: ethers.getAddress(
                INVESTOR_2_ADDRESS
            ),
            bondUsdOwner: ethers.getAddress(
                bondUsdOwner
            ),
        },

        contracts: {
            BondUSDToken: {
                address: ethers.getAddress(
                    BOND_USD_ADDRESS
                ),
                name: bondUsdName,
                symbol: bondUsdSymbol,
                decimals: Number(bondUsdDecimals),
            },

            BondToken: {
                address: ethers.getAddress(
                    bondTokenAddress
                ),
                deploymentTransactionHash:
                    bondTokenDeployment.transactionHash,
                deploymentBlock:
                    bondTokenDeployment.blockNumber,
                deploymentGasUsed:
                    bondTokenDeployment.gasUsed,
            },

            TokenizedBond: {
                address: ethers.getAddress(
                    tokenizedBondAddress
                ),
                deploymentTransactionHash:
                    tokenizedBondDeployment
                        .transactionHash,
                deploymentBlock:
                    tokenizedBondDeployment.blockNumber,
                deploymentGasUsed:
                    tokenizedBondDeployment.gasUsed,
            },
        },

        configurationTransactions: {
            setController: {
                transactionHash:
                    setControllerTx.hash,
                blockNumber:
                    setControllerReceipt.blockNumber,
                gasUsed:
                    setControllerReceipt.gasUsed.toString(),
            },

            renounceOwnership: {
                transactionHash:
                    renounceTx.hash,
                blockNumber:
                    renounceReceipt.blockNumber,
                gasUsed:
                    renounceReceipt.gasUsed.toString(),
            },
        },

        initialState: {
            lifecycle: lifecycle.toString(),
            lifecycleName: "Draft",
            subscriptionPaused,
            bondTokenOwner: finalOwner,
            bondTokenController:
                ethers.getAddress(finalController),
            bondTokenTotalSupply:
                finalBondSupply.toString(),
        },
    };

    const deploymentFile =
        path.join(deploymentDirectory, "sepolia.json");

    saveJson(
        deploymentFile,
        deploymentData
    );

    console.log("\n10. Files generated");
    console.log(
        "Deployment file:",
        deploymentFile
    );
    console.log(
        "BondToken ABI:   ",
        path.join(abiDirectory, "BondToken.json")
    );
    console.log(
        "TokenizedBond ABI:",
        path.join(
            abiDirectory,
            "TokenizedBond.json"
        )
    );

    // --------------------------------------------------------
    // FINAL SUMMARY
    // --------------------------------------------------------

    console.log("\n====================================================");
    console.log("SEPOLIA DEPLOYMENT COMPLETED");
    console.log("====================================================");
    console.log("BondUSDToken: ", BOND_USD_ADDRESS);
    console.log("BondToken:    ", bondTokenAddress);
    console.log("TokenizedBond:", tokenizedBondAddress);
    console.log("Admin:        ", adminAddress);
    console.log("Issuer:       ", ISSUER_ADDRESS);
    console.log("Controller:   ", finalController);
    console.log("Bond owner:   ", finalOwner);
    console.log("Lifecycle:     Draft");
    console.log("====================================================");
}

main()
    .then(() => {
        process.exitCode = 0;
    })
    .catch((error) => {
        console.error("\nDEPLOYMENT FAILED");
        console.error(error);
        process.exitCode = 1;
    });