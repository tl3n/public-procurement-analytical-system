// Typed wrapper around the backend REST API. Requests target ``/api/...`` so
// Vite's dev-server proxy (see vite.config.ts) can route them to FastAPI.

import type {
  DashboardResponse,
  IndicatorReportResponse,
  RankingsResponse,
  RecomputeResponse,
  TenderDetail,
  TenderListFilters,
  TenderListResponse,
} from "./types";

const API_BASE = "/api";

type Params = Record<string, string | number | undefined | null>;

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, init);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${path}`);
  }
  return (await response.json()) as T;
}

function withParams(path: string, params?: Params): string {
  if (!params) return path;
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `${path}?${qs}` : path;
}

export const api = {
  listTenders: (filters: TenderListFilters = {}): Promise<TenderListResponse> =>
    fetchJson(withParams("/tenders", filters as Params)),

  getTender: (id: string): Promise<TenderDetail> =>
    fetchJson(`/tenders/${encodeURIComponent(id)}`),

  getDashboard: (): Promise<DashboardResponse> => fetchJson("/dashboard"),

  getRankings: (
    params: { limit?: number; since?: string; until?: string } = {},
  ): Promise<RankingsResponse> =>
    fetchJson(withParams("/statistics/rankings", params)),

  getIndicatorReport: (): Promise<IndicatorReportResponse> =>
    fetchJson("/statistics/indicators"),

  recompute: (): Promise<RecomputeResponse> =>
    fetchJson("/admin/recompute", { method: "POST" }),
};
