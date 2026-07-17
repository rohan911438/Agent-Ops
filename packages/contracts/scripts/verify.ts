import { run, network } from "hardhat";
import * as fs from "fs";
import * as path from "path";

/**
 * Verifies the three contracts on Basescan using the addresses recorded in
 * deployments/<network>.json by scripts/deploy.ts. Requires BASESCAN_API_KEY
 * to be set; if it isn't, this exits with instructions for manual
 * verification instead of failing the deploy pipeline (see
 * docs/VerificationGuide.md).
 */
async function main() {
  if (!process.env.BASESCAN_API_KEY) {
    console.log(
      "BASESCAN_API_KEY is not set — skipping automatic verification.\n" +
        "See docs/VerificationGuide.md for the manual Basescan verification steps."
    );
    return;
  }

  const deploymentFile = path.join(__dirname, "..", "deployments", `${network.name}.json`);
  if (!fs.existsSync(deploymentFile)) {
    throw new Error(`No deployment record found at ${deploymentFile}. Run scripts/deploy.ts first.`);
  }
  const deployment = JSON.parse(fs.readFileSync(deploymentFile, "utf-8"));
  const { EnterpriseReportRegistry, ServicePricing, AgentOpsRegistry } = deployment.contracts;
  const deployer = deployment.deployer;

  const targets: Array<{ name: string; address: string; constructorArguments: unknown[] }> = [
    { name: "EnterpriseReportRegistry", address: EnterpriseReportRegistry, constructorArguments: [deployer] },
    { name: "ServicePricing", address: ServicePricing, constructorArguments: [deployer] },
    { name: "AgentOpsRegistry", address: AgentOpsRegistry, constructorArguments: [deployer] },
  ];

  for (const target of targets) {
    console.log(`Verifying ${target.name} at ${target.address}...`);
    try {
      await run("verify:verify", {
        address: target.address,
        constructorArguments: target.constructorArguments,
      });
    } catch (error: any) {
      if (String(error?.message).toLowerCase().includes("already verified")) {
        console.log(`  already verified`);
      } else {
        console.error(`  verification failed:`, error?.message ?? error);
      }
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
