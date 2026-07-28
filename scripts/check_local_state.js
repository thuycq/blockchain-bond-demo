const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

const { ethers } = hre;

const LIFECYCLE_NAMES = [
    "Draft",
    "SubscriptionOpen",
    "Failed",
    "Active",
    "Matured",
    "Closed",
];

function resolveStateFile() {
    const configured =
        process.env.STATE_FILE ||
        path.join("deployment", "local", "latest.json");

    return path.isAbsolute(configured)
        ? configured
        : path.join(process.cwd(), configured);
}

function formatToken(value) {
    return ethers.formatEther(value);
}

function formatTimestamp(value) {
    if (value === 0n) {
        return "Not set";
    }

    return `${value.toString()} (${new Date(Number(value) * 1000).toISOString()})`;
}

async function assertContractExists(address, label) {
    const code = await ethers.provider.getCode(address);
    if (code === "0x") {
        throw new Error(
            `${label} has no bytecode at ${address}. ` +
                "The Hardhat node may have been restarted, or the wrong deployment file is selected."
        );
    }
}

async function printAccountState(label, address, paymentToken, bondToken) {
    const paymentBalance = await paymentToken.balanceOf(address);
    const bondBalance = await bondToken.balanceOf(address);

    console.log(`\n${label}`);
    console.log(`  Address:       ${address}`);
    console.log(`  BONDUSD:       ${formatToken(paymentBalance)}`);
    console.log(`  DBOND26 units: ${bondBalance.toString()}`);
}

async function main() {
    const stateFile = resolveStateFile();

    if (!fs.existsSync(stateFile)) {
        throw new Error(
            `Deployment file not found: ${stateFile}\n` +
                "Run a deployment or scenario script first."
        );
    }

    const deployment = JSON.parse(fs.readFileSync(stateFile, "utf8"));
    const { contracts, roles } = deployment;

    if (!contracts?.paymentToken || !contracts?.bondToken || !contracts?.tokenizedBond) {
        throw new Error("Deployment file is missing contract addresses.");
    }

    await assertContractExists(contracts.paymentToken, "Payment token");
    await assertContractExists(contracts.bondToken, "BondToken");
    await assertContractExists(contracts.tokenizedBond, "TokenizedBond");

    const paymentToken = await ethers.getContractAt(
        "MockBondUSD",
        contracts.paymentToken
    );
    const bondToken = await ethers.getContractAt("BondToken", contracts.bondToken);
    const tokenizedBond = await ethers.getContractAt(
        "TokenizedBond",
        contracts.tokenizedBond
    );

    const network = await ethers.provider.getNetwork();
    const bondInfo = await tokenizedBond.getBondInfo();
    const offering = await tokenizedBond.getOfferingInfo();
    const coupon1 = await tokenizedBond.getCouponInfo(1);
    const coupon2 = await tokenizedBond.getCouponInfo(2);
    const principal = await tokenizedBond.getPrincipalInfo();
    const lifecycleIndex = Number(offering.currentLifecycle);

    console.log("\n=== LOCAL BOND STATE ===");
    console.log(`State file: ${stateFile}`);
    console.log(`Scenario:   ${deployment.scenario || "unknown"}`);
    console.log(`Network:    ${hre.network.name}`);
    console.log(`Chain ID:   ${network.chainId.toString()}`);

    console.log("\nContracts");
    console.log(`  Payment token: ${contracts.paymentToken}`);
    console.log(`  BondToken:     ${contracts.bondToken}`);
    console.log(`  TokenizedBond: ${contracts.tokenizedBond}`);

    console.log("\nBond configuration");
    console.log(`  Name:                 ${bondInfo.bondName}`);
    console.log(`  Face value:           ${formatToken(bondInfo.faceValue)} BONDUSD`);
    console.log(`  Issue price:          ${formatToken(bondInfo.issuePrice)} BONDUSD`);
    console.log(`  Maximum supply:       ${bondInfo.maxSupply.toString()}`);
    console.log(`  Minimum subscription: ${bondInfo.minimumSubscription.toString()}`);
    console.log(`  Coupon per period:    ${formatToken(bondInfo.couponPerPeriod)} BONDUSD`);

    console.log("\nOffering");
    console.log(
        `  Lifecycle:          ${LIFECYCLE_NAMES[lifecycleIndex] || lifecycleIndex}`
    );
    console.log(`  Paused:             ${offering.paused}`);
    console.log(`  Start:              ${formatTimestamp(offering.start)}`);
    console.log(`  Deadline:           ${formatTimestamp(offering.deadline)}`);
    console.log(`  Finalized at:       ${formatTimestamp(offering.finalizedTime)}`);
    console.log(`  Total subscribed:   ${offering.subscribed.toString()}`);
    console.log(`  Total raised:       ${formatToken(offering.raised)} BONDUSD`);
    console.log(`  Total refunded:     ${formatToken(offering.refunded)} BONDUSD`);
    console.log(`  Proceeds withdrawn: ${offering.proceedsAreWithdrawn}`);
    console.log(`  Can finalize:       ${await tokenizedBond.canFinalize()}`);
    console.log(`  Can close:          ${await tokenizedBond.canClose()}`);
    console.log(`  Currently defaulted:${await tokenizedBond.isDefaulted()}`);

    console.log("\nCoupon 1");
    console.log(`  Due:       ${formatTimestamp(coupon1.dueDate)}`);
    console.log(`  Required:  ${formatToken(coupon1.requiredAmount)} BONDUSD`);
    console.log(`  Funded:    ${formatToken(coupon1.fundedAmount)} BONDUSD`);
    console.log(`  Claimed:   ${formatToken(coupon1.claimedAmount)} BONDUSD`);
    console.log(`  Default:   ${coupon1.isInDefault}`);
    console.log(`  Default at:${formatTimestamp(coupon1.defaultTimestamp)}`);

    console.log("\nCoupon 2");
    console.log(`  Due:       ${formatTimestamp(coupon2.dueDate)}`);
    console.log(`  Required:  ${formatToken(coupon2.requiredAmount)} BONDUSD`);
    console.log(`  Funded:    ${formatToken(coupon2.fundedAmount)} BONDUSD`);
    console.log(`  Claimed:   ${formatToken(coupon2.claimedAmount)} BONDUSD`);
    console.log(`  Default:   ${coupon2.isInDefault}`);
    console.log(`  Default at:${formatTimestamp(coupon2.defaultTimestamp)}`);

    console.log("\nPrincipal");
    console.log(`  Maturity:   ${formatTimestamp(principal.maturityDate)}`);
    console.log(`  Required:   ${formatToken(principal.requiredAmount)} BONDUSD`);
    console.log(`  Funded:     ${formatToken(principal.fundedAmount)} BONDUSD`);
    console.log(`  Redeemed:   ${formatToken(principal.redeemedAmount)} BONDUSD`);
    console.log(`  Default:    ${principal.isInDefault}`);
    console.log(`  Default at: ${formatTimestamp(principal.defaultTimestamp)}`);

    console.log("\nContract balances");
    console.log(
        `  BONDUSD held: ${formatToken(
            await paymentToken.balanceOf(contracts.tokenizedBond)
        )}`
    );
    console.log(`  DBOND26 supply: ${(await bondToken.totalSupply()).toString()}`);

    if (roles?.issuer) {
        await printAccountState("Issuer", roles.issuer, paymentToken, bondToken);
    }
    if (roles?.investor1) {
        await printAccountState(
            "Investor 1",
            roles.investor1,
            paymentToken,
            bondToken
        );
        const position = await tokenizedBond.getInvestorPosition(roles.investor1);
        console.log(`  Subscribed:    ${position.quantitySubscribed.toString()}`);
        console.log(`  Paid:          ${formatToken(position.amountPaid)} BONDUSD`);
        console.log(`  Refundable:    ${formatToken(position.refundableAmount)} BONDUSD`);
        console.log(`  Claimable:     ${formatToken(position.claimableCouponTotal)} BONDUSD`);
        console.log(`  Principal now: ${formatToken(position.redeemablePrincipal)} BONDUSD`);
    }
    if (roles?.investor2) {
        await printAccountState(
            "Investor 2",
            roles.investor2,
            paymentToken,
            bondToken
        );
        const position = await tokenizedBond.getInvestorPosition(roles.investor2);
        console.log(`  Subscribed:    ${position.quantitySubscribed.toString()}`);
        console.log(`  Paid:          ${formatToken(position.amountPaid)} BONDUSD`);
        console.log(`  Refundable:    ${formatToken(position.refundableAmount)} BONDUSD`);
        console.log(`  Claimable:     ${formatToken(position.claimableCouponTotal)} BONDUSD`);
        console.log(`  Principal now: ${formatToken(position.redeemablePrincipal)} BONDUSD`);
    }

    console.log("\n=== STATE CHECK COMPLETE ===");
}

main().catch((error) => {
    console.error("\nState check failed:");
    console.error(error);
    process.exitCode = 1;
});
