import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function TenderList() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Тендери</CardTitle>
        <CardDescription>
          Інтерактивний пошук та фільтрація тендерних процедур.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          Фільтри, таблиця з пагінацією та сортуванням з'являться в наступному
          коміті.
        </p>
      </CardContent>
    </Card>
  );
}
