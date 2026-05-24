import type { LotOut } from "@/api/types";
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
import { formatCount, formatMoney } from "@/lib/format";

import { StatusBadge } from "./StatusBadge";

interface Props {
  lots: LotOut[];
}

export function LotsSection({ lots }: Props) {
  if (lots.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Лоти</CardTitle>
          <CardDescription>Лотів не зареєстровано.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {lots.map((lot, idx) => (
        <Card key={lot.id}>
          <CardHeader>
            <CardTitle className="text-base">
              Лот №{idx + 1}
              {lot.title ? ` — ${lot.title}` : ""}
            </CardTitle>
            {lot.value_amount && (
              <CardDescription>
                Очікувана вартість лота:{" "}
                {formatMoney(lot.value_amount, lot.value_currency ?? "грн")}
              </CardDescription>
            )}
          </CardHeader>
          <CardContent className="flex flex-col gap-6">
            {lot.items.length > 0 && (
              <Block title="Предмети закупівлі">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Опис</TableHead>
                      <TableHead className="w-32">CPV</TableHead>
                      <TableHead className="w-24 text-right">Кількість</TableHead>
                      <TableHead className="w-24">Од.</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {lot.items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="max-w-md">
                          {item.description ?? "—"}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {item.cpv_code ?? "—"}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCount(item.quantity)}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {item.unit ?? "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Block>
            )}

            {lot.bids.length > 0 ? (
              <Block title={`Пропозиції (${lot.bids.length})`}>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Постачальник</TableHead>
                      <TableHead className="w-32">Статус</TableHead>
                      <TableHead className="w-36 text-right">Ціна</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {lot.bids.map((bid) => (
                      <TableRow key={bid.id}>
                        <TableCell>
                          {bid.supplier_name ?? "—"}
                          {bid.supplier_edrpou && (
                            <span className="ml-1 text-xs text-muted-foreground">
                              ({bid.supplier_edrpou})
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={bid.status} />
                        </TableCell>
                        <TableCell className="text-right">
                          {formatMoney(
                            bid.value_amount,
                            bid.value_currency ?? "грн",
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Block>
            ) : (
              <p className="text-sm text-muted-foreground">
                Пропозицій не подано.
              </p>
            )}

            {lot.awards.length > 0 && (
              <Block title="Присудження">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Постачальник</TableHead>
                      <TableHead className="w-32">Статус</TableHead>
                      <TableHead className="w-36 text-right">Сума</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {lot.awards.map((aw) => (
                      <TableRow key={aw.id}>
                        <TableCell>
                          {aw.supplier_name ?? "—"}
                          {aw.supplier_edrpou && (
                            <span className="ml-1 text-xs text-muted-foreground">
                              ({aw.supplier_edrpou})
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={aw.status} />
                        </TableCell>
                        <TableCell className="text-right">
                          {formatMoney(aw.value_amount, aw.value_currency ?? "грн")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Block>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function Block({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-sm font-semibold">{title}</h4>
      {children}
    </div>
  );
}
