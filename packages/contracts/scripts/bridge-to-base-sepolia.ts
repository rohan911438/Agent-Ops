import { ethers, network } from "hardhat";

/**
 * One-off: bridges ETH from Ethereum Sepolia (L1) to Base Sepolia (L2) via
 * the official Base Sepolia L1StandardBridge, so the deployer/submitter
 * wallet can pay for contract deployment on Base Sepolia.
 *
 * Address verified against docs.base.org's published Base Sepolia L1
 * contract addresses (raw HTML, not AI-summarized) and confirmed to hold
 * deployed bytecode on Ethereum Sepolia before use.
 *
 * Usage: BRIDGE_AMOUNT_ETH=0.03 npx hardhat run scripts/bridge-to-base-sepolia.ts --network sepolia
 */

const L1_STANDARD_BRIDGE_SEPOLIA = "0xfd0Bf71F60660E2f608ed56e1659C450eB113120";
const BRIDGE_ABI = ["function depositETH(uint32 _minGasLimit, bytes calldata _extraData) external payable"];
const L2_MIN_GAS_LIMIT = 200_000;

async function main() {
  if (network.name !== "sepolia") {
    throw new Error('Run this with --network sepolia (Ethereum Sepolia, the L1 side of the bridge).');
  }

  const amountEth = process.env.BRIDGE_AMOUNT_ETH || "0.03";
  const [signer] = await ethers.getSigners();
  const bridge = new ethers.Contract(L1_STANDARD_BRIDGE_SEPOLIA, BRIDGE_ABI, signer);

  const value = ethers.parseEther(amountEth);
  const balance = await ethers.provider.getBalance(signer.address);
  console.log(`Signer: ${signer.address}`);
  console.log(`Ethereum Sepolia balance: ${ethers.formatEther(balance)} ETH`);
  console.log(`Bridging ${amountEth} ETH to Base Sepolia via ${L1_STANDARD_BRIDGE_SEPOLIA}...`);

  const tx = await bridge.depositETH(L2_MIN_GAS_LIMIT, "0x", { value });
  console.log(`Submitted: ${tx.hash}`);
  const receipt = await tx.wait();
  console.log(`Confirmed on Ethereum Sepolia in block ${receipt?.blockNumber}.`);
  console.log("Funds typically appear on Base Sepolia within a few minutes.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
