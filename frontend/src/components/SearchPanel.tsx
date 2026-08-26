import { useEffect, useState } from "react";

import { searchNodes } from "../api/client";
import type { NodeSearchResult } from "../api/types";

interface SearchPanelProps {
  selectedNodeId: string | null;
  onSelect: (nodeId: string) => void;
}

export function SearchPanel({ selectedNodeId, onSelect }: SearchPanelProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<NodeSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      setLoading(false);
      setError(null);
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        setResults(await searchNodes(trimmed, 20, controller.signal));
      } catch (requestError) {
        if ((requestError as Error).name !== "AbortError") {
          setResults([]);
          setError("Search unavailable. Check the local Knowledge API.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 250);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [query]);

  const trimmed = query.trim();

  return (
    <section className="search-panel" aria-labelledby="search-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Discover</p>
          <h2 id="search-heading">Search</h2>
        </div>
        {results.length > 0 && <span className="count-label">{results.length}</span>}
      </div>

      <label className="search-label" htmlFor="node-search">
        Search nodes or aliases
      </label>
      <div className="search-input-wrap">
        <span aria-hidden="true" className="search-icon">⌕</span>
        <input
          id="node-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search nodes or aliases…"
          autoComplete="off"
        />
      </div>

      <div className="search-feedback" aria-live="polite">
        {loading && "Searching…"}
        {error && <span className="error-text">{error}</span>}
        {!loading && !error && trimmed && results.length === 0 && "No matching nodes."}
        {!trimmed && "Try EML, optical, HBM, or a known alias."}
      </div>

      <div className="search-results" aria-label="Search results">
        {results.map((result) => (
          <button
            type="button"
            key={result.node_id}
            className={`search-result ${selectedNodeId === result.node_id ? "is-selected" : ""}`}
            onClick={() => onSelect(result.node_id)}
            aria-pressed={selectedNodeId === result.node_id}
          >
            <span className="result-name">{result.canonical_name}</span>
            <span className="result-type">{result.primary_type}</span>
            {result.matched_by === "alias" && (
              <span className="result-match">Matched alias: {result.matched_text}</span>
            )}
          </button>
        ))}
      </div>
    </section>
  );
}
