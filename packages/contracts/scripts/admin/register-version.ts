import { ethers, network } from "hardhat";
import * as fs from "fs";
import * as path from "path";

/**
 * Owner-only admin script: registers a new AgentOps product release.
 *
 * Usage:
 *   VERSION=phase4.1.0 BACKEND_VERSION=api-1.4.1 FRONTEND_VERSION=web-1.4.1 CONTRACT_VERSION=0.1.0 \
 *     npm run admin:register-version -w @agentops/contracts
 */
async function main() {
  const version = requireEnv("VERSION");
  const backendVersion = requireEnv("BACKEND_VERSION");
  const frontendVersion = requireEnv("FRONTEND_VERSION");
  const contractVersion = requireEnv("CONTRACT_VERSION");

  const deployment = readDeployment();
  const [signer] = await ethers.getSigners();
  const registry = await ethers.getContractAt("AgentOpsRegistry", deployment.contracts.AgentOpsRegistry, signer);

  const tx = await registry.registerVersion(version, backendVersion, frontendVersion, contractVersion);
  const receipt = await tx.wait();
  console.log(`Registered version "${version}" (tx ${receipt?.hash})`);
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
