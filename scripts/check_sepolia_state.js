const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

const { ethers } = hre;

function requireAddressEqual(actual, expected, label) {
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

function lifecycleName(value) {
    const names = [
        "Draft",
        "SubscriptionOpen",
        "Failed",
        "Active",
        "Matured",
        "Closed",
    ];

    return names[Number(value)] ?? `Unknown (${value})`;
}

async function main() {
    console.log("====================================================");
    console.log("BOND 5 - CHECK SEPOLIA STATE");
    console.log("====================================================");

    const deploymentPath = path.join(
        __dirname,
        "..",
        "deployment",
        "sepolia.json"
    );

    if (!fs.existsSync(deploymentPath)) {
        throw new Error(
            `Deployment file not found: ${deploymentPath}`
        );
    }

    const deployment = JSON.parse(
        fs.readFileSync(deploymentPath, "utf8")
    );

    const bondUsdAddress =
        deployment.contracts.BondUSDToken.address;

    const bondTokenAddress =
        deployment.contracts.BondToken.address;

    const tokenizedBondAddress =
        deployment.contracts.TokenizedBond.address;

    const expectedAdmin =
        deployment.roles.admin;

    const expectedIssuer =
        deployment.roles.issuer;

    const network = await ethers.provider.getNetwork();

    if (network.chainId !== 11155111n) {
        throw new Error(
            `Wrong network. Expected Sepolia, received chain ID ` +
            `${network.chainId}.`
        );
    }

    const [signer] = await ethers.getSigners();
    const signerAddress = await signer.getAddress();
    const signerBalance =
        await ethers.provider.getBalance(signerAddress);

    console.log("\n1. Network");
    console.log("Network:            Sepolia");
    console.log("Chain ID:          ", network.chainId.toString());
    console.log("Connected signer:  ", signerAddress);
    console.log(
        "Signer balance:   ",
        ethers.formatEther(signerBalance),
        "Sepolia ETH"
    );

    const bondUsdCode =
        await ethers.provider.getCode(bondUsdAddress);

    const bondTokenCode =
        await ethers.provider.getCode(bondTokenAddress);

    const tokenizedBondCode =
        await ethers.provider.getCode(tokenizedBondAddress);

    if (bondUsdCode === "0x") {
        throw new Error("BondUSD contract code not found.");
    }

    if (bondTokenCode === "0x") {
        throw new Error("BondToken contract code not found.");
    }

    if (tokenizedBondCode === "0x") {
        throw new Error("TokenizedBond contract code not found.");
    }

    console.log("\n2. Contract code check");
    console.log("BondUSD:           OK");
    console.log("BondToken:         OK");
    console.log("TokenizedBond:     OK");

    const bondUsdAbi = [
        "function name() view returns (string)",
        "function symbol() view returns (string)",
        "function decimals() view returns (uint8)",
        "function totalSupply() view returns (uint256)",
        "function owner() view returns (address)",
    ];

    const bondUSD = new ethers.Contract(
        bondUsdAddress,
        bondUsdAbi,
        signer
    );

    const BondToken =
        await ethers.getContractFactory("BondToken");

    const TokenizedBond =
        await ethers.getContractFactory("TokenizedBond");

    const bondToken =
        BondToken.attach(bondTokenAddress);

    const tokenizedBond =
        TokenizedBond.attach(tokenizedBondAddress);

    const [
        bondUsdName,
        bondUsdSymbol,
        bondUsdDecimals,
        bondUsdSupply,
        bondUsdOwner,
    ] = await Promise.all([
        bondUSD.name(),
        bondUSD.symbol(),
        bondUSD.decimals(),
        bondUSD.totalSupply(),
        bondUSD.owner(),
    ]);

    console.log("\n3. BondUSD");
    console.log("Address:           ", bondUsdAddress);
    console.log("Name:              ", bondUsdName);
    console.log("Symbol:            ", bondUsdSymbol);
    console.log("Decimals:          ", bondUsdDecimals.toString());
    console.log("Owner:             ", bondUsdOwner);
    console.log(
        "Total supply:     ",
        ethers.formatUnits(
            bondUsdSupply,
            bondUsdDecimals
        ),
        bondUsdSymbol
    );

    const [
        bondName,
        bondSymbol,
        bondDecimals,
        bondOwner,
        bondController,
        bondSupply,
    ] = await Promise.all([
        bondToken.name(),
        bondToken.symbol(),
        bondToken.decimals(),
        bondToken.owner(),
        bondToken.controller(),
        bondToken.totalSupply(),
    ]);

    console.log("\n4. BondToken");
    console.log("Address:           ", bondTokenAddress);
    console.log("Name:              ", bondName);
    console.log("Symbol:            ", bondSymbol);
    console.log("Decimals:          ", bondDecimals.toString());
    console.log("Owner:             ", bondOwner);
    console.log("Controller:        ", bondController);
    console.log("Total supply:      ", bondSupply.toString());

    const [
        admin,
        issuer,
        paymentToken,
        configuredBondToken,
        lifecycle,
        subscriptionPaused,
    ] = await Promise.all([
        tokenizedBond.admin(),
        tokenizedBond.issuer(),
        tokenizedBond.paymentToken(),
        tokenizedBond.bondToken(),
        tokenizedBond.lifecycle(),
        tokenizedBond.subscriptionPaused(),
    ]);

    console.log("\n5. TokenizedBond");
    console.log("Address:           ", tokenizedBondAddress);
    console.log("Admin:             ", admin);
    console.log("Issuer:            ", issuer);
    console.log("Payment token:     ", paymentToken);
    console.log("Bond token:        ", configuredBondToken);
    console.log(
        "Lifecycle:        ",
        `${lifecycle.toString()} - ${lifecycleName(lifecycle)}`
    );
    console.log(
        "Subscription paused:",
        subscriptionPaused
    );

    requireAddressEqual(
        admin,
        expectedAdmin,
        "Admin"
    );

    requireAddressEqual(
        issuer,
        expectedIssuer,
        "Issuer"
    );

    requireAddressEqual(
        paymentToken,
        bondUsdAddress,
        "Payment token"
    );

    requireAddressEqual(
        configuredBondToken,
        bondTokenAddress,
        "Bond token reference"
    );

    requireAddressEqual(
        bondController,
        tokenizedBondAddress,
        "BondToken controller"
    );

    if (bondOwner !== ethers.ZeroAddress) {
        throw new Error(
            `BondToken owner must be zero address. ` +
            `Actual owner: ${bondOwner}`
        );
    }

    if (bondSupply !== 0n) {
        throw new Error(
            `BondToken initial supply must be zero. ` +
            `Actual supply: ${bondSupply}`
        );
    }

    if (lifecycle !== 0n) {
        throw new Error(
            `Initial lifecycle must be Draft. ` +
            `Actual lifecycle: ${lifecycle}`
        );
    }

    console.log("\n6. Integrity checks");
    console.log("Admin reference:          OK");
    console.log("Issuer reference:         OK");
    console.log("BondUSD reference:        OK");
    console.log("BondToken reference:      OK");
    console.log("Controller reference:     OK");
    console.log("Ownership renounced:      OK");
    console.log("Initial total supply:     OK");
    console.log("Initial lifecycle Draft:  OK");

    console.log("\n====================================================");
    console.log("SEPOLIA STATE CHECK PASSED");
    console.log("====================================================");
}

main()
    .then(() => {
        process.exitCode = 0;
    })
    .catch((error) => {
        console.error("\nSTATE CHECK FAILED");
        console.error(error);
        process.exitCode = 1;
    });