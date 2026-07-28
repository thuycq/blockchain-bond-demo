const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

const { ethers } = hre;

async function waitForSuccess(transaction, label) {
    console.log(`${label} tx:`, transaction.hash);

    const receipt = await transaction.wait();

    if (!receipt || receipt.status !== 1) {
        throw new Error(`${label} transaction failed.`);
    }

    console.log(`${label}: successful`);

    return {
        transactionHash: transaction.hash,
        blockNumber: receipt.blockNumber,
        gasUsed: receipt.gasUsed.toString(),
    };
}

async function main() {
    console.log("====================================================");
    console.log("BOND 5 - PREPARE SEPOLIA BASE DEPLOYMENT");
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

    const tokenizedBondAddress =
        deployment.contracts.TokenizedBond.address;

    const bondTokenAddress =
        deployment.contracts.BondToken.address;

    const expectedAdmin =
        ethers.getAddress(deployment.roles.admin);

    const investor1 =
        ethers.getAddress(deployment.roles.investor1);

    const investor2 =
        ethers.getAddress(deployment.roles.investor2);

    const network = await ethers.provider.getNetwork();

    if (network.chainId !== 11155111n) {
        throw new Error(
            `Wrong network. Expected Sepolia chain ID 11155111, ` +
            `received ${network.chainId}.`
        );
    }

    const [adminSigner] = await ethers.getSigners();

    const adminAddress = ethers.getAddress(
        await adminSigner.getAddress()
    );

    if (adminAddress !== expectedAdmin) {
        throw new Error(
            `Wrong admin signer.\n` +
            `Expected: ${expectedAdmin}\n` +
            `Actual:   ${adminAddress}`
        );
    }

    const tokenizedBond = await ethers.getContractAt(
        "TokenizedBond",
        tokenizedBondAddress,
        adminSigner
    );

    const bondToken = await ethers.getContractAt(
        "BondToken",
        bondTokenAddress,
        adminSigner
    );

    const lifecycleBefore =
        await tokenizedBond.lifecycle();

    const supplyBefore =
        await bondToken.totalSupply();

    if (lifecycleBefore !== 0n) {
        throw new Error(
            `Base deployment is no longer in Draft. ` +
            `Lifecycle: ${lifecycleBefore}`
        );
    }

    if (supplyBefore !== 0n) {
        throw new Error(
            `Base BondToken supply must be zero. ` +
            `Actual supply: ${supplyBefore}`
        );
    }

    console.log("\n1. Base deployment");
    console.log("Admin:         ", adminAddress);
    console.log("TokenizedBond: ", tokenizedBondAddress);
    console.log("BondToken:     ", bondTokenAddress);
    console.log("Lifecycle:     ", lifecycleBefore.toString());
    console.log("Bond supply:   ", supplyBefore.toString());

    console.log("\n2. Whitelisting Investor 1");

    const investor1Tx =
        await tokenizedBond.setWhitelist(
            investor1,
            true
        );

    const investor1Result =
        await waitForSuccess(
            investor1Tx,
            "Investor 1 whitelist"
        );

    console.log("\n3. Whitelisting Investor 2");

    const investor2Tx =
        await tokenizedBond.setWhitelist(
            investor2,
            true
        );

    const investor2Result =
        await waitForSuccess(
            investor2Tx,
            "Investor 2 whitelist"
        );

    const lifecycleAfter =
        await tokenizedBond.lifecycle();

    const supplyAfter =
        await bondToken.totalSupply();

    if (lifecycleAfter !== 0n) {
        throw new Error(
            `Lifecycle changed unexpectedly. ` +
            `Actual lifecycle: ${lifecycleAfter}`
        );
    }

    if (supplyAfter !== 0n) {
        throw new Error(
            `BondToken supply changed unexpectedly. ` +
            `Actual supply: ${supplyAfter}`
        );
    }

    deployment.basePreparation = {
        preparedAt: new Date().toISOString(),

        investor1Whitelist: investor1Result,

        investor2Whitelist: investor2Result,

        finalState: {
            lifecycle: lifecycleAfter.toString(),
            lifecycleName: "Draft",
            bondTokenTotalSupply:
                supplyAfter.toString(),
        },
    };

    fs.writeFileSync(
        deploymentPath,
        JSON.stringify(deployment, null, 2),
        "utf8"
    );

    console.log("\n4. Final base state");
    console.log("Investor 1:    ", investor1);
    console.log("Investor 2:    ", investor2);
    console.log("Lifecycle:     ", lifecycleAfter.toString());
    console.log("Bond supply:   ", supplyAfter.toString());

    console.log("\nDeployment file updated:");
    console.log(deploymentPath);

    console.log("\n====================================================");
    console.log("SEPOLIA BASE PREPARATION COMPLETED");
    console.log("====================================================");
    console.log("Base contract remains in Draft.");
    console.log("Subscription has NOT been opened.");
    console.log("No BondToken has been minted.");
    console.log("====================================================");
}

main()
    .then(() => {
        process.exitCode = 0;
    })
    .catch((error) => {
        console.error("\nBASE PREPARATION FAILED");
        console.error(error);
        process.exitCode = 1;
    });