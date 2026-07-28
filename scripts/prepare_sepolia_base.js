const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

const { ethers } = hre;

const SEPOLIA_CHAIN_ID = 11155111n;

function assertEqual(actual, expected, label) {
    if (actual !== expected) {
        throw new Error(
            `${label} mismatch.\n` +
            `Expected: ${expected}\n` +
            `Actual:   ${actual}`
        );
    }
}

function assertAddressEqual(actual, expected, label) {
    const actualChecksum =
        ethers.getAddress(actual);

    const expectedChecksum =
        ethers.getAddress(expected);

    if (actualChecksum !== expectedChecksum) {
        throw new Error(
            `${label} mismatch.\n` +
            `Expected: ${expectedChecksum}\n` +
            `Actual:   ${actualChecksum}`
        );
    }
}

async function main() {
    console.log(
        "===================================================="
    );
    console.log(
        "BOND 7 - VALIDATE CLEAN SEPOLIA BASE"
    );
    console.log(
        "===================================================="
    );

    const deploymentPath =
        path.join(
            __dirname,
            "..",
            "deployment",
            "sepolia.json"
        );

    if (!fs.existsSync(deploymentPath)) {
        throw new Error(
            `Deployment file not found: ` +
            `${deploymentPath}`
        );
    }

    const deployment =
        JSON.parse(
            fs.readFileSync(
                deploymentPath,
                "utf8"
            )
        );

    const network =
        await ethers.provider.getNetwork();

    if (
        network.chainId !==
        SEPOLIA_CHAIN_ID
    ) {
        throw new Error(
            `Wrong network. Expected Sepolia ` +
            `chain ID ${SEPOLIA_CHAIN_ID}, ` +
            `received ${network.chainId}.`
        );
    }

    const [adminSigner] =
        await ethers.getSigners();

    if (!adminSigner) {
        throw new Error(
            "No signer is available."
        );
    }

    const adminAddress =
        ethers.getAddress(
            await adminSigner.getAddress()
        );

    const expectedAdmin =
        ethers.getAddress(
            deployment.roles.admin
        );

    assertAddressEqual(
        adminAddress,
        expectedAdmin,
        "Admin signer"
    );

    const tokenizedBondAddress =
        deployment
            .contracts
            .TokenizedBond
            .address;

    const bondTokenAddress =
        deployment
            .contracts
            .BondToken
            .address;

    const tokenizedBond =
        await ethers.getContractAt(
            "TokenizedBond",
            tokenizedBondAddress,
            adminSigner
        );

    const bondToken =
        await ethers.getContractAt(
            "BondToken",
            bondTokenAddress,
            adminSigner
        );

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
        supply,
        controller,
        owner,
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
        "Lifecycle"
    );

    assertEqual(
        subscriptionPaused,
        false,
        "Subscription paused"
    );

    assertEqual(
        subscriptionStart,
        0n,
        "Subscription start"
    );

    assertEqual(
        subscriptionDeadline,
        0n,
        "Subscription deadline"
    );

    assertEqual(
        totalSubscribed,
        0n,
        "Total subscribed"
    );

    assertEqual(
        totalRaised,
        0n,
        "Total raised"
    );

    assertEqual(
        totalRefunded,
        0n,
        "Total refunded"
    );

    assertEqual(
        proceedsWithdrawn,
        false,
        "Proceeds withdrawn"
    );

    assertEqual(
        applicantCount,
        0n,
        "Whitelist applicant count"
    );

    assertEqual(
        supply,
        0n,
        "BondToken supply"
    );

    assertAddressEqual(
        controller,
        tokenizedBondAddress,
        "BondToken controller"
    );

    assertEqual(
        owner,
        ethers.ZeroAddress,
        "BondToken owner"
    );

    deployment.cleanBaseValidation = {
        validatedAt:
            new Date().toISOString(),
        readOnlyValidation: true,
        transactionsSent: 0,
        finalState: {
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
            bondTokenTotalSupply:
                supply.toString(),
            bondTokenController:
                ethers.getAddress(
                    controller
                ),
            bondTokenOwner: owner,
        },
    };

    fs.writeFileSync(
        deploymentPath,
        JSON.stringify(
            deployment,
            null,
            2
        ),
        "utf8"
    );

    console.log(
        "\n1. Clean deployment"
    );
    console.log(
        "Admin:                 ",
        adminAddress
    );
    console.log(
        "TokenizedBond:         ",
        tokenizedBondAddress
    );
    console.log(
        "BondToken:             ",
        bondTokenAddress
    );

    console.log(
        "\n2. Clean base state"
    );
    console.log(
        "Lifecycle:              Draft"
    );
    console.log(
        "Subscription paused:    false"
    );
    console.log(
        "Whitelist applicants:   0"
    );
    console.log(
        "Total subscribed:       0"
    );
    console.log(
        "Total raised:           0"
    );
    console.log(
        "BondToken supply:       0"
    );
    console.log(
        "Transactions sent:      0"
    );

    console.log(
        "\nDeployment file updated:"
    );
    console.log(
        deploymentPath
    );

    console.log(
        "\n===================================================="
    );
    console.log(
        "CLEAN SEPOLIA BASE VALIDATION PASSED"
    );
    console.log(
        "===================================================="
    );
    console.log(
        "No investor was registered."
    );
    console.log(
        "No investor was whitelisted."
    );
    console.log(
        "No blockchain transaction was sent."
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
            "\nCLEAN BASE VALIDATION FAILED"
        );
        console.error(error);
        process.exitCode = 1;
    });
