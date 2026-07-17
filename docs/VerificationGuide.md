# Verification Guide

How an enterprise customer (or anyone) verifies that an AgentOps Cloud Executive Report has not been modified since it was generated.

## What "verified" means here

When a Health Scan completes, `apps/api/app/services/verification_service.py` computes `sha256(json.dumps(report, sort_keys=True))` over the Executive Report and submits that hash to `EnterpriseReportRegistry.registerReport` on Base Sepolia. The report itself — every word of it — never leaves the database. Only its fingerprint does.

Verifying a report means: **recompute the same fingerprint from the report you're holding, and check it matches what's on-chain.** If even one character of the report changed, the recomputed hash won't match — that mismatch is the whole point.

## In the product

Once a scan completes, its Executive Report page shows a "Report Integrity" card (only when submission succeeded) with:

- **Verified** — when the proof was anchored
- **Report Seal** — the report's hash (truncated)
- **Registry Contract** — the `EnterpriseReportRegistry` address
- **Verification Record** — the transaction hash
- A **"View verification record"** link to the Base Sepolia explorer

No wallet, gas, or blockchain terminology is required to understand this — it reads as "this report is sealed and hasn't been tampered with," because that's what it is.

## Verifying independently (outside the product)

1. Fetch the report via `GET /api/v1/scans/{id}` (field `executive_report`) and the proof via `GET /api/v1/scans/{id}/verification`.
2. Recompute the hash: `sha256(json.dumps(report, sort_keys=True))` (Python) or an equivalent canonical-JSON SHA-256 in any language — key order and whitespace matter, which is why the backend always serializes with `sort_keys=True`.
3. Compare it to `report_hash` from step 1, or call `EnterpriseReportRegistry.verifyReport(reportHash)` directly on Base Sepolia and compare `workspaceId`, `timestamp`, and `version`.
4. Alternatively, open the `explorer_url` from step 1 and inspect the transaction's input data on Basescan directly.

## Manual Basescan verification (no API key)

If `BASESCAN_API_KEY` isn't set, `scripts/verify.ts` skips automatic verification. To verify a contract manually:

1. Go to the contract address on `https://sepolia.basescan.org`.
2. Open the "Contract" tab → "Verify and Publish."
3. Compiler: Solidity `0.8.24`, optimizer enabled, `200` runs (matches `hardhat.config.ts`).
4. Paste the flattened source (`npx hardhat flatten contracts/<Name>.sol -w @agentops/contracts`) or use Basescan's multi-file upload with the files under `packages/contracts/contracts/`.
5. Constructor argument: the deployer address, ABI-encoded (recorded in `deployments/baseSepolia.json`).

## What verification does *not* prove

It proves the report's content is byte-for-byte what was hashed at that timestamp. It does not prove the report's *conclusions* are correct — that's a separate trust question about the underlying rule engine and LLM narration, documented in `TechnicalDecisions.md`.
