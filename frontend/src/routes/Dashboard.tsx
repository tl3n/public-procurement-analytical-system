import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function Dashboard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Дашборд</CardTitle>
        <CardDescription>
          Огляд ключових показників системи моніторингу.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          KPI-картки, графіки динаміки та блок тендерів з найвищим ризиком будуть
          реалізовані в наступному коміті.
        </p>
      </CardContent>
    </Card>
  );
}
