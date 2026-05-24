import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import type { TimeRange } from "./TimeRangeControls";

interface Props {
  range: TimeRange;
}

function buildUrl(format: "csv" | "json", range: TimeRange): string {
  const url = new URL(
    `/api/export/tenders.${format}`,
    window.location.origin,
  );
  if (range.since) url.searchParams.set("date_from", range.since);
  if (range.until) url.searchParams.set("date_to", range.until);
  // Pathname + search keeps the relative path under the dev-server proxy.
  return url.pathname + url.search;
}

export function ExportButtons({ range }: Props) {
  return (
    <Card className="p-4">
      <CardHeader className="p-0 pb-3">
        <CardTitle className="text-base">Експорт даних</CardTitle>
        <CardDescription>
          Завантажити повний перелік тендерів за поточним часовим діапазоном.
        </CardDescription>
      </CardHeader>
      <div className="flex gap-2">
        <Button asChild>
          <a href={buildUrl("csv", range)} download>
            Завантажити CSV
          </a>
        </Button>
        <Button asChild variant="outline">
          <a href={buildUrl("json", range)} download>
            Завантажити JSON
          </a>
        </Button>
      </div>
    </Card>
  );
}
