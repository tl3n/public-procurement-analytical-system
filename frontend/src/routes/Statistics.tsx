import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function Statistics() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Статистика</CardTitle>
        <CardDescription>
          Рейтинги, розподіли та динаміка індикаторів ризику.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          Аналітичні графіки та таблиці з'являться в наступному коміті.
        </p>
      </CardContent>
    </Card>
  );
}
