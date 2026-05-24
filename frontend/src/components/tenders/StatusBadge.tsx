import { Badge } from "@/components/ui/badge";
import { labelForStatus } from "@/lib/labels";

const STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "success" | "danger" | "warning"
> = {
  complete: "success",
  "active.awarded": "success",
  "active.qualification": "warning",
  "active.tendering": "warning",
  "active.enquiries": "warning",
  "active.auction": "warning",
  cancelled: "danger",
  unsuccessful: "danger",
  draft: "secondary",
};

export function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <Badge variant="secondary">—</Badge>;
  const variant = STATUS_VARIANT[status] ?? "secondary";
  return <Badge variant={variant}>{labelForStatus(status)}</Badge>;
}
