/**
 * API client for the Creseada RFQ backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface Rate {
  id: string;
  carrier_name: string;
  mode: string;
  origin_port: string;
  destination_port: string;
  currency: string;
  rate_per_unit: number;
  unit: string;
  minimum_charge: number | null;
  dg_surcharge_pct: number | null;
  valid_from: string;
  valid_to: string;
  source: string;
  status: string;
  notes: string | null;
  created_at: string;
}

export interface RFQListItem {
  id: string;
  rfq_reference: string | null;
  customer_name: string | null;
  subject: string | null;
  status: string;
  urgency: string;
  shipping_mode: string | null;
  origin: string | null;
  destination: string | null;
  is_dangerous_goods: boolean;
  odoo_quotation_number: string | null;
  assigned_agent: string | null;
  sla_deadline_at: string | null;
  sla_breached: boolean;
  received_at: string | null;
  created_at: string | null;
}

export interface RFQDetail extends RFQListItem {
  customer_email: string | null;
  parsed_email_json: string | null;
  parsed_cipl_json: string | null;
  parsed_msds_json: string | null;
  rate_id: string | null;
  rate_amount: number | null;
  rate_currency: string | null;
  estimated_cost: number | null;
  odoo_sale_order_id: number | null;
  email_file_path: string | null;
  attachment_paths_json: string | null;
  sla_target_hours: number | null;
  sla_breached_at: string | null;
  parsing_completed_at: string | null;
  rate_found_at: string | null;
  quote_drafted_at: string | null;
  quote_sent_at: string | null;
  updated_at: string | null;
  audit_log: AuditLogEntry[];
}

export interface AuditLogEntry {
  id: number;
  rfq_id: string;
  event: string;
  old_value: string | null;
  new_value: string | null;
  timestamp: string;
}

export interface DashboardOverview {
  by_status: Record<string, number>;
  total: number;
  urgent_count: number;
}

export interface SLAAlert {
  rfq_id: string;
  rfq_reference: string | null;
  customer_name: string | null;
  subject: string | null;
  status: string;
  urgency: string;
  sla_deadline_at: string;
  hours_remaining: number;
  sla_target_hours: number;
  assigned_agent: string | null;
  sla_breached_at?: string;
}

export interface SLAAlerts {
  summary: {
    breached_count: number;
    approaching_count: number;
    on_track_count: number;
    total_open: number;
  };
  breached?: SLAAlert[];
  approaching: SLAAlert[];
  on_track_count: number;
}

export interface RateLookupRequest {
  origin: string;
  destination: string;
  mode: string;
  weight_kg?: number;
  is_dangerous_goods?: boolean;
}

export interface RateLookupResponse {
  found: boolean;
  match_type: string;
  rate: Rate | null;
  estimated_cost: number | null;
  confidence: number;
  message: string;
}

export interface RateCreate {
  carrier_name: string;
  mode: string;
  origin_port: string;
  destination_port: string;
  currency?: string;
  rate_per_unit: number;
  unit: string;
  minimum_charge?: number;
  dg_surcharge_pct?: number;
  valid_from: string;
  valid_to: string;
  source?: string;
  notes?: string;
}

// API Functions

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `API error: ${response.status}`);
  }

  return response.json();
}

// Dashboard
export async function getDashboardOverview(): Promise<DashboardOverview> {
  return fetchApi<DashboardOverview>("/api/dashboard/overview");
}

export async function getSLAAlerts(
  includeBreached = true,
  approachingHours = 2
): Promise<SLAAlerts> {
  const params = new URLSearchParams({
    include_breached: String(includeBreached),
    approaching_hours: String(approachingHours),
  });
  return fetchApi<SLAAlerts>(`/api/dashboard/sla-alerts?${params}`);
}

// RFQs
export async function listRFQs(
  status?: string,
  urgency?: string
): Promise<RFQListItem[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (urgency) params.set("urgency", urgency);
  const query = params.toString() ? `?${params}` : "";
  return fetchApi<RFQListItem[]>(`/api/rfqs${query}`);
}

export async function getRFQ(rfqId: string): Promise<RFQDetail> {
  return fetchApi<RFQDetail>(`/api/rfqs/${rfqId}`);
}

export async function uploadRFQ(file: File): Promise<RFQDetail> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/api/rfqs/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `Upload failed: ${response.status}`);
  }

  return response.json();
}

export async function assignRateToRFQ(
  rfqId: string,
  rateId: string
): Promise<RFQDetail> {
  return fetchApi<RFQDetail>(`/api/rfqs/${rfqId}/assign-rate`, {
    method: "POST",
    body: JSON.stringify({ rate_id: rateId }),
  });
}

export async function approveRFQ(rfqId: string): Promise<RFQDetail> {
  return fetchApi<RFQDetail>(`/api/rfqs/${rfqId}/approve`, {
    method: "POST",
  });
}

export async function assignAgentToRFQ(
  rfqId: string,
  agentName: string
): Promise<RFQDetail> {
  return fetchApi<RFQDetail>(`/api/rfqs/${rfqId}/assign`, {
    method: "PATCH",
    body: JSON.stringify({ agent: agentName }),
  });
}

export async function exportRFQ(
  rfqId: string,
  format: "json" | "csv" | "pdf" = "json"
): Promise<Blob | object> {
  const response = await fetch(
    `${API_URL}/api/rfqs/${rfqId}/export?format=${format}`
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `Export failed: ${response.status}`);
  }

  if (format === "json") {
    return response.json();
  }
  return response.blob();
}

// Rates
export async function listRates(filters?: {
  mode?: string;
  origin?: string;
  destination?: string;
  status?: string;
}): Promise<Rate[]> {
  const params = new URLSearchParams();
  if (filters?.mode) params.set("mode", filters.mode);
  if (filters?.origin) params.set("origin", filters.origin);
  if (filters?.destination) params.set("destination", filters.destination);
  if (filters?.status) params.set("status", filters.status);
  const query = params.toString() ? `?${params}` : "";
  return fetchApi<Rate[]>(`/api/rates${query}`);
}

export async function getRate(rateId: string): Promise<Rate> {
  return fetchApi<Rate>(`/api/rates/${rateId}`);
}

export async function createRate(data: RateCreate): Promise<Rate> {
  return fetchApi<Rate>("/api/rates", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateRate(
  rateId: string,
  data: Partial<RateCreate>
): Promise<Rate> {
  return fetchApi<Rate>(`/api/rates/${rateId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function lookupRate(
  request: RateLookupRequest
): Promise<RateLookupResponse> {
  return fetchApi<RateLookupResponse>("/api/rates/lookup", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
