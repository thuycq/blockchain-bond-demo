require("dotenv").config();
require("@nomicfoundation/hardhat-toolbox");

const accounts = [
    process.env.PRIVATE_KEY,
    process.env.ISSUER_PRIVATE_KEY,
    process.env.INVESTOR1_PRIVATE_KEY,
].filter(Boolean);

module.exports = {
    solidity: {
        version: "0.8.24",
        settings: {
            optimizer: {
                enabled: true,
                runs: 200,
            },
        },
    },

    networks: {
        sepolia: {
            url: process.env.SEPOLIA_RPC_URL || "",
            accounts,
            chainId: 11155111,
        },
    },

    mocha: {
        timeout: 40000,
    },
};