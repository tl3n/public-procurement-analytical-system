import type { BuyerRankOut, SupplierRankOut } from "@/api/types";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCount, formatMoney } from "@/lib/format";

interface Props {
  buyers: BuyerRankOut[];
  suppliers: SupplierRankOut[];
}

export function RankingsBlock({ buyers, suppliers }: Props) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Card className="p-4">
        <CardHeader className="p-0 pb-3">
          <CardTitle className="text-base">Топ замовників</CardTitle>
          <CardDescription>За загальною вартістю тендерів</CardDescription>
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Замовник</TableHead>
              <TableHead className="w-20 text-right">Кількість</TableHead>
              <TableHead className="w-36 text-right">Вартість</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {buyers.map((b) => (
              <TableRow key={b.edrpou ?? b.name ?? Math.random()}>
                <TableCell className="max-w-md">
                  <p className="line-clamp-2 text-sm" title={b.name ?? undefined}>
                    {b.name ?? "—"}
                  </p>
                  {b.edrpou && (
                    <p className="text-xs text-muted-foreground">{b.edrpou}</p>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  {formatCount(b.tender_count)}
                </TableCell>
                <TableCell className="text-right font-medium">
                  {formatMoney(b.total_value)}
                </TableCell>
              </TableRow>
            ))}
            {buyers.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="py-6 text-center text-sm text-muted-foreground">
                  Дані відсутні.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      <Card className="p-4">
        <CardHeader className="p-0 pb-3">
          <CardTitle className="text-base">Топ постачальників</CardTitle>
          <CardDescription>За сумою укладених договорів</CardDescription>
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Постачальник</TableHead>
              <TableHead className="w-20 text-right">Договорів</TableHead>
              <TableHead className="w-36 text-right">Сума</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {suppliers.map((s) => (
              <TableRow key={s.edrpou ?? s.name ?? Math.random()}>
                <TableCell className="max-w-md">
                  <p className="line-clamp-2 text-sm" title={s.name ?? undefined}>
                    {s.name ?? "—"}
                  </p>
                  {s.edrpou && (
                    <p className="text-xs text-muted-foreground">{s.edrpou}</p>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  {formatCount(s.contract_count)}
                </TableCell>
                <TableCell className="text-right font-medium">
                  {formatMoney(s.total_value)}
                </TableCell>
              </TableRow>
            ))}
            {suppliers.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="py-6 text-center text-sm text-muted-foreground">
                  Дані відсутні.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
