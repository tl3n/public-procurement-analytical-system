// Human-readable metadata for the risk indicators. The backend's
// ``Indicator.describe()`` is the source of truth — keep these strings in
// sync when the indicator set evolves.

export interface IndicatorMeta {
  code: string;
  name: string;
  interpretation: string;
  valueType: "boolean" | "numeric";
}

export const INDICATOR_METADATA: Record<string, IndicatorMeta> = {
  "risk.single_bidding": {
    code: "risk.single_bidding",
    name: "Одиночне подання",
    interpretation:
      "Конкурентна процедура із завершеним прийомом пропозицій, у якій взяв участь лише один учасник. NULL — період подання ще триває або процедура не є конкурентною.",
    valueType: "boolean",
  },
  "risk.non_competitive": {
    code: "risk.non_competitive",
    name: "Неконкурентна процедура",
    interpretation:
      "Тип процедури передбачає обмежений доступ (negotiation, negotiation.quick, reporting).",
    valueType: "boolean",
  },
  "risk.shortened_period": {
    code: "risk.shortened_period",
    name: "Скорочений строк подачі",
    interpretation:
      "Кількість робочих днів між публікацією та крайнім строком подачі менша за законодавчий мінімум для цього типу процедури.",
    valueType: "boolean",
  },
  "risk.buyer_concentration": {
    code: "risk.buyer_concentration",
    name: "Концентрація витрат замовника",
    interpretation:
      "Максимальна частка одного постачальника у договорах замовника за останні 12 місяців. 0–1; значення близькі до 1 свідчать про захоплення ринку.",
    valueType: "numeric",
  },
  "risk.price_deviation": {
    code: "risk.price_deviation",
    name: "Цінове відхилення від медіани CPV",
    interpretation:
      "Знакове відносне відхилення очікуваної вартості від медіани тендерів з тим самим CPV за останні 12 місяців. NULL — менше 30 порівняльних тендерів.",
    valueType: "numeric",
  },
};

export function lookupIndicator(code: string): IndicatorMeta {
  return (
    INDICATOR_METADATA[code] ?? {
      code,
      name: code,
      interpretation: "Опис відсутній.",
      valueType: "boolean",
    }
  );
}
