import { Link, useNavigate } from "@tanstack/react-router";

import type { TenderSummary } from "@/api/types";
import { StatusBadge } from "@/components/tenders/StatusBadge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney } from "@/lib/format";
import { labelForType } from "@/lib/labels";

interface Props {
  tenders: TenderSummary[];
}

export function TenderTable({ tenders }: Props) {
  const navigate = useNavigate();

  return (
    <Table>
      <TableHeader>
        <TableRow className="bg-muted/40 hover:bg-muted/40">
          <TableHead className="w-44">№ Prozorro</TableHead>
          <TableHead>Назва</TableHead>
          <TableHead className="w-44">Тип</TableHead>
          <TableHead className="w-32">Статус</TableHead>
          <TableHead className="w-36 text-right">Вартість</TableHead>
          <TableHead className="w-72">Замовник</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tenders.map((t) => (
          <TableRow
            key={t.id}
            className="cursor-pointer"
            onClick={() => navigate({ to: "/tenders/$id", params: { id: t.id } })}
          >
            <TableCell className="font-mono text-xs">
              <Link
                to="/tenders/$id"
                params={{ id: t.id }}
                onClick={(e) => e.stopPropagation()}
                className="text-primary hover:underline"
              >
                {t.tender_id_human ?? t.id.slice(0, 12)}
              </Link>
            </TableCell>
            <TableCell className="max-w-md">
              <p className="line-clamp-2 text-sm" title={t.title ?? undefined}>
                {t.title ?? "—"}
              </p>
            </TableCell>
            <TableCell className="text-muted-foreground">
              {labelForType(t.procurement_method_type)}
            </TableCell>
            <TableCell>
              <StatusBadge status={t.status} />
            </TableCell>
            <TableCell className="text-right font-medium">
              {formatMoney(t.value_amount, t.value_currency ?? "грн")}
            </TableCell>
            <TableCell
              className="max-w-xs truncate text-muted-foreground"
              title={t.buyer_name ?? undefined}
            >
              {t.buyer_name ?? "—"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
