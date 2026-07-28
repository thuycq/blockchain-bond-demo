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

function lifecycleName(value) {
    const names = [
        "Draft",
        "SubscriptionOpen",
        "Failed",
        "Active",
        "Matured",
        "Closed",
    ];

    return (
        names[Number(value)] ??
        `Unknown (${value})`
    );
}

async function main() {
    console.log(
        "===================================================="
    );
    console.log(
        "BOND 7 - CHECK CLEAN SEPOLIA STATE"
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

    const bondUsdAddress =
        deployment
            .contracts
            .BondUSDToken
            .address;

    const bondTokenAddress =
        deployment
            .contracts
            .BondToken
            .address;

    const tokenizedBondAddress =
        deployment
            .contracts
            .TokenizedBond
            .address;

    const expectedAdmin =
        deployment.roles.admin;

    const expectedIssuer =
        deployment.roles.issuer;

    const network =
        await ethers.provider.getNetwork();

    if (
        network.chainId !==
        SEPOLIA_CHAIN_ID
    ) {
        throw new Error(
            `Wrong network. Expected Sepolia, ` +
            `received chain ID ` +
            `${network.chainId}.`
        );
    }

    const [signer] =
        await ethers.getSigners();

    if (!signer) {
        throw new Error(
            "No signer is available."
        );
    }

    const signerAddress =
        await signer.getAddress();

    const signerBalance =
        await ethers.provider.getBalance(
            signerAddress
        );

    console.log("\n1. Network");
    console.log(
        "Network:            Sepolia"
    );
    console.log(
        "Chain ID:          ",
        network.chainId.toString()
    );
    console.log(
        "Connected signer:  ",
        signerAddress
    );
    console.log(
        "Signer balance:   ",
        ethers.formatEther(
            signerBalance
        ),
        "Sepolia ETH"
    );

    const [
        bondUsdCode,
        bondTokenCode,
        tokenizedBondCode,
    ] = await Promise.all([
        ethers.provider.getCode(
            bondUsdAddress
        ),
        ethers.provider.getCode(
            bondTokenAddress
        ),
        ethers.provider.getCode(
            tokenizedBondAddress
        ),
    ]);

    if (bondUsdCode === "0x") {
        throw new Error(
            "BondUSD contract code not found."
        );
    }

    if (bondTokenCode === "0x") {
        throw new Error(
            "BondToken contract code not found."
        );
    }

    if (tokenizedBondCode === "0x") {
        throw new Error(
            "TokenizedBond contract code not found."
        );
    }

    const bondToken =
        await ethers.getContractAt(
            "BondToken",
            bondTokenAddress,
            signer
        );

    const tokenizedBond =
        await ethers.getContractAt(
            "TokenizedBond",
            tokenizedBondAddress,
            signer
        );

    const [
        admin,
        issuer,
        paymentToken,
        configuredBondToken,
        lifecycle,
        subscriptionPaused,
        subscriptionStart,
        subscriptionDeadline,
        totalSubscribed,
        totalRaised,
        totalRefunded,
        proceedsWithdrawn,
        applicantCount,
        bondOwner,
        bondController,
        bondSupply,
    ] = await Promise.all([
        tokenizedBond.admin(),
        tokenizedBond.issuer(),
        tokenizedBond.paymentToken(),
        tokenizedBond.bondToken(),
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
        bondToken.owner(),
        bondToken.controller(),
        bondToken.totalSupply(),
    ]);

    assertAddressEqual(
        admin,
        expectedAdmin,
        "Admin"
    );

    assertAddressEqual(
        issuer,
        expectedIssuer,
        "Issuer"
    );

    assertAddressEqual(
        paymentToken,
        bondUsdAddress,
        "Payment token"
    );

    assertAddressEqual(
        configuredBondToken,
        bondTokenAddress,
        "Bond token reference"
    );

    assertAddressEqual(
        bondController,
        tokenizedBondAddress,
        "BondToken controller"
    );

    assertEqual(
        bondOwner,
        ethers.ZeroAddress,
        "BondToken owner"
    );

    assertEqual(
        bondSupply,
        0n,
        "BondToken supply"
    );

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

    console.log(
        "\n2. Contracts"
    );
    console.log(
        "BondUSD:             ",
        bondUsdAddress
    );
    console.log(
        "BondToken:           ",
        bondTokenAddress
    );
    console.log(
        "TokenizedBond:       ",
        tokenizedBondAddress
    );

    console.log(
        "\n3. Roles"
    );
    console.log(
        "Admin:               ",
        admin
    );
    console.log(
        "Issuer:              ",
        issuer
    );

    console.log(
        "\n4. Clean initial state"
    );
    console.log(
        "Lifecycle:           ",
        `${lifecycle} - ` +
        `${lifecycleName(lifecycle)}`
    );
    console.log(
        "Subscription paused: ",
        subscriptionPaused
    );
    console.log(
        "Subscription start:  ",
        subscriptionStart.toString()
    );
    console.log(
        "Subscription deadline:",
        subscriptionDeadline.toString()
    );
    console.log(
        "Whitelist applicants:",
        applicantCount.toString()
    );
    console.log(
        "Total subscribed:    ",
        totalSubscribed.toString()
    );
    console.log(
        "Total raised:        ",
        totalRaised.toString()
    );
    console.log(
        "Total refunded:      ",
        totalRefunded.toString()
    );
    console.log(
        "Proceeds withdrawn:  ",
        proceedsWithdrawn
    );
    console.log(
        "BondToken supply:    ",
        bondSupply.toString()
    );

    console.log(
        "\n===================================================="
    );
    console.log(
        "CLEAN SEPOLIA STATE CHECK PASSED"
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
            "\nCLEAN STATE CHECK FAILED"
        );
        console.error(error);
        process.exitCode = 1;
    });
