import * as fs from "fs";
import * as path from "path";

/**
 * Copies compiled contract ABIs out of Hardhat's artifacts/ directory into
 * the two consumers that need them, keeping the Solidity source as the
 * single source of truth:
 *   - apps/api/app/services/chain/abi/*.json   (web3.py contract calls)
 *   - apps/web/lib/contracts/abi/*.json         (frontend display/reads, if ever needed)
 *
 * Run `npm run compile -w @agentops/contracts` first if artifacts/ is stale.
 */

const CONTRACTS = ["EnterpriseReportRegistry", "ServicePricing", "AgentOpsRegistry"];

const ROOT = path.join(__dirname, "..");
const ARTIFACTS_DIR = path.join(ROOT, "artifacts", "contracts");
const TARGETS = [
  path.join(ROOT, "..", "..", "apps", "api", "app", "services", "chain", "abi"),
  path.join(ROOT, "..", "..", "apps", "web", "lib", "contracts", "abi"),
];

function main() {
  for (const target of TARGETS) {
    fs.mkdirSync(target, { recursive: true });
  }

  for (const contractName of CONTRACTS) {
    const artifactPath = path.join(ARTIFACTS_DIR, `${contractName}.sol`, `${contractName}.json`);
    if (!fs.existsSync(artifactPath)) {
      throw new Error(`Missing artifact for ${contractName} at ${artifactPath}. Run "npm run compile" first.`);
    }
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf-8"));
    const abiOnly = JSON.stringify(artifact.abi, null, 2) + "\n";

    for (const target of TARGETS) {
      const outFile = path.join(target, `${contractName}.json`);
      fs.writeFileSync(outFile, abiOnly);
      console.log(`Wrote ${outFile}`);
    }
  }
}

main();
