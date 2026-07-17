import { ethers, network } from "hardhat";
import * as fs from "fs";
import * as path from "path";

/**
 * Owner-only admin script: updates the price of an existing service.
 * No public UI exposes this — it's operated directly by whoever holds the
 * contract owner key (see docs/FutureMonetization.md).
 *
 * Usage:
 *   SERVICE_ID=health_scan NEW_PRICE=500 npm run admin:update-price -w @agentops/contracts
 */
async function main() {
  const serviceId = requireEnv("SERVICE_ID");
  const newPrice = BigInt(requireEnv("NEW_PRICE"));

  const deployment = readDeployment();
  const [signer] = await ethers.getSigners();
  const pricing = await ethers.getContractAt("ServicePricing", deployment.contracts.ServicePricing, signer);

  const tx = await pricing.updatePrice(serviceId, newPrice);
  const receipt = await tx.wait();
  console.log(`Updated "${serviceId}" price to ${newPrice.toString()} (tx ${receipt?.hash})`);
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
