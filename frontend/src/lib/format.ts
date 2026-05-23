// Display formatters shared by the dashboard and other views.

const numberFmt = new Intl.NumberFormat("uk-UA");
const monthFmt = new Intl.DateTimeFormat("uk-UA", {
  year: "numeric",
  month: "short",
});

export function formatCount(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return "—";
  return numberFmt.format(n);
}

/** Compact money — switches to "млн" / "млрд" past the relevant thresholds. */
export function formatMoney(
  value: string | number | null | undefined,
  currency = "грн",
): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000_000) {
    return `${numberFmt.format(Math.round((n / 1_000_000_000) * 10) / 10)} млрд ${currency}`;
  }
  if (Math.abs(n) >= 1_000_000) {
    return `${numberFmt.format(Math.round((n / 1_000_000) * 10) / 10)} млн ${currency}`;
  }
  return `${numberFmt.format(Math.round(n))} ${currency}`;
}

export function formatMonth(iso: string): string {
  return monthFmt.format(new Date(iso));
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
