import { ethers, network } from "hardhat";
import * as fs from "fs";
import * as path from "path";

/**
 * Owner-only admin script: enables or disables a service.
 *
 * Usage:
 *   SERVICE_ID=optimization_planner ENABLED=false npm run admin:set-service-enabled -w @agentops/contracts
 */
async function main() {
  const serviceId = requireEnv("SERVICE_ID");
  const enabled = requireEnv("ENABLED").toLowerCase() === "true";

  const deployment = readDeployment();
  const [signer] = await ethers.getSigners();
  const pricing = await ethers.getContractAt("ServicePricing", deployment.contracts.ServicePricing, signer);

  const tx = await pricing.setEnabled(serviceId, enabled);
  const receipt = await tx.wait();
  console.log(`Set "${serviceId}" enabled=${enabled} (tx ${receipt?.hash})`);
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
