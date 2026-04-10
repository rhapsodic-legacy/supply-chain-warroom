/* ─── Suppliers ─── */
export interface Supplier {
  id: string;
  name: string;
  country: string;
  region: string;
  city: string;
  reliability_score: number;
  base_lead_time_days: number;
  lead_time_variance: number;
  cost_multiplier: number;
  capacity_units: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SupplierBrief {
  id: string;
  name: string;
  country: string;
  region: string;
  reliability_score: number;
  is_active: boolean;
}

/* ─── Products ─── */
export interface Product {
  id: string;
  sku: string;
  name: string;
  category: string;
  unit_cost: number;
  weight_kg: number;
  is_critical: boolean;
  description: string | null;
  created_at: string;
}

export interface ProductBrief {
  id: string;
  sku: string;
  name: string;
  category: string;
  is_critical: boolean;
}

/* ─── Shipping Routes ─── */
export interface ShippingRoute {
  id: string;
  name: string;
  origin_port: string;
  origin_country: string;
  destination_port: string;
  destination_country: string;
  transport_mode: string;
  base_transit_days: number;
  transit_variance_days: number;
  cost_per_kg: number;
  risk_score: number;
  capacity_tons: number;
  is_active: boolean;
  origin_lat: number;
  origin_lon: number;
  dest_lat: number;
  dest_lon: number;
  created_at: string;
}

export interface ShippingRouteBrief {
  id: string;
  name: string;
  origin_port: string;
  destination_port: string;
  transport_mode: string;
  base_transit_days: number;
  risk_score: number;
}

/* ─── Orders ─── */
export interface Order {
  id: string;
  order_number: string;
  product_id: string;
  supplier_id: string;
  route_id: string | null;
  quantity: number;
  unit_price: number;
  total_cost: number;
  status: string;
  ordered_at: string;
  expected_delivery: string | null;
  actual_delivery: string | null;
  delay_days: number;
  delay_reason: string | null;
  created_at: string;
  updated_at: string;
  supplier: SupplierBrief;
  product: ProductBrief;
  route: ShippingRouteBrief | null;
}

export interface OrderBrief {
  id: string;
  order_number: string;
  status: string;
  total_cost: number;
  ordered_at: string;
  expected_delivery: string | null;
  delay_days: number;
}

/* ─── Demand ─── */
export interface DemandSignal {
  id: string;
  product_id: string;
  region: string;
  signal_date: string;
  forecast_qty: number;
  actual_qty: number | null;
  variance_pct: number | null;
  created_at: string;
}

export interface DemandSummary {
  product_id: string;
  region: string;
  total_forecast: number;
  total_actual: number;
  avg_variance_pct: number;
}

/* ─── Risk Events ─── */
export interface RiskEvent {
  id: string;
  event_type: string;
  title: string;
  description: string;
  severity: string;
  severity_score: number;
  affected_region: string | null;
  started_at: string;
  expected_end: string | null;
  actual_end: string | null;
  is_active: boolean;
  created_at: string;
  impacts: RiskEventImpact[];
}

export interface RiskEventImpact {
  id: string;
  risk_event_id: string;
  entity_type: string;
  entity_id: string | null;
  entity_name: string;
  impact_multiplier: number;
  created_at: string;
}

/* ─── Agent Decisions ─── */
export interface AgentDecision {
  id: string;
  agent_type: string;
  trigger_event_id: string | null;
  decision_type: string;
  decision_summary: string;
  reasoning: string;
  confidence_score: number;
  affected_orders: string;
  parameters: string;
  status: string;
  outcome: string | null;
  outcome_notes: string | null;
  cost_impact: number | null;
  time_impact_days: number | null;
  decided_at: string;
  executed_at: string | null;
  created_at: string;
}

export interface AgentDecisionBrief {
  id: string;
  agent_type: string;
  decision_type: string;
  decision_summary: string;
  confidence_score: number;
  status: string;
  decided_at: string;
}

/* ─── Simulations ─── */
export interface Simulation {
  id: string;
  name: string;
  description: string | null;
  scenario_params: string;
  status: string;
  iterations: number;
  baseline_metrics: string | null;
  mitigated_metrics: string | null;
  comparison: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface SimulationBrief {
  id: string;
  name: string;
  status: string;
  created_at: string;
}

/* ─── Simulation Comparison ─── */
export interface HistogramData {
  bin_edges: number[];
  counts: number[];
}

export interface SimulationCompareItem {
  id: string;
  name: string;
  status: string;
  baseline_metrics: string | null;
  mitigated_metrics: string | null;
  comparison: string | null;
}

export interface SimulationCompareResponse {
  simulations: SimulationCompareItem[];
}

/* ─── Dashboard ─── */
export interface DashboardOverview {
  total_orders: number;
  active_orders: number;
  total_suppliers: number;
  active_suppliers: number;
  active_risk_events: number;
  critical_risk_events: number;
  avg_fill_rate: number;
  total_revenue: number;
}

export interface SupplyHealthItem {
  supplier_id: string;
  supplier_name: string;
  region: string;
  reliability_score: number;
  active_risk_count: number;
  pending_orders: number;
}

/* ─── Chat ─── */
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  response: string;
  agent_actions: Record<string, unknown>[];
  timestamp: string;
}

/* ─── Notifications ─── */
export interface Notification {
  id: string;
  type: 'risk' | 'agent' | 'order' | 'system';
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

/* ─── Agent Handoffs ─── */
export interface AgentHandoff {
  id: string;
  session_id: string;
  sequence: number;
  from_agent: string;
  to_agent: string;
  query: string;
  status: 'running' | 'completed' | 'error';
  result_summary: string | null;
  duration_ms: number | null;
  started_at: string;
  completed_at: string | null;
}

export interface AgentHandoffSession {
  session_id: string;
  handoffs: AgentHandoff[];
  started_at: string;
  completed_at: string | null;
  total_duration_ms: number | null;
}

/* ─── Executive Summary ─── */
export interface ExecutiveSummarySection {
  title: string;
  content: string;
}

export interface ExecutiveSummary {
  simulation_id: string;
  simulation_name: string;
  generated_at: string;
  llm_tier: 'claude' | 'gemma' | 'template';
  sections: Record<string, ExecutiveSummarySection>;
  raw_metrics: {
    baseline: Record<string, number>;
    mitigated: Record<string, number>;
    comparison: Record<string, number>;
    roi: {
      mitigation_cost: number;
      avoided_loss: number;
      roi_pct: number;
      payback_days: number | null;
      revenue_at_risk_per_day: number;
    };
  };
}

/* ─── SSE Events ─── */
export interface StreamEvent {
  type: 'risk_update' | 'order_update' | 'agent_action' | 'agent_handoff' | 'supply_alert' | 'demo_step' | 'heartbeat';
  data: Record<string, unknown>;
  timestamp: string;
}
