# Future Monetization

AgentOps Cloud is free today. This document explains the architecture that lets that change later without a redeploy, a schema migration, or an API breaking change — and explicitly what has **not** been built yet.

## What exists today

- **`ServicePricing.sol`** — on-chain pricing metadata for `health_scan`, `executive_report`, `optimization_planner`, all at price `0`, `enabled=true`. Prices are owner-updatable (`updatePrice`) without redeploying the contract or touching the backend/frontend.
- **`GET /api/v1/pricing`** — reads live prices from `ServicePricing` (falling back to a static FREE default if the chain is unreachable or unconfigured — see `app/services/payment/pricing_service.py`). The frontend's pricing note (`components/pricing-note.tsx`) always shows real data from this endpoint, never a hardcoded label.
- **`PaymentProvider` ABC** (`app/services/payment/provider.py`) — `is_payment_required(service_id)` / `charge(service_id, org_id)`.
- **`FreePaymentProvider`** — the only implementation wired up. Always returns "not required" / "not charged." This is what every service execution path uses today.

## What is explicitly not built

- **No payment is ever collected.** `charge()` is never called from any route.
- **`X402Adapter`** (`app/services/payment/x402_adapter.py`) exists only as a documented stub — every method raises `NotImplementedError`. It is not imported by any route or service. It exists so the eventual implementation has an exact interface to fill in, not to be toggled on today.

## The architecture, end to end

```
PricingService  ──reads price──▶  ServicePricing.sol (on-chain, owner-updatable)
      │
      ▼
PaymentProvider (ABC)
      │
      ├── FreePaymentProvider  ← wired up today, always bypasses
      │
      └── X402Adapter (future) ← stub only, NotImplementedError
                │
                ▼
      Service Execution (Health Scan / Executive Report / Optimization Planner)
```

Every service execution path calls `PaymentProvider.is_payment_required()` before running — today that always returns `False` via `FreePaymentProvider`, so execution proceeds unconditionally. Turning on payments later means:

1. An owner calls `ServicePricing.updatePrice(serviceId, newPrice)` for the services going paid.
2. `X402Adapter` gets a real implementation of `PaymentProvider`.
3. The call site that currently constructs `FreePaymentProvider()` constructs the new provider instead.

No route signature changes, no schema migration, no frontend contract change — `GET /pricing` already reports real numbers, so the UI updates automatically once prices move off `0`.

## Why x402 specifically

x402 (HTTP 402 Payment Required, revived as an agent-payment protocol) fits this product's shape well: AgentOps Cloud is itself an Agentic Service Provider (see `Architecture.md`), and its customers are increasingly other agents/automated systems, not just humans clicking a browser. An HTTP-native, per-request payment challenge is a more natural fit for that audience than a subscription checkout flow — but that's a decision for whenever paid tiers actually ship, not one this phase makes. The interfaces above are deliberately payment-provider-agnostic; x402 is the leading candidate, not a commitment.

## What the UI shows today

Every price surface — the Health Scan start page's pricing note, and any future pricing display — reads "Current Price: **FREE** — Future enterprise plans may introduce paid services," sourced from `GET /pricing`, never hand-written per page.
