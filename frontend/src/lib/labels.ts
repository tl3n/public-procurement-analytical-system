// User-facing Ukrainian labels for API enum values. The backend uses the raw
// Prozorro identifiers (e.g. ``aboveThresholdUA``) on the wire; we translate
// only at the boundary, so filters and queries keep using the canonical
// strings.

export const PROCEDURE_TYPE_LABELS: Record<string, string> = {
  open: "Відкриті торги",
  aboveThreshold: "Понадпорогові",
  aboveThresholdUA: "Понадпорогові (UA)",
  aboveThresholdEU: "Понадпорогові (EU)",
  belowThreshold: "Допорогові",
  priceQuotation: "Запит цінових пропозицій",
  negotiation: "Переговорна процедура",
  "negotiation.quick": "Переговорна (скорочена)",
  reporting: "Звіт про договір",
  competitiveOrdering: "Конкурентне замовлення",
  competitiveDialogueUA: "Конкурентний діалог (UA)",
  competitiveDialogueEU: "Конкурентний діалог (EU)",
  closeFrameworkAgreementUA: "Рамкова угода (UA)",
  closeFrameworkAgreementSelectionUA: "Відбір за рамковою угодою",
  esco: "ESCO-договір",
  simple: "Спрощена закупівля",
  "simple.defense": "Оборонна спрощена",
  "aboveThresholdUA.defense": "Оборонна понадпорогова",
};

export const STATUS_LABELS: Record<string, string> = {
  draft: "Чернетка",
  "active.enquiries": "Період запитань",
  "active.tendering": "Прийом пропозицій",
  "active.auction": "Аукціон",
  "active.qualification": "Кваліфікація",
  "active.awarded": "Присуджено",
  complete: "Завершено",
  cancelled: "Скасовано",
  unsuccessful: "Безуспішно",
};

export function labelForType(t: string | null | undefined): string {
  if (!t) return "—";
  return PROCEDURE_TYPE_LABELS[t] ?? t;
}

export function labelForStatus(s: string | null | undefined): string {
  if (!s) return "—";
  return STATUS_LABELS[s] ?? s;
}
