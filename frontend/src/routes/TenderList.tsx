import { useState } from "react";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { FilterSidebar, type Filters } from "@/components/tenders/FilterSidebar";
import { Pagination } from "@/components/tenders/Pagination";
import { TenderTable } from "@/components/tenders/TenderTable";
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
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
      <FilterSidebar
        values={filters}
        onApply={applyFilters}
        onReset={resetFilters}
      />
      <Card className="flex flex-col">
        <CardContent className="p-0">
          {query.isError ? (
            <div className="p-8 text-center">
              <p className="text-sm text-foreground">
                Не вдалось завантажити перелік тендерів.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {(query.error as Error).message}
              </p>
            </div>
          ) : query.isPending ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              Завантаження…
            </div>
          ) : query.data.data.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              За цими фільтрами нічого не знайдено.
            </div>
          ) : (
            <>
              <TenderTable tenders={query.data.data} />
              <Pagination
                page={cursorStack.length}
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
  );
}
