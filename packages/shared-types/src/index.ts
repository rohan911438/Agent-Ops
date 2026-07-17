/**
 * Hand-mirrored copies of apps/api/app/schemas/*.py.
 *
 * These are maintained by hand for the MVP. Once the API surface
 * stabilizes, generate this file from the FastAPI OpenAPI schema
 * (openapi-typescript) instead of hand-mirroring — see docs/API_Design.md.
 */
import { z } from "zod";

export const AgentFramework = z.enum([
  "openai_agents",
  "langgraph",
  "crewai",
  "autogen",
  "n8n",
  "custom",
  "mcp",
  "internal",
]);
export type AgentFramework = z.infer<typeof AgentFramework>;

export const AgentStatus = z.enum(["active", "idle", "error", "archived"]);
export type AgentStatus = z.infer<typeof AgentStatus>;

export const RiskLevel = z.enum(["low", "medium", "high"]);
export type RiskLevel = z.infer<typeof RiskLevel>;

export const AgentSchema = z.object({
  id: z.string(),
  org_id: z.string(),
  name: z.string(),
  framework: AgentFramework,
  owner_user_id: z.string().nullable(),
  status: AgentStatus,
  monthly_cost_cents: z.number().int(),
  health_score: z.number().int(),
  risk_level: RiskLevel,
  source: z.enum(["manual", "connector"]),
  agent_metadata: z.record(z.unknown()),
  created_at: z.string(),
  updated_at: z.string(),
});
export type Agent = z.infer<typeof AgentSchema>;

export const RecommendationType = z.enum([
  "merge_duplicate",
  "reduce_cost",
  "unused_agent",
  "permission_risk",
  "memory_optimization",
  "workflow_optimization",
  "orphaned_agent",
  "model_downgrade",
]);
export type RecommendationType = z.infer<typeof RecommendationType>;

export const RecommendationStatus = z.enum(["open", "dismissed", "applied"]);
export type RecommendationStatus = z.infer<typeof RecommendationStatus>;

export const RecommendationSchema = z.object({
  id: z.string(),
  org_id: z.string(),
  agent_id: z.string().nullable(),
  type: RecommendationType,
  title: z.string(),
  description: z.string(),
  impact_estimate: z.string(),
  status: RecommendationStatus,
  created_at: z.string(),
});
export type Recommendation = z.infer<typeof RecommendationSchema>;

export const ActivityEventSchema = z.object({
  id: z.string(),
  org_id: z.string(),
  agent_id: z.string().nullable(),
  actor: z.string(),
  event_type: z.string(),
  description: z.string(),
  event_metadata: z.record(z.unknown()),
  tx_hash: z.string().nullable(),
  created_at: z.string(),
});
export type ActivityEvent = z.infer<typeof ActivityEventSchema>;

export const OverviewSummarySchema = z.object({
  agents_found: z.number().int(),
  monthly_cost_cents: z.number().int(),
  open_risks: z.number().int(),
  optimization_opportunities: z.number().int(),
  recent_activity: z.array(ActivityEventSchema),
});
export type OverviewSummary = z.infer<typeof OverviewSummarySchema>;

export const WorkspaceSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
});
export type Workspace = z.infer<typeof WorkspaceSchema>;

export const UserRole = z.enum(["owner", "admin", "member"]);
export type UserRole = z.infer<typeof UserRole>;

export const AuthProviderType = z.enum(["wallet", "google", "microsoft", "github", "okta", "saml"]);
export type AuthProviderType = z.infer<typeof AuthProviderType>;

export const UserSchema = z.object({
  id: z.string(),
  email: z.string(),
  name: z.string(),
  role: UserRole,
  wallet_address: z.string().nullable(),
  auth_provider: AuthProviderType,
  last_login_at: z.string().nullable(),
  created_at: z.string(),
});
export type User = z.infer<typeof UserSchema>;

export const SessionOrganizationSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
});
export type SessionOrganization = z.infer<typeof SessionOrganizationSchema>;

export const SessionUserSchema = z.object({
  id: z.string(),
  wallet_address: z.string().nullable(),
  auth_provider: AuthProviderType,
  email: z.string(),
  name: z.string(),
  role: UserRole,
  last_login_at: z.string().nullable(),
  created_at: z.string(),
});
export type SessionUser = z.infer<typeof SessionUserSchema>;

export const SessionReadSchema = z.object({
  user: SessionUserSchema,
  organization: SessionOrganizationSchema,
  created: z.boolean().optional(),
});
export type SessionRead = z.infer<typeof SessionReadSchema>;

export const WalletNonceResponseSchema = z.object({
  nonce: z.string(),
  message: z.string(),
});
export type WalletNonceResponse = z.infer<typeof WalletNonceResponseSchema>;

export const ApiKeySchema = z.object({
  id: z.string(),
  name: z.string(),
  key_prefix: z.string(),
  last_used_at: z.string().nullable(),
  created_at: z.string(),
});
export type ApiKey = z.infer<typeof ApiKeySchema>;

export const WalletSchema = z.object({
  id: z.string(),
  chain: z.enum(["base"]),
  address: z.string(),
  last_verified_at: z.string().nullable(),
  created_at: z.string(),
});
export type Wallet = z.infer<typeof WalletSchema>;

export const ScanSourceType = z.enum([
  "file_upload",
  "github",
  "langgraph",
  "crewai",
  "openai_agents_sdk",
]);
export type ScanSourceType = z.infer<typeof ScanSourceType>;

export const ScanStatus = z.enum([
  "pending",
  "parsing",
  "analyzing",
  "generating_report",
  "completed",
  "failed",
]);
export type ScanStatus = z.infer<typeof ScanStatus>;

export const PriorityActionSchema = z.object({
  title: z.string(),
  rationale: z.string(),
  estimated_impact: z.string(),
});
export type PriorityAction = z.infer<typeof PriorityActionSchema>;

export const CostAnalysisSchema = z.object({
  summary: z.string(),
  model_downgrade_suggestions: z.array(z.string()),
});
export type CostAnalysis = z.infer<typeof CostAnalysisSchema>;

export const SecurityRisksSchema = z.object({
  summary: z.string(),
  high_risk_agents: z.array(z.string()),
});
export type SecurityRisks = z.infer<typeof SecurityRisksSchema>;

export const OperationalRisksSchema = z.object({
  summary: z.string(),
  orphaned_agents: z.array(z.string()),
  redundant_workflows: z.array(z.string()),
});
export type OperationalRisks = z.infer<typeof OperationalRisksSchema>;

export const OptimizationOpportunitiesSchema = z.object({
  summary: z.string(),
  merge_candidates: z.array(z.string()),
});
export type OptimizationOpportunities = z.infer<typeof OptimizationOpportunitiesSchema>;

export const ExecutiveReportSchema = z.object({
  executive_summary: z.string(),
  organization_overview: z.string(),
  cost_analysis: CostAnalysisSchema,
  security_risks: SecurityRisksSchema,
  operational_risks: OperationalRisksSchema,
  optimization_opportunities: OptimizationOpportunitiesSchema,
  business_impact: z.string(),
  priority_actions: z.array(PriorityActionSchema),
  health_score: z.number().int(),
});
export type ExecutiveReport = z.infer<typeof ExecutiveReportSchema>;

export const OptimizationPlanItemSchema = z.object({
  id: z.string(),
  type: RecommendationType,
  title: z.string(),
  business_problem: z.string(),
  business_value: z.string(),
  technical_reason: z.string(),
  recommended_action: z.string(),
  priority: z.enum(["high", "medium", "low"]),
  estimated_cost_savings: z.string(),
  estimated_engineering_effort: z.string(),
  risk_level: z.enum(["low", "medium", "high"]),
  dependencies: z.array(z.string()),
  confidence_score: z.number().int(),
  rollback_strategy: z.string(),
  expected_kpi_improvement: z.string(),
  timeline: z.string(),
  expected_roi: z.string(),
});
export type OptimizationPlanItem = z.infer<typeof OptimizationPlanItemSchema>;

export const OptimizationPlanSchema = z.object({
  summary: z.string(),
  total_estimated_monthly_savings: z.string(),
  immediate_wins: z.array(OptimizationPlanItemSchema),
  thirty_day_plan: z.array(OptimizationPlanItemSchema),
  ninety_day_improvements: z.array(OptimizationPlanItemSchema),
  long_term_architecture: z.array(OptimizationPlanItemSchema),
});
export type OptimizationPlan = z.infer<typeof OptimizationPlanSchema>;

export const ScanSummarySchema = z.object({
  agent_count: z.number().int(),
  frameworks: z.record(z.number().int()),
  models: z.record(z.number().int()),
  monthly_cost_cents: z.number().int(),
  duplicate_count: z.number().int(),
  orphaned_count: z.number().int(),
  high_risk_count: z.number().int(),
  unused_count: z.number().int(),
  model_downgrade_count: z.number().int(),
});
export type ScanSummary = z.infer<typeof ScanSummarySchema>;

export const HealthScanSchema = z.object({
  id: z.string(),
  org_id: z.string(),
  source_type: ScanSourceType,
  source_label: z.string(),
  status: ScanStatus,
  current_step: z.string().nullable(),
  agent_ids: z.array(z.string()),
  summary: ScanSummarySchema.nullable(),
  executive_report: ExecutiveReportSchema.nullable(),
  optimization_plan: OptimizationPlanSchema.nullable(),
  error_message: z.string().nullable(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
});
export type HealthScan = z.infer<typeof HealthScanSchema>;

export const VerificationStatus = z.enum(["pending", "confirmed", "failed"]);

export const ReportVerificationSchema = z.object({
  id: z.string(),
  health_scan_id: z.string(),
  report_hash: z.string(),
  contract_address: z.string(),
  tx_hash: z.string().nullable(),
  chain_id: z.number().int(),
  block_number: z.number().int().nullable(),
  status: VerificationStatus,
  explorer_url: z.string().nullable(),
  version: z.string(),
  created_at: z.string(),
});
export type ReportVerification = z.infer<typeof ReportVerificationSchema>;

export const ServicePriceSchema = z.object({
  service_id: z.string(),
  name: z.string(),
  price: z.number().int(),
  currency: z.string(),
  enabled: z.boolean(),
  note: z.string(),
});
export type ServicePrice = z.infer<typeof ServicePriceSchema>;
