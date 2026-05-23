import { useParams } from "@tanstack/react-router";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function TenderDetail() {
  const { id } = useParams({ from: "/tenders/$id" });
  return (
    <Card>
      <CardHeader>
        <CardTitle>Деталі тендеру</CardTitle>
        <CardDescription>ID: {id}</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          Повна картка процедури з лотами, пропозиціями та індикаторами ризику
          буде реалізована в наступному коміті.
        </p>
      </CardContent>
    </Card>
  );
}
