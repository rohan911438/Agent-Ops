# Smart Contracts

Source: `packages/contracts` (Hardhat + TypeScript, Solidity `^0.8.24`, OpenZeppelin `Ownable`). Deployed to Base Sepolia; Base Mainnet is a config change away (`hardhat.config.ts` already reserves the `baseMainnet` network).

Three contracts, each with a single, narrow job. None of them ever see report content, org names, agent data, or customer information — see `ContractArchitecture.md` for why.

## EnterpriseReportRegistry

Anchors immutable proof that an Executive Report existed, unmodified, at a point in time.

**Storage** — `mapping(bytes32 reportHash => ReportProof)`:

| Field | Type | Notes |
|---|---|---|
| `workspaceId` | `string` | Opaque org identifier — never a company name |
| `timestamp` | `uint256` | `block.timestamp` at registration |
| `version` | `string` | Product version that produced the report (see `AgentOpsRegistry`) |
| `metadataURI` | `string` | Optional off-chain pointer; empty in the MVP |
| `submitter` | `address` | Backend signer that submitted the proof |

**Functions**

- `registerReport(bytes32 reportHash, string workspaceId, string version, string metadataURI)` — `onlyAuthorized`. Reverts with `ReportAlreadyRegistered` if `reportHash` was already written. A report is identified by its own hash, so re-registering the same hash is both meaningless and rejected — this doubles as tamper/replay protection with no extra bookkeeping.
- `verifyReport(bytes32 reportHash) view returns (bool exists, ReportProof proof)` — the read path anyone (not just the backend) can call.
- `addAuthorizedSubmitter` / `removeAuthorizedSubmitter` — `onlyOwner`. Submission rights are a separate allowlist from contract ownership, so the backend's signer key can rotate or differ from the deployer/owner key without a redeploy.

**Events**: `ReportRegistered`, `SubmitterAuthorized`, `SubmitterRevoked`.

**Why hash-only**: `reportHash = sha256(json.dumps(report, sort_keys=True))`, computed in `apps/api/app/services/verification_service.py`. Anyone holding the original report JSON can recompute the same hash and compare it against `verifyReport` — that comparison *is* the verification. See `VerificationGuide.md`.

## ServicePricing

Pricing metadata for AgentOps Cloud services. Every service is priced at `0` today — this contract exists so a future price change is `updatePrice` (a config update), never a redeploy or an API contract change.

**Storage** — `mapping(string serviceId => Service)` + `string[] serviceIds` for enumeration:

| Field | Type | Notes |
|---|---|---|
| `name` | `string` | Human-readable service name |
| `price` | `uint256` | Smallest unit of `currency`; `0` = free |
| `currency` | `string` | e.g. `"USD"` |
| `enabled` | `bool` | Whether the service is currently offered |
| `version` | `uint256` | Bumped on every price change |

Seeded at deploy time (`scripts/deploy.ts`) with `health_scan`, `executive_report`, `optimization_planner`, all at price `0`.

**Functions**: `registerService`, `updatePrice`, `setEnabled` (all `onlyOwner`), `getService` (view).

**Events**: `ServiceRegistered`, `PriceUpdated(serviceId, oldPrice, newPrice)`, `ServiceEnabledUpdated`.

No payment logic lives here — this is metadata only. See `FutureMonetization.md`.

## AgentOpsRegistry

Registers AgentOps Cloud product releases (backend + frontend + contract versions bundled together), so an enterprise customer can verify exactly which product version produced a given report — the `version` field on an `EnterpriseReportRegistry` proof points here.

**Storage** — `mapping(string version => ProductVersion)` + `string[] versionHistory` + `string currentVersion`.

**Functions**: `registerVersion` (`onlyOwner`), `getCurrentVersion`, `getVersion` (views).

**Event**: `VersionRegistered`.

## Access control summary

All three contracts are `Ownable`. Administrative functions (`updatePrice`, `setEnabled`, `registerVersion`, `addAuthorizedSubmitter`, `removeAuthorizedSubmitter`) are `onlyOwner`. There is deliberately no public UI for any of this — see `scripts/admin/*.ts` and `DeploymentGuide.md`.

## Testing

`packages/contracts/test/*.test.ts` (Hardhat + Chai). Covers: hash registration, duplicate-hash rejection, unauthorized-submitter rejection, submitter add/revoke, price updates + events, service enable/disable, version registration + duplicate rejection, and `onlyOwner` reverts on every admin function. Run with `npm test -w @agentops/contracts`.
