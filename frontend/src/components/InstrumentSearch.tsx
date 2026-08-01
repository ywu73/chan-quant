import { FormEvent, useEffect, useId, useState } from "react";

import { searchInstruments } from "../api/instruments";
import type { InstrumentIdentity } from "../types/instrument";


interface InstrumentSearchProps {
  onSelect: (instrument: InstrumentIdentity) => void;
  variant?: "landing" | "compact";
  actionLabel?: string;
}


export function normalizeDirectSymbol(value: string): string | null {
  const normalized = value.trim().toUpperCase();
  return /^\d{6}\.(SZ|SH)$/.test(normalized) ? normalized : null;
}


export function directInstrumentFromSymbol(value: string): InstrumentIdentity | null {
  const symbol = normalizeDirectSymbol(value);
  if (symbol === null) return null;
  return {
    symbol,
    name: symbol,
    exchange: symbol.endsWith(".SZ") ? "SZ" : "SH",
    asset_type: "UNKNOWN",
    price_precision: 2,
  };
}


export function InstrumentSearch({
  onSelect,
  variant = "landing",
  actionLabel,
}: InstrumentSearchProps) {
  const inputId = useId();
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<InstrumentIdentity[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const directSymbol = normalizeDirectSymbol(query);
  const directInstrument = directInstrumentFromSymbol(query);
  const normalizedQuery = query.trim();

  const selectInstrument = (instrument: InstrumentIdentity) => {
    setQuery("");
    setItems([]);
    setIsLoading(false);
    setHasSearched(false);
    setError(null);
    onSelect(instrument);
  };

  useEffect(() => {
    if (!normalizedQuery || directSymbol) {
      setItems([]);
      setIsLoading(false);
      setHasSearched(false);
      setError(null);
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setIsLoading(true);
      setError(null);
      searchInstruments(normalizedQuery, controller.signal)
        .then((response) => {
          setItems(response.items);
          setHasSearched(true);
        })
        .catch((reason: unknown) => {
          if (reason instanceof DOMException && reason.name === "AbortError") {
            return;
          }
          setItems([]);
          setHasSearched(true);
          setError(reason instanceof Error ? reason.message : "证券搜索不可用");
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setIsLoading(false);
          }
        });
    }, 250);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [directSymbol, normalizedQuery]);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (directInstrument) {
      selectInstrument(directInstrument);
    } else if (!isLoading && items.length === 1) {
      selectInstrument(items[0]);
    }
  };

  const hasResults = directSymbol !== null || items.length > 0;
  const statusId = `${inputId}-status`;
  const listId = `${inputId}-results`;

  return (
    <div className={`instrument-search instrument-search--${variant}`}>
      <form className="instrument-search__form" onSubmit={submit} role="search">
        <label className="sr-only" htmlFor={inputId}>
          搜索股票、ETF 或指数代码或名称
        </label>
        <span className="instrument-search__icon" aria-hidden="true">⌕</span>
        <input
          id={inputId}
          type="search"
          value={query}
          placeholder="搜索代码或名称，例如 600519、513100、纳指ETF"
          autoComplete="off"
          autoFocus={variant === "landing"}
          aria-controls={listId}
          aria-describedby={statusId}
          aria-expanded={hasResults}
          aria-haspopup="listbox"
          onChange={(event) => setQuery(event.target.value)}
        />
        <button
          type="submit"
          disabled={!directSymbol && (isLoading || items.length !== 1)}
        >
          {actionLabel ?? (variant === "landing" ? "开始研究" : "切换")}
        </button>
      </form>

      <div className="instrument-search__popover">
        {directInstrument && (
          <div className="instrument-search__results" id={listId} role="listbox">
            <button
              type="button"
              role="option"
              aria-selected="false"
              onClick={() => selectInstrument(directInstrument)}
            >
              <span>
                <strong>{directInstrument.symbol}</strong>
                <small>规范代码 · 直接打开</small>
              </span>
              <span className="instrument-search__exchange">
                {directInstrument.exchange === "SZ" ? "深市" : "沪市"}
              </span>
            </button>
          </div>
        )}
        {!directSymbol && items.length > 0 && (
          <div className="instrument-search__results" id={listId} role="listbox">
            {items.map((item) => (
              <button
                type="button"
                role="option"
                aria-selected="false"
                key={item.symbol}
                onClick={() => selectInstrument(item)}
              >
                <span>
                  <strong>{item.name}</strong>
                  <small>
                    {item.symbol}{item.asset_type === "ETF" ? " · ETF" : ""}
                  </small>
                </span>
                <span className="instrument-search__exchange">
                  {item.exchange === "SZ" ? "深市" : "沪市"}
                </span>
              </button>
            ))}
            <p className="instrument-search__source">
              名称匹配来自新浪未文档化建议端点，仅用于选择研究标的
            </p>
          </div>
        )}
      </div>

      <p
        className={`instrument-search__status${error ? " instrument-search__status--error" : ""}`}
        id={statusId}
        aria-live="polite"
      >
        {isLoading && "正在搜索…"}
        {!isLoading && error}
        {!isLoading && !error && hasSearched && items.length === 0 &&
          "没有找到匹配的沪深股票、ETF 或指数"}
        {!isLoading && !error && !hasSearched && normalizedQuery.length === 6 && !directSymbol &&
          "六位代码可能对应不同市场，请从搜索结果中选择"}
      </p>
    </div>
  );
}
