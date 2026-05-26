import { useState } from "react";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SearchX } from "lucide-react";

import { api } from "@/api/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { FilterSidebar, type Filters } from "@/components/tenders/FilterSidebar";
import { Pagination } from "@/components/tenders/Pagination";
import { TenderTable } from "@/components/tenders/TenderTable";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function TenderList() {
  const [filters, setFilters] = useState<Filters>({});
  // Cursor pagination is forward-only; we keep the stack of cursors we have
  // walked through so "Попередня" pops back to the previous page.
  const [cursorStack, setCursorStack] = useState<(string | null)[]>([null]);
  const currentCursor = cursorStack[cursorStack.length - 1];

  const query = useQuery({
    queryKey: ["tenders", filters, currentCursor],
    queryFn: () =>
      api.listTenders({
        ...filters,
        cursor: currentCursor ?? undefined,
        limit: 20,
      }),
    placeholderData: keepPreviousData,
  });

  const activeFilterCount = Object.entries(filters).filter(([, v]) => {
    if (Array.isArray(v)) return v.length > 0;
    return v !== undefined && v !== "";
  }).length;

  function applyFilters(next: Filters) {
    setFilters(next);
    setCursorStack([null]);
  }
  function resetFilters() {
    setFilters({});
    setCursorStack([null]);
  }
  function nextPage() {
    if (query.data?.next_cursor) {
      setCursorStack((s) => [...s, query.data!.next_cursor!]);
    }
  }
  function prevPage() {
    if (cursorStack.length > 1) {
      setCursorStack((s) => s.slice(0, -1));
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Тендери"
        description={
          activeFilterCount > 0
            ? `Активних фільтрів: ${activeFilterCount}`
            : "Інтерактивний пошук та фільтрація процедур з відкритого API Prozorro."
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        <FilterSidebar
          values={filters}
          onApply={applyFilters}
          onReset={resetFilters}
        />
        <Card className="flex flex-col">
          <CardContent className="p-0">
            {query.isError ? (
              <ErrorState message={(query.error as Error).message} />
            ) : query.isPending ? (
              <LoadingState />
            ) : query.data.data.length === 0 ? (
              <EmptyState
                onReset={resetFilters}
                hasFilters={activeFilterCount > 0}
              />
            ) : (
              <>
                <TenderTable tenders={query.data.data} />
                <Pagination
                  page={cursorStack.length}
                  pageSize={query.data.data.length}
                  hasPrev={cursorStack.length > 1}
                  hasNext={Boolean(query.data.next_cursor)}
                  onPrev={prevPage}
                  onNext={nextPage}
                />
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col divide-y">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex animate-pulse items-center gap-4 px-3 py-3">
          <div className="h-3 w-32 rounded bg-muted" />
          <div className="h-3 flex-1 rounded bg-muted" />
          <div className="h-3 w-20 rounded bg-muted" />
          <div className="h-3 w-24 rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}

function EmptyState({
  onReset,
  hasFilters,
}: {
  onReset: () => void;
  hasFilters: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-10 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-muted text-muted-foreground">
        <SearchX className="h-6 w-6" />
      </span>
      <p className="text-sm font-medium">
        {hasFilters
          ? "За цими фільтрами нічого не знайдено."
          : "У базі поки немає тендерів."}
      </p>
      <p className="max-w-md text-xs text-muted-foreground">
        {hasFilters
          ? "Спробуйте розширити критерії або скиньте фільтри."
          : "Зачекайте на завершення першого циклу синхронізації або запустіть seed_demo."}
      </p>
      {hasFilters && (
        <Button variant="outline" size="sm" onClick={onReset}>
          Скинути фільтри
        </Button>
      )}
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="p-8 text-center">
      <p className="text-sm font-medium text-foreground">
        Не вдалось завантажити перелік тендерів.
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{message}</p>
    </div>
  );
}
