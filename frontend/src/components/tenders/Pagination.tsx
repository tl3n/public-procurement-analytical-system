import { Button } from "@/components/ui/button";

interface Props {
  page: number;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
}

export function Pagination({ page, hasPrev, hasNext, onPrev, onNext }: Props) {
  return (
    <div className="flex items-center justify-between border-t px-4 py-3">
      <p className="text-xs text-muted-foreground">Сторінка {page}</p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onPrev}
          disabled={!hasPrev}
        >
          ← Попередня
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onNext}
          disabled={!hasNext}
        >
          Наступна →
        </Button>
      </div>
    </div>
  );
}
