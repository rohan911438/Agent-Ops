import { ethers } from "ethers";
import * as fs from "fs";
import * as path from "path";

/**
 * Generates a fresh, throwaway Base Sepolia keypair for use as the
 * deployer/submitter wallet. The private key is written ONLY to local,
 * gitignored .env files (packages/contracts/.env and apps/api/.env) — it is
 * never printed to stdout. Only the public address is printed, so it's safe
 * to share for faucet funding.
 *
 * Re-running this script overwrites CHAIN_PRIVATE_KEY / PRIVATE_KEY lines in
 * both files with a brand-new wallet — do not run it again after funding an
 * address unless you intend to replace it.
 */

function upsertEnvVar(filePath: string, key: string, value: string) {
  let contents = fs.existsSync(filePath) ? fs.readFileSync(filePath, "utf-8") : "";
  const line = `${key}=${value}`;
  const pattern = new RegExp(`^${key}=.*$`, "m");

  if (pattern.test(contents)) {
    contents = contents.replace(pattern, line);
  } else {
    contents = contents.length > 0 && !contents.endsWith("\n") ? contents + "\n" + line + "\n" : contents + line + "\n";
  }
  fs.writeFileSync(filePath, contents);
}

function main() {
  const wallet = ethers.Wallet.createRandom();

  const contractsEnvPath = path.join(__dirname, "..", ".env");
  upsertEnvVar(contractsEnvPath, "PRIVATE_KEY", wallet.privateKey);

  const apiEnvPath = path.join(__dirname, "..", "..", "..", "apps", "api", ".env");
  upsertEnvVar(apiEnvPath, "CHAIN_PRIVATE_KEY", wallet.privateKey);

  console.log("Generated a new Base Sepolia deployer/submitter wallet.");
  console.log(`Address: ${wallet.address}`);
  console.log("\nThe private key was written to (gitignored, not printed here):");
  console.log(`  ${contractsEnvPath}`);
  console.log(`  ${apiEnvPath}`);
  console.log("\nFund this address via the Base Sepolia faucet before deploying:");
  console.log("  https://www.alchemy.com/faucets/base-sepolia");
  console.log("  (or https://portal.cdp.coinbase.com/products/faucet)");
}

main();
