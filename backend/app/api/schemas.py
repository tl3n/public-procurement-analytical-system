"""Pydantic response models for the REST API."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Tenders ---------------------------------------------------------------


class TenderSummary(_Out):
    id: str
    tender_id_human: str | None = None
    title: str | None = None
    procurement_method: str | None = None
    procurement_method_type: str | None = None
    status: str | None = None
    value_amount: Decimal | None = None
    value_currency: str | None = None
    date_published: datetime | None = None
    buyer_edrpou: str | None = None
    buyer_name: str | None = None


class TenderListResponse(BaseModel):
    data: list[TenderSummary]
    next_cursor: str | None = None


class BidOut(_Out):
    id: str
    status: str | None = None
    value_amount: Decimal | None = None
    value_currency: str | None = None
    date: datetime | None = None
    supplier_edrpou: str | None = None
    supplier_name: str | None = None


class AwardOut(_Out):
    id: str
    status: str | None = None
    value_amount: Decimal | None = None
    value_currency: str | None = None
    date: datetime | None = None
    supplier_edrpou: str | None = None
    supplier_name: str | None = None


class ContractOut(_Out):
    id: str
    status: str | None = None
    value_amount: Decimal | None = None
    value_currency: str | None = None
    date_signed: datetime | None = None
    supplier_edrpou: str | None = None
    supplier_name: str | None = None


class ItemOut(_Out):
    id: str
    description: str | None = None
    cpv_code: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None


class LotOut(_Out):
    id: str
    title: str | None = None
    description: str | None = None
    status: str | None = None
    value_amount: Decimal | None = None
    value_currency: str | None = None
    items: list[ItemOut] = []
    bids: list[BidOut] = []
    awards: list[AwardOut] = []


class RiskIndicatorValueOut(_Out):
    indicator_code: str
    value_boolean: bool | None = None
    value_numeric: Decimal | None = None
    computed_at: datetime | None = None


class TenderDetail(TenderSummary):
    description: str | None = None
    tender_period_start: datetime | None = None
    tender_period_end: datetime | None = None
    buyer_region: str | None = None
    lots: list[LotOut] = []
    contracts: list[ContractOut] = []
    risk_indicator_values: list[RiskIndicatorValueOut] = []


# --- Dashboard / statistics ------------------------------------------------


class DistributionBucketOut(_Out):
    label: str
    tender_count: int
    total_value: Decimal | None = None


class TimeSeriesPointOut(_Out):
    period: datetime
    tender_count: int
    total_value: Decimal | None = None


class BuyerRankOut(_Out):
    edrpou: str | None = None
    name: str | None = None
    tender_count: int
    total_value: Decimal | None = None


class SupplierRankOut(_Out):
    edrpou: str | None = None
    name: str | None = None
    contract_count: int
    total_value: Decimal | None = None


class HighRiskShareOut(_Out):
    total_tenders: int
    high_risk_tenders: int
    share: float


class DashboardKpis(BaseModel):
    total_tenders: int
    total_value: Decimal | None = None
    active_tenders: int


class DashboardResponse(BaseModel):
    kpis: DashboardKpis
    procurement_type_distribution: list[DistributionBucketOut]
    volume_over_time: list[TimeSeriesPointOut]
    top_risk_tenders: list[TenderSummary]
    high_risk_share: HighRiskShareOut


class RankingsResponse(BaseModel):
    buyers: list[BuyerRankOut]
    suppliers: list[SupplierRankOut]


class DistributionsResponse(BaseModel):
    by_cpv: list[DistributionBucketOut]
    by_region: list[DistributionBucketOut]


class IndicatorReportRow(BaseModel):
    code: str
    name: str
    value_type: str
    count_total: int
    count_true: int
    count_false: int
    count_null: int
    avg_numeric: float | None = None


class IndicatorReportResponse(BaseModel):
    indicators: list[IndicatorReportRow]


# --- Admin -----------------------------------------------------------------


class RecomputeResponse(BaseModel):
    tenders_processed: int
    bulk_rows_inserted: int
