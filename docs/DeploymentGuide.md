# Deployment Guide

How to deploy `packages/contracts` to Base Sepolia and wire the resulting addresses into `apps/api` and `apps/web`. Nothing here is required for the rest of AgentOps Cloud to run — every chain call degrades gracefully when unconfigured (see `SmartContracts.md` and `ContractArchitecture.md`).

## 1. Get a deployer wallet

Never paste a real private key into a chat session or commit it anywhere. Two options:

- **Generate a fresh throwaway wallet** (recommended for dev/test):
  ```
  npm run generate-wallet -w @agentops/contracts
  ```
  This prints an address and writes the private key **only** to gitignored local files: `packages/contracts/.env` (`PRIVATE_KEY`) and `apps/api/.env` (`CHAIN_PRIVATE_KEY`). The key is never printed to the terminal.
- **Bring your own key** — set `PRIVATE_KEY` in `packages/contracts/.env` and `CHAIN_PRIVATE_KEY` in `apps/api/.env` by hand.

Fund the resulting address via a Base Sepolia faucet before deploying:
- https://www.alchemy.com/faucets/base-sepolia
- https://portal.cdp.coinbase.com/products/faucet

## 2. Configure environment

`packages/contracts/.env` (copy from `.env.example`):

```
RPC_URL_BASE_SEPOLIA=https://sepolia.base.org
PRIVATE_KEY=<funded deployer key>
BASESCAN_API_KEY=<optional, for automatic verification>
```

## 3. Deploy

```
npm install -w @agentops/contracts
npm run compile -w @agentops/contracts
npm run deploy:baseSepolia -w @agentops/contracts
```

This deploys `EnterpriseReportRegistry`, `ServicePricing`, and `AgentOpsRegistry`; seeds `ServicePricing` with the three MVP services at price `0`; registers the initial `AgentOpsRegistry` version; and writes `packages/contracts/deployments/baseSepolia.json` (addresses are public information, safe to commit).

## 4. Export ABIs

```
npm run export-abi -w @agentops/contracts
```

Copies compiled ABI JSON from `artifacts/` into `apps/api/app/services/chain/abi/*.json` (used by `web3.py`) and `apps/web/lib/contracts/abi/*.json`. Solidity stays the single source of truth — nothing hand-copies an ABI.

## 5. Wire addresses into the apps

Add the addresses printed by the deploy script to `apps/api/.env`:

```
REPORT_REGISTRY_CONTRACT_ADDRESS=0x...
SERVICE_PRICING_CONTRACT_ADDRESS=0x...
AGENTOPS_REGISTRY_CONTRACT_ADDRESS=0x...
CHAIN_RPC_URL=https://sepolia.base.org
CHAIN_ID=84532
```

No frontend contract address env vars are required — the frontend only ever reads verification/pricing data through the FastAPI backend (`GET /scans/{id}/verification`, `GET /pricing`), never calling the chain directly.

## 6. Verify on Basescan

```
npm run verify:baseSepolia -w @agentops/contracts
```

Requires `BASESCAN_API_KEY`. If you don't have one, this step prints instructions and exits without failing the pipeline — see `VerificationGuide.md` for the manual verification steps.

## Admin operations (no public UI)

Contract admin (price updates, enable/disable, version registration, ownership transfer) is deliberately CLI-only — operated by whoever holds the owner key, never exposed through the product's UI:

```
SERVICE_ID=health_scan NEW_PRICE=500 npm run admin:update-price -w @agentops/contracts
SERVICE_ID=optimization_planner ENABLED=false npm run admin:set-service-enabled -w @agentops/contracts
VERSION=phase4.1.0 BACKEND_VERSION=api-1.4.1 FRONTEND_VERSION=web-1.4.1 CONTRACT_VERSION=0.1.0 \
  npm run admin:register-version -w @agentops/contracts
NEW_OWNER=0x... npm run admin:transfer-ownership -w @agentops/contracts
```

## Switching to Base Mainnet later

`hardhat.config.ts` already reserves a `baseMainnet` network (chain id `8453`, `RPC_URL_BASE_MAINNET`). Cutover is: fund a production deployer wallet, run `npm run deploy:localhost`-style commands against `--network baseMainnet` instead, update `apps/api/.env` with the new addresses and `CHAIN_ID=8453`, and update `BASE_EXPLORER_URL` to `https://basescan.org`. No contract code changes.

## Key separation in production

For this MVP build, one generated wallet is both the contract **owner** and the backend's authorized **submitter**. `EnterpriseReportRegistry.addAuthorizedSubmitter` exists specifically so production deployments can split these: keep the owner key offline/cold, and authorize a separate, narrowly-scoped signer key for the backend to use day-to-day. See `SecurityConsiderations` in the final deliverable summary.
