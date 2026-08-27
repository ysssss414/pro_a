import type { CurrentViewContent } from "./api/types";

export interface PresentationSection { title: string; value: string | string[]; }
export interface CurrentViewPresentation {
  structured: boolean;
  sections: PresentationSection[];
  evidenceCount: number;
  hasSource: boolean;
  recentChange?: string;
}

const text = (value: unknown): string => typeof value === "string" ? value.trim() : "";
const strings = (value: unknown): string[] => Array.isArray(value)
  ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
  : [];
const unique = (values: string[]) => [...new Set(values)];

const PRODUCT_DIMENSION_LABELS: Record<string, string> = {
  applications: "应用场景",
  demand_drivers: "需求驱动",
  pricing: "价格",
  supply: "供给",
  capacity: "产能",
  supply_capacity: "供给与产能",
  competition: "竞争格局",
  major_suppliers: "主要供应商",
  technology: "技术演进",
  product_evolution: "产品演进",
  inventory: "库存",
};

const MLCC_ATTRIBUTION_PREFIXES = [
  "据该材料，",
  "据现有财通证券业绩会更新材料，",
];

function normalizedStatement(value: string): string {
  let normalized = value.trim();
  const prefix = MLCC_ATTRIBUTION_PREFIXES.find((item) => normalized.startsWith(item));
  if (prefix) normalized = normalized.slice(prefix.length);
  return normalized.replace(/[。；]$/, "").trim();
}

function factsNotRepeatedInConclusion(keyFacts: string[], conclusion: string): string[] {
  const conclusionStatements = new Set(
    conclusion.split(/[；。]/).map(normalizedStatement).filter(Boolean),
  );
  return keyFacts.filter((item) => !conclusionStatements.has(normalizedStatement(item)));
}

function evidenceBoundary(content: CurrentViewContent): string[] {
  return unique([
    ...strings(content.core_disagreements),
    ...strings(content.assumptions_to_verify),
    ...strings(content.knowledge_gaps),
    ...strings(content.major_risks),
  ]);
}

function dimensions(content: CurrentViewContent, keyFacts: string[]): string[] {
  if (!content.type_specific || typeof content.type_specific !== "object") return [];
  const result: string[] = [];
  for (const [key, raw] of Object.entries(content.type_specific as Record<string, unknown>)) {
    const values = Array.isArray(raw) ? raw.filter((item): item is string => typeof item === "string") : [];
    const remaining = unique(values.filter((item) => !keyFacts.includes(item)));
    if (remaining.length) {
      const label = PRODUCT_DIMENSION_LABELS[key] ?? key;
      result.push(`${label}: ${remaining.join("；")}`);
    }
  }
  return result;
}

export function buildCurrentViewPresentation(
  content: CurrentViewContent,
  primaryType: string,
  triggerClaimCount: number,
  hasSource: boolean,
  hasPreviousView: boolean,
): CurrentViewPresentation {
  const conclusion = text(content.one_line_conclusion);
  const keyFacts = strings(content.key_facts);
  const visibleKeyFacts = primaryType === "Product"
    ? factsNotRepeatedInConclusion(keyFacts, conclusion)
    : keyFacts;
  const sections: PresentationSection[] = [];
  if (conclusion) sections.push({ title: "当前判断", value: conclusion });
  if (visibleKeyFacts.length) {
    sections.push({ title: primaryType === "Company" ? "关键进展" : "关键变化", value: visibleKeyFacts });
  }
  if (primaryType === "Product") {
    const values = dimensions(content, keyFacts);
    if (values.length) sections.push({ title: "专业维度", value: values });
  }
  const investment = text(content.investment_implication);
  if (investment) sections.push({ title: primaryType === "Company" ? "投资逻辑" : "投资含义", value: investment });
  const watches = strings(content.key_watch_items);
  if (watches.length) sections.push({ title: "关键验证点", value: watches });
  const boundary = evidenceBoundary(content);
  if (boundary.length) sections.push({ title: "证据边界", value: boundary });
  return {
    structured: Boolean(conclusion || keyFacts.length || investment || watches.length),
    sections,
    evidenceCount: triggerClaimCount,
    hasSource,
    recentChange: hasPreviousView ? text(content.recent_change) || undefined : undefined,
  };
}
