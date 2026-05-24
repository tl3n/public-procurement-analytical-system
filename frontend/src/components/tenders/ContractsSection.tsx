import type { ContractOut } from "@/api/types";
import {
  Card,
  CardContent,
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
import { formatMoney } from "@/lib/format";

import { StatusBadge } from "./StatusBadge";

interface Props {
  contracts: ContractOut[];
}

export function ContractsSection({ contracts }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Договори</CardTitle>
        {contracts.length === 0 && (
          <CardDescription>Договори не укладено.</CardDescription>
        )}
      </CardHeader>
      {contracts.length > 0 && (
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Постачальник</TableHead>
                <TableHead className="w-32">Статус</TableHead>
                <TableHead className="w-36">Дата підписання</TableHead>
                <TableHead className="w-36 text-right">Сума</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {contracts.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>
                    {c.supplier_name ?? "—"}
                    {c.supplier_edrpou && (
                      <span className="ml-1 text-xs text-muted-foreground">
                        ({c.supplier_edrpou})
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={c.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {c.date_signed
                      ? new Date(c.date_signed).toLocaleDateString("uk-UA")
                      : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(c.value_amount, c.value_currency ?? "грн")}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      )}
    </Card>
  );
}
