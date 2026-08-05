import { FormEvent, useEffect, useId, useRef, useState } from "react";

import { resolveInstrument, searchInstruments } from "../api/instruments";
import type { InstrumentIdentity } from "../types/instrument";


interface InstrumentSearchProps {
  onSelect: (instrument: InstrumentIdentity) => void;
  variant?: "landing" | "compact";
  actionLabel?: string;
}


export function normalizeDirectSymbol(value: string): string | null {
  const normalized = value.trim().toUpperCase();
  const supported = [
    /^\d{6}\.(SZ|SH)$/,
    /^\d{5}\.HK$/,
    /^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)*\.US$/,
    /^[A-Z][A-Z0-9.-]*\.GI$/,
  ];
  return supported.some((pattern) => pattern.test(normalized)) ? normalized : null;
}


interface DirectInstrumentCandidate {
  symbol: string;
  market: "CN" | "HK" | "US" | "GLOBAL";
}


export function directInstrumentFromSymbol(value: string): DirectInstrumentCandidate | null {
  const symbol = normalizeDirectSymbol(value);
  if (symbol === null) return null;
  return {
    symbol,
    market: symbol.endsWith(".HK")
      ? "HK"
      : symbol.endsWith(".US")
        ? "US"
        : symbol.endsWith(".GI")
          ? "GLOBAL"
          : "CN",
  };
}


function marketLabel(instrument: Pick<InstrumentIdentity, "market" | "exchange">): string {
  if (instrument.exchange === "SZ") return "深市";
  if (instrument.exchange === "SH") return "沪市";
  if (instrument.market === "HK") return "港股";
  if (instrument.market === "US") return "美股";
  if (instrument.market === "GLOBAL") return "全球指数";
  return "身份待确认";
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
  const directResolutionRef = useRef<AbortController | null>(null);
  const normalizedQuery = query.trim();

  const selectInstrument = (instrument: InstrumentIdentity) => {
    directResolutionRef.current?.abort();
    directResolutionRef.current = null;
    setQuery("");
    setItems([]);
    setIsLoading(false);
    setHasSearched(false);
    setError(null);
    onSelect(instrument);
  };

  const resolveDirectSelection = (candidate: DirectInstrumentCandidate) => {
    directResolutionRef.current?.abort();
    const controller = new AbortController();
    directResolutionRef.current = controller;
    setIsLoading(true);
    setError(null);
    resolveInstrument(candidate.symbol, controller.signal)
      .then(selectInstrument)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "无法确认规范证券身份");
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });
  };

  useEffect(() => () => directResolutionRef.current?.abort(), []);

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
      resolveDirectSelection(directInstrument);
    } else if (!isLoading && items.length === 1) {
      selectInstrument(items[0]);
    }
  };

  const hasResults = directInstrument !== null || items.length > 0;
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
          placeholder="搜索名称，或输入 600519.SH、00700.HK、AAPL.US、SPX.GI"
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
          disabled={isLoading || (!directInstrument && items.length !== 1)}
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
              disabled={isLoading}
              onClick={() => resolveDirectSelection(directInstrument)}
            >
              <span>
                <strong>{directInstrument.symbol}</strong>
                <small>规范代码 · 直接打开</small>
              </span>
              <span className="instrument-search__exchange">
                {marketLabel({ market: directInstrument.market, exchange: null })}
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
                  {marketLabel(item)}
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
          "没有找到匹配的沪深股票、ETF 或指数；跨市场标的需输入已审计规范代码"}
        {!isLoading && !error && !hasSearched && normalizedQuery.length === 6 && !directSymbol &&
          "六位代码可能对应不同市场，请从搜索结果中选择"}
      </p>
    </div>
  );
}
