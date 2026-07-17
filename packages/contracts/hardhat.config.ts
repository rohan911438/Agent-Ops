import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

dotenv.config();

const PRIVATE_KEY = process.env.PRIVATE_KEY;
const accounts = PRIVATE_KEY ? [PRIVATE_KEY] : [];

// Base Sepolia is the only network wired up for now. Base Mainnet is
// reserved below — flipping the deploy target to production later is a
// config change, not a rewrite (see docs/DeploymentGuide.md).
const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  networks: {
    hardhat: {},
    baseSepolia: {
      url: process.env.RPC_URL_BASE_SEPOLIA || "https://sepolia.base.org",
      chainId: 84532,
      accounts,
    },
    baseMainnet: {
      url: process.env.RPC_URL_BASE_MAINNET || "https://mainnet.base.org",
      chainId: 8453,
      accounts,
    },
    // Ethereum Sepolia — the L1 side of the Base Sepolia bridge. Only used
    // by scripts/bridge-to-base-sepolia.ts, never for deploying contracts.
    sepolia: {
      url: process.env.RPC_URL_ETHEREUM_SEPOLIA || "https://ethereum-sepolia-rpc.publicnode.com",
      chainId: 11155111,
      accounts,
    },
  },
  etherscan: {
    apiKey: {
      baseSepolia: process.env.BASESCAN_API_KEY || "",
      base: process.env.BASESCAN_API_KEY || "",
    },
    customChains: [
      {
        network: "baseSepolia",
        chainId: 84532,
        urls: {
          apiURL: "https://api-sepolia.basescan.org/api",
          browserURL: "https://sepolia.basescan.org",
        },
      },
      {
        network: "base",
        chainId: 8453,
        urls: {
          apiURL: "https://api.basescan.org/api",
          browserURL: "https://basescan.org",
        },
      },
    ],
  },
};

export default config;
