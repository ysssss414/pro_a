import type { SourceLocator } from "../api/types";

function label(value: string): string {
  const sheet = /^SHEET:(.+?)(?::ROW:(\d+))?$/.exec(value);
  if (sheet) return `Sheet: ${sheet[1]}${sheet[2] ? ` · Row: ${sheet[2]}` : ""}`;
  const table = /^TABLE:(\d+)(?::ROW:(\d+))?$/.exec(value);
  if (table) return `Table ${table[1]}${table[2] ? ` · Row: ${table[2]}` : ""}`;
  const unit = /^(PAGE|PARA|SLIDE):(\d+)$/.exec(value);
  if (unit) return `${{ PAGE: "Page", PARA: "Paragraph", SLIDE: "Slide" }[unit[1]]} ${unit[2]}`;
  return value === "TEXT" ? "Text document" : value;
}

export function SourceLocatorLabel({ locator }: { locator?: SourceLocator | null }) {
  if (!locator) return null;
  if (locator.status === "resolved" && locator.locator) {
    return <p className="source-locator">Source locator: {label(locator.locator)}</p>;
  }
  if (locator.status === "ambiguous") {
    return <p className="source-locator">Source locator ambiguous: {(locator.locators ?? []).map(label).join("; ")}</p>;
  }
  return <p className="source-locator">Source locator unresolved</p>;
}
