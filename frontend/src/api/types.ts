// Types mirroring the backend's Pydantic response models. Numeric Decimal
// fields are serialized as strings on the wire; we keep them as strings here
// to avoid float-precision surprises and format them at render time.

export interface TenderSummary {
  id: string;
  tender_id_human: string | null;
  title: string | null;
  procurement_method: string | null;
  procurement_method_type: string | null;
  status: string | null;
  value_amount: string | null;
  value_currency: string | null;
  date_published: string | null;
  buyer_edrpou: string | null;
  buyer_name: string | null;
}

export interface TenderListResponse {
  data: TenderSummary[];
  next_cursor: string | null;
}

export interface BidOut {
  id: string;
  status: string | null;
  value_amount: string | null;
  value_currency: string | null;
  date: string | null;
  supplier_edrpou: string | null;
  supplier_name: string | null;
}

export interface AwardOut {
  id: string;
  status: string | null;
  value_amount: string | null;
  value_currency: string | null;
  date: string | null;
  supplier_edrpou: string | null;
  supplier_name: string | null;
}

export interface ContractOut {
  id: string;
  status: string | null;
  value_amount: string | null;
  value_currency: string | null;
  date_signed: string | null;
  supplier_edrpou: string | null;
  supplier_name: string | null;
}

export interface ItemOut {
  id: string;
  description: string | null;
  cpv_code: string | null;
  quantity: string | null;
  unit: string | null;
}

export interface LotOut {
  id: string;
  title: string | null;
  description: string | null;
  status: string | null;
  value_amount: string | null;
  value_currency: string | null;
  items: ItemOut[];
  bids: BidOut[];
  awards: AwardOut[];
}

export interface RiskIndicatorValueOut {
  indicator_code: string;
  value_boolean: boolean | null;
  value_numeric: string | null;
  computed_at: string | null;
}

export interface TenderDetail extends TenderSummary {
  description: string | null;
  tender_period_start: string | null;
  tender_period_end: string | null;
  buyer_region: string | null;
  lots: LotOut[];
  contracts: ContractOut[];
  risk_indicator_values: RiskIndicatorValueOut[];
}

export interface DistributionBucketOut {
  label: string;
  tender_count: number;
  total_value: string | null;
}

export interface TimeSeriesPoint {
  period: string; // ISO datetime, e.g. "2025-01-01T00:00:00+00:00"
  tender_count: number;
  total_value: string | null;
}

export interface BuyerRankOut {
  edrpou: string | null;
  name: string | null;
  tender_count: number;
  total_value: string | null;
}

export interface SupplierRankOut {
  edrpou: string | null;
  name: string | null;
  contract_count: number;
  total_value: string | null;
}

export interface HighRiskShareOut {
  total_tenders: number;
  high_risk_tenders: number;
  share: number;
}

export interface DashboardKpis {
  total_tenders: number;
  total_value: string | null;
  active_tenders: number;
}

export interface DashboardResponse {
  kpis: DashboardKpis;
  procurement_type_distribution: DistributionBucketOut[];
  volume_over_time: TimeSeriesPoint[];
  top_risk_tenders: TenderSummary[];
  high_risk_share: HighRiskShareOut;
}

export interface RankingsResponse {
  buyers: BuyerRankOut[];
  suppliers: SupplierRankOut[];
}

export interface IndicatorReportRow {
  code: string;
  name: string;
  value_type: string;
  count_total: number;
  count_true: number;
  count_false: number;
  count_null: number;
  avg_numeric: number | null;
}

export interface IndicatorReportResponse {
  indicators: IndicatorReportRow[];
}

export interface RecomputeResponse {
  tenders_processed: number;
  bulk_rows_inserted: number;
}

export interface TenderListFilters {
  procuring_entity_id?: string;
  supplier_id?: string;
  cpv?: string;
  region?: string;
  procurement_method_type?: string;
  date_from?: string;
  date_to?: string;
  value_min?: string;
  value_max?: string;
  cursor?: string;
  limit?: number;
}
