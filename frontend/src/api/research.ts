import { request } from "./workbench";

export type ResearchRouteKind = "home" | "node" | "claim" | "source" | "relation" | "coverage" | "claims" | "sources";
export type SearchResult = {
  object_type: "NODE" | "CLAIM" | "SOURCE" | "RESEARCH_QUESTION" | "GAP";
  object_id: string;
  label: string;
  subtitle: string;
  status: string;
  node_type?: string;
  node_id?: string;
  matched_aliases?: string[];
};
export type Note = {
  note_id: string; object_type: string; object_id: string; text: string;
  status: "OPEN" | "DONE" | "DEFERRED"; revision: number; operator: string;
  created_at: string; updated_at: string;
  route_kind?: ResearchRouteKind; route_id?: string;
};

function params(values: Record<string, string | number | boolean | null | undefined>) {
  const search = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) search.set(key, String(value));
  });
  const encoded = search.toString();
  return encoded ? "?" + encoded : "";
}

export const getResearchHome = (signal: AbortSignal) => request<any>("/research/home", signal);
export const searchResearch = (q: string, objectType: string, signal: AbortSignal) =>
  request<{ query: string; results: SearchResult[] }>("/research/search" + params({ q, object_type: objectType, limit: 30 }), signal);
export const getResearchNode = (id: string, signal: AbortSignal) =>
  request<any>("/research/nodes/" + encodeURIComponent(id), signal);
export const getResearchClaim = (id: string, signal: AbortSignal) =>
  request<any>("/research/claims/" + encodeURIComponent(id), signal);
export const getResearchSource = (id: string, filters: Record<string, string>, signal: AbortSignal) =>
  request<any>("/research/sources/" + encodeURIComponent(id) + params(filters), signal);
export const getResearchRelation = (id: string, signal: AbortSignal) =>
  request<any>("/research/relations/" + encodeURIComponent(id), signal);
export const getResearchCoverage = (cursor: string, signal: AbortSignal) =>
  request<any>("/research/coverage" + params({ cursor, limit: 25 }), signal);
export const getResearchClaims = (filters: Record<string, string>, signal: AbortSignal) =>
  request<any>("/research/claims" + params({ ...filters, limit: 25 }), signal);
export const getResearchSources = (filters: Record<string, string>, signal: AbortSignal) =>
  request<any>("/research/sources" + params({ ...filters, limit: 25 }), signal);
export const createNote = (body: object, csrf: string, signal: AbortSignal) =>
  request<{ note: Note }>("/research/notes", signal, {
    method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body),
  });
export const updateNote = (id: string, body: object, csrf: string, signal: AbortSignal) =>
  request<{ note: Note }>("/research/notes/" + encodeURIComponent(id), signal, {
    method: "PUT", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify(body),
  });
