import { ethers, network } from "hardhat";
import * as fs from "fs";
import * as path from "path";

/**
 * Deploys EnterpriseReportRegistry, ServicePricing, and AgentOpsRegistry,
 * seeds ServicePricing with the three MVP services at price 0, registers
 * the initial AgentOpsRegistry product version, and writes addresses to
 * deployments/<network>.json. Safe to re-run against a fresh network; it
 * does NOT skip re-deployment if a deployments file already exists — that
 * decision is left to the operator (see docs/DeploymentGuide.md).
 */

const SEED_SERVICES: Array<{ id: string; name: string; currency: string }> = [
  { id: "health_scan", name: "Enterprise Health Scan", currency: "USD" },
  { id: "executive_report", name: "Executive Report", currency: "USD" },
  { id: "optimization_planner", name: "Optimization Planner", currency: "USD" },
];

const INITIAL_VERSION = process.env.INITIAL_PRODUCT_VERSION || "phase4.0.0";
const INITIAL_BACKEND_VERSION = process.env.INITIAL_BACKEND_VERSION || "api-unversioned";
const INITIAL_FRONTEND_VERSION = process.env.INITIAL_FRONTEND_VERSION || "web-unversioned";
const CONTRACT_VERSION = "0.1.0";

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log(`Deploying to network "${network.name}" as ${deployer.address}`);

  const ReportRegistryFactory = await ethers.getContractFactory("EnterpriseReportRegistry");
  const reportRegistry = await ReportRegistryFactory.deploy(deployer.address);
  await reportRegistry.waitForDeployment();
  const reportRegistryAddress = await reportRegistry.getAddress();
  console.log(`EnterpriseReportRegistry deployed at ${reportRegistryAddress}`);

  const ServicePricingFactory = await ethers.getContractFactory("ServicePricing");
  const servicePricing = await ServicePricingFactory.deploy(deployer.address);
  await servicePricing.waitForDeployment();
  const servicePricingAddress = await servicePricing.getAddress();
  console.log(`ServicePricing deployed at ${servicePricingAddress}`);

  const AgentOpsRegistryFactory = await ethers.getContractFactory("AgentOpsRegistry");
  const agentOpsRegistry = await AgentOpsRegistryFactory.deploy(deployer.address);
  await agentOpsRegistry.waitForDeployment();
  const agentOpsRegistryAddress = await agentOpsRegistry.getAddress();
  console.log(`AgentOpsRegistry deployed at ${agentOpsRegistryAddress}`);

  console.log("Seeding ServicePricing with MVP services @ price 0...");
  for (const service of SEED_SERVICES) {
    const tx = await servicePricing.registerService(service.id, service.name, 0, service.currency);
    await tx.wait();
    console.log(`  registered "${service.id}"`);
  }

  console.log(`Registering initial AgentOpsRegistry version "${INITIAL_VERSION}"...`);
  const versionTx = await agentOpsRegistry.registerVersion(
    INITIAL_VERSION,
    INITIAL_BACKEND_VERSION,
    INITIAL_FRONTEND_VERSION,
    CONTRACT_VERSION
  );
  await versionTx.wait();

  const deployment = {
    network: network.name,
    chainId: (await ethers.provider.getNetwork()).chainId.toString(),
    deployer: deployer.address,
    deployedAt: new Date().toISOString(),
    contracts: {
      EnterpriseReportRegistry: reportRegistryAddress,
      ServicePricing: servicePricingAddress,
      AgentOpsRegistry: agentOpsRegistryAddress,
    },
    initialProductVersion: INITIAL_VERSION,
  };

  const deploymentsDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(deploymentsDir)) fs.mkdirSync(deploymentsDir, { recursive: true });
  const outFile = path.join(deploymentsDir, `${network.name}.json`);
  fs.writeFileSync(outFile, JSON.stringify(deployment, null, 2) + "\n");

  console.log(`\nDeployment record written to ${outFile}`);
  console.log("\nAdd these to apps/api/.env and apps/web/.env.local:");
  console.log(`REPORT_REGISTRY_CONTRACT_ADDRESS=${reportRegistryAddress}`);
  console.log(`SERVICE_PRICING_CONTRACT_ADDRESS=${servicePricingAddress}`);
  console.log(`AGENTOPS_REGISTRY_CONTRACT_ADDRESS=${agentOpsRegistryAddress}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
