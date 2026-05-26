import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatCount } from "@/lib/format";

interface Props {
  page: number;
  pageSize: number;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
}

export function Pagination({
  page,
  pageSize,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
}: Props) {
  return (
    <div className="flex flex-col items-start gap-2 border-t bg-muted/30 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-xs text-muted-foreground">
        Сторінка <span className="font-semibold text-foreground">{page}</span>
        <span className="mx-1.5 text-border">·</span>
        Показано{" "}
        <span className="font-semibold text-foreground">
          {formatCount(pageSize)}
        </span>{" "}
        {pluralRecords(pageSize)}
      </p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onPrev}
          disabled={!hasPrev}
        >
          <ChevronLeft className="mr-1 h-3.5 w-3.5" />
          Попередня
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onNext}
          disabled={!hasNext}
        >
          Наступна
          <ChevronRight className="ml-1 h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

function pluralRecords(n: number): string {
  // Ukrainian plural for "запис" — keep the table footer copy natural.
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "запис";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "записи";
  return "записів";
}
