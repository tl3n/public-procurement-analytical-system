import { Link } from "@tanstack/react-router";

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

interface Props {
  tenders: TenderSummary[];
}

export function TenderTable({ tenders }: Props) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
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
          <TableRow key={t.id} className="cursor-pointer">
            <TableCell className="font-mono text-xs">
              <Link
                to="/tenders/$id"
                params={{ id: t.id }}
                className="hover:underline"
              >
                {t.tender_id_human ?? t.id.slice(0, 12)}
              </Link>
            </TableCell>
            <TableCell className="max-w-md">
              <Link
                to="/tenders/$id"
                params={{ id: t.id }}
                className="line-clamp-2 hover:underline"
                title={t.title ?? undefined}
              >
                {t.title ?? "—"}
              </Link>
            </TableCell>
            <TableCell className="text-muted-foreground">
              {t.procurement_method_type ?? "—"}
            </TableCell>
            <TableCell>
              <StatusBadge status={t.status} />
            </TableCell>
            <TableCell className="text-right">
              {formatMoney(t.value_amount, t.value_currency ?? "грн")}
            </TableCell>
            <TableCell className="max-w-xs truncate text-muted-foreground" title={t.buyer_name ?? undefined}>
              {t.buyer_name ?? "—"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
