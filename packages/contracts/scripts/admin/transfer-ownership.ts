import { ethers, network } from "hardhat";
import * as fs from "fs";
import * as path from "path";

/**
 * Owner-only admin script: transfers ownership of all three contracts to a
 * new address. Use with care — this is irreversible without the new
 * owner's cooperation.
 *
 * Usage:
 *   NEW_OWNER=0x... npm run admin:transfer-ownership -w @agentops/contracts
 */
async function main() {
  const newOwner = requireEnv("NEW_OWNER");

  const deployment = readDeployment();
  const [signer] = await ethers.getSigners();

  for (const [name, address] of Object.entries(deployment.contracts) as [string, string][]) {
    const contract = await ethers.getContractAt(name, address, signer);
    const tx = await contract.transferOwnership(newOwner);
    const receipt = await tx.wait();
    console.log(`${name}: ownership transferred to ${newOwner} (tx ${receipt?.hash})`);
  }
}

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required env var ${name}`);
  return value;
}

function readDeployment() {
  const deploymentFile = path.join(__dirname, "..", "..", "deployments", `${network.name}.json`);
  if (!fs.existsSync(deploymentFile)) {
    throw new Error(`No deployment record found at ${deploymentFile}. Run scripts/deploy.ts first.`);
  }
  return JSON.parse(fs.readFileSync(deploymentFile, "utf-8"));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
