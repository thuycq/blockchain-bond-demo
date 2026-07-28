const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

const { ethers, artifacts } = hre;

const ADMIN_ADDRESS =
    "0x09428D10764503E9158374e556398b409d37381E";

const ISSUER_ADDRESS =
    "0x9D4C235100Ddfd5d61326769e16b2BB9dE04074e";

const INVESTOR_ADDRESS =
    "0x054d225D719B6326b45c50f3dd3c5275234d96C3";

const BOND_USD_ADDRESS =
    "0xcDe41c009D3fFd58CaA9a4CC561155c2616B7D7D";

const SMOKE_QUANTITY = 2n;

function sameAddress(left, right) {
    return (
        ethers.getAddress(left) ===
        ethers.getAddress(right)
    );
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

async function waitForSuccess(tx, label) {
    console.log(`${label} tx:`, tx.hash);

    const receipt = await tx.wait();

    if (!receipt || receipt.status !== 1) {
        throw new Error(`${label} failed.`);
    }

    console.log(`${label}: successful`);

    return {
        transactionHash: tx.hash,
        blockNumber: receipt.blockNumber,
        gasUsed: receipt.gasUsed.toString(),
    };
}

function findSigner(signers, expectedAddress, label) {
    const expected = ethers.getAddress(expectedAddress);

    const signer = signers.find(
        (item) =>
            ethers.getAddress(item.address) === expected
    );

    if (!signer) {
        throw new Error(
            `${label} signer not found: ${expected}`
        );
    }

    return signer;
}

async function main() {
    console.log("====================================================");
    console.log("BOND 5 - SEPOLIA SMOKE TEST");
    console.log("====================================================");

    const network = await ethers.provider.getNetwork();

    if (network.chainId !== 11155111n) {
        throw new Error(
            `Wrong network: ${network.chainId}`
        );
    }

    const signers = await ethers.getSigners();

    const admin = findSigner(
        signers,
        ADMIN_ADDRESS,
        "Admin"
    );

    const issuer = findSigner(
        signers,
        ISSUER_ADDRESS,
        "Issuer"
    );

    const investor = findSigner(
        signers,
        INVESTOR_ADDRESS,
        "Investor"
    );

    console.log("\n1. Accounts");

    for (const [label, signer] of [
        ["Admin", admin],
        ["Issuer", issuer],
        ["Investor", investor],
    ]) {
        const balance =
            await ethers.provider.getBalance(
                signer.address
            );

        console.log(
            `${label}:`,
            signer.address,
            "-",
            ethers.formatEther(balance),
            "ETH"
        );

        if (balance < ethers.parseEther("0.002")) {
            throw new Error(
                `${label} does not have enough Sepolia ETH.`
            );
        }
    }

    const bondUsdCode =
        await ethers.provider.getCode(
            BOND_USD_ADDRESS
        );

    if (bondUsdCode === "0x") {
        throw new Error("BondUSD contract not found.");
    }

    const bondUsdAbi = [
        "function name() view returns (string)",
        "function symbol() view returns (string)",
        "function decimals() view returns (uint8)",
        "function owner() view returns (address)",
        "function balanceOf(address) view returns (uint256)",
        "function allowance(address,address) view returns (uint256)",
        "function approve(address,uint256) returns (bool)",
        "function mint(address,uint256)",
    ];

    const bondUsdAdmin = new ethers.Contract(
        BOND_USD_ADDRESS,
        bondUsdAbi,
        admin
    );

    const bondUsdInvestor =
        bondUsdAdmin.connect(investor);

    const bondUsdOwner = await bondUsdAdmin.owner();

    if (!sameAddress(bondUsdOwner, admin.address)) {
        throw new Error(
            "Admin is not the BondUSD owner."
        );
    }

    console.log("\n2. Deploy BondToken");

    const BondToken =
        await ethers.getContractFactory(
            "BondToken",
            admin
        );

    const bondToken =
        await BondToken.deploy(admin.address);

    const bondTokenDeployTx =
        bondToken.deploymentTransaction();

    console.log(
        "BondToken deployment tx:",
        bondTokenDeployTx.hash
    );

    await bondToken.waitForDeployment();

    const bondTokenAddress =
        await bondToken.getAddress();

    const bondTokenDeployReceipt =
        await bondTokenDeployTx.wait();

    console.log(
        "BondToken:",
        bondTokenAddress
    );

    console.log("\n3. Deploy TokenizedBond");

    const TokenizedBond =
        await ethers.getContractFactory(
            "TokenizedBond",
            admin
        );

    const tokenizedBond =
        await TokenizedBond.deploy(
            admin.address,
            issuer.address,
            BOND_USD_ADDRESS,
            bondTokenAddress
        );

    const tokenizedBondDeployTx =
        tokenizedBond.deploymentTransaction();

    console.log(
        "TokenizedBond deployment tx:",
        tokenizedBondDeployTx.hash
    );

    await tokenizedBond.waitForDeployment();

    const tokenizedBondAddress =
        await tokenizedBond.getAddress();

    const tokenizedBondDeployReceipt =
        await tokenizedBondDeployTx.wait();

    console.log(
        "TokenizedBond:",
        tokenizedBondAddress
    );

    console.log("\n4. Configure controller");

    const controllerResult = await waitForSuccess(
        await bondToken.setController(
            tokenizedBondAddress
        ),
        "setController"
    );

    if (
        !sameAddress(
            await bondToken.controller(),
            tokenizedBondAddress
        )
    ) {
        throw new Error(
            "Controller was not configured correctly."
        );
    }

    const renounceResult = await waitForSuccess(
        await bondToken.renounceOwnership(),
        "renounceOwnership"
    );

    if (
        (await bondToken.owner()) !==
        ethers.ZeroAddress
    ) {
        throw new Error(
            "BondToken ownership was not renounced."
        );
    }

    console.log("\n5. Whitelist investor");

    const whitelistResult = await waitForSuccess(
        await tokenizedBond
            .connect(admin)
            .setWhitelist(
                investor.address,
                true
            ),
        "setWhitelist"
    );

    console.log("\n6. Open subscription");

    const openResult = await waitForSuccess(
        await tokenizedBond
            .connect(issuer)
            .openSubscription(),
        "openSubscription"
    );

    const lifecycleAfterOpen =
        await tokenizedBond.lifecycle();

    if (lifecycleAfterOpen !== 1n) {
        throw new Error(
            `Expected SubscriptionOpen lifecycle, received ` +
            `${lifecycleAfterOpen}.`
        );
    }

    const issuePrice =
        await tokenizedBond.ISSUE_PRICE();

    const requiredPayment =
        issuePrice * SMOKE_QUANTITY;

    console.log("\n7. Prepare investor BondUSD");
    console.log(
        "Issue price:",
        ethers.formatEther(issuePrice),
        "BONDUSD"
    );
    console.log(
        "Quantity:",
        SMOKE_QUANTITY.toString()
    );
    console.log(
        "Required payment:",
        ethers.formatEther(requiredPayment),
        "BONDUSD"
    );

    let investorBondUsdBefore =
        await bondUsdAdmin.balanceOf(
            investor.address
        );

    if (investorBondUsdBefore < requiredPayment) {
        const mintAmount =
            requiredPayment - investorBondUsdBefore;

        console.log(
            "Investor balance is insufficient."
        );

        console.log(
            "Minting:",
            ethers.formatEther(mintAmount),
            "BONDUSD"
        );

        await waitForSuccess(
            await bondUsdAdmin.mint(
                investor.address,
                mintAmount
            ),
            "BondUSD mint"
        );

        investorBondUsdBefore =
            await bondUsdAdmin.balanceOf(
                investor.address
            );
    }

    console.log(
        "Investor BondUSD before:",
        ethers.formatEther(
            investorBondUsdBefore
        )
    );

    console.log("\n8. Approve BondUSD");

    const approveResult = await waitForSuccess(
        await bondUsdInvestor.approve(
            tokenizedBondAddress,
            requiredPayment
        ),
        "BondUSD approve"
    );

    const allowance =
        await bondUsdAdmin.allowance(
            investor.address,
            tokenizedBondAddress
        );

    if (allowance < requiredPayment) {
        throw new Error(
            "BondUSD allowance is insufficient."
        );
    }

    console.log(
        "Allowance:",
        ethers.formatEther(allowance),
        "BONDUSD"
    );

    console.log("\n9. Subscribe");

    const subscribeResult = await waitForSuccess(
        await tokenizedBond
            .connect(investor)
            .subscribe(SMOKE_QUANTITY),
        "subscribe"
    );

    const [
        investorBondUsdAfter,
        escrowBalance,
        investorBondBalance,
        totalSubscribed,
        totalRaised,
        bondSupply,
        lifecycleAfterSubscribe,
    ] = await Promise.all([
        bondUsdAdmin.balanceOf(
            investor.address
        ),
        bondUsdAdmin.balanceOf(
            tokenizedBondAddress
        ),
        bondToken.balanceOf(
            investor.address
        ),
        tokenizedBond.totalSubscribed(),
        tokenizedBond.totalRaised(),
        bondToken.totalSupply(),
        tokenizedBond.lifecycle(),
    ]);

    console.log("\n10. Smoke test results");
    console.log(
        "Investor BondUSD after:",
        ethers.formatEther(
            investorBondUsdAfter
        )
    );
    console.log(
        "Escrow BondUSD:",
        ethers.formatEther(escrowBalance)
    );
    console.log(
        "Investor BondToken:",
        investorBondBalance.toString()
    );
    console.log(
        "Total subscribed:",
        totalSubscribed.toString()
    );
    console.log(
        "Total raised:",
        ethers.formatEther(totalRaised),
        "BONDUSD"
    );
    console.log(
        "BondToken supply:",
        bondSupply.toString()
    );
    console.log(
        "Lifecycle:",
        lifecycleAfterSubscribe.toString()
    );

    if (investorBondBalance !== SMOKE_QUANTITY) {
        throw new Error(
            "Investor BondToken balance is incorrect."
        );
    }

    if (totalSubscribed !== SMOKE_QUANTITY) {
        throw new Error(
            "totalSubscribed is incorrect."
        );
    }

    if (totalRaised !== requiredPayment) {
        throw new Error(
            "totalRaised is incorrect."
        );
    }

    if (escrowBalance !== requiredPayment) {
        throw new Error(
            "Escrow BondUSD balance is incorrect."
        );
    }

    if (bondSupply !== SMOKE_QUANTITY) {
        throw new Error(
            "BondToken total supply is incorrect."
        );
    }

    if (lifecycleAfterSubscribe !== 1n) {
        throw new Error(
            "Lifecycle should remain SubscriptionOpen."
        );
    }

    const deploymentDirectory = path.join(
        __dirname,
        "..",
        "deployment"
    );

    const abiDirectory = path.join(
        deploymentDirectory,
        "abi"
    );

    const bondTokenArtifact =
        await artifacts.readArtifact("BondToken");

    const tokenizedBondArtifact =
        await artifacts.readArtifact(
            "TokenizedBond"
        );

    saveJson(
        path.join(
            abiDirectory,
            "BondToken.smoke.json"
        ),
        bondTokenArtifact.abi
    );

    saveJson(
        path.join(
            abiDirectory,
            "TokenizedBond.smoke.json"
        ),
        tokenizedBondArtifact.abi
    );

    const smokeData = {
        network: "sepolia",
        chainId: Number(network.chainId),
        completedAt: new Date().toISOString(),

        roles: {
            admin: admin.address,
            issuer: issuer.address,
            investor: investor.address,
        },

        contracts: {
            BondUSDToken: BOND_USD_ADDRESS,
            BondToken: bondTokenAddress,
            TokenizedBond: tokenizedBondAddress,
        },

        transactions: {
            deployBondToken: {
                transactionHash:
                    bondTokenDeployTx.hash,
                blockNumber:
                    bondTokenDeployReceipt.blockNumber,
                gasUsed:
                    bondTokenDeployReceipt
                        .gasUsed
                        .toString(),
            },

            deployTokenizedBond: {
                transactionHash:
                    tokenizedBondDeployTx.hash,
                blockNumber:
                    tokenizedBondDeployReceipt
                        .blockNumber,
                gasUsed:
                    tokenizedBondDeployReceipt
                        .gasUsed
                        .toString(),
            },

            setController: controllerResult,
            renounceOwnership: renounceResult,
            whitelistInvestor: whitelistResult,
            openSubscription: openResult,
            approveBondUsd: approveResult,
            subscribe: subscribeResult,
        },

        smokeInput: {
            quantity: SMOKE_QUANTITY.toString(),
            issuePrice:
                issuePrice.toString(),
            requiredPayment:
                requiredPayment.toString(),
        },

        finalState: {
            lifecycle:
                lifecycleAfterSubscribe.toString(),
            lifecycleName:
                "SubscriptionOpen",
            investorBondUsdBalance:
                investorBondUsdAfter.toString(),
            escrowBondUsdBalance:
                escrowBalance.toString(),
            investorBondTokenBalance:
                investorBondBalance.toString(),
            totalSubscribed:
                totalSubscribed.toString(),
            totalRaised:
                totalRaised.toString(),
            bondTokenTotalSupply:
                bondSupply.toString(),
        },
    };

    const outputPath = path.join(
        deploymentDirectory,
        "sepolia-smoke.json"
    );

    saveJson(outputPath, smokeData);

    console.log("\nOutput:");
    console.log(outputPath);

    console.log("\n====================================================");
    console.log("SEPOLIA SMOKE TEST PASSED");
    console.log("====================================================");
    console.log(
        "The base deployment was not modified."
    );
    console.log(
        "This smoke deployment is disposable."
    );
    console.log("====================================================");
}

main()
    .then(() => {
        process.exitCode = 0;
    })
    .catch((error) => {
        console.error("\nSMOKE TEST FAILED");
        console.error(error);
        process.exitCode = 1;
    });