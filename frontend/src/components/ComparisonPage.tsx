import { useEffect, useRef, useState } from "react";

import { fetchMarketComparison } from "../api/comparison";
import {
  BUILT_IN_BOARDS,
  COMPARISON_MAX_INSTRUMENTS,
  COMPARISON_MIN_INSTRUMENTS,
  prepareBoardSelection,
  type BoardInstrument,
  type BuiltInBoard,
  type StoredBoardV1,
} from "../comparisonBoards";
import type { ComparisonQuoteState } from "../comparisonQuotePolling";
import { createComparisonRequestRunner } from "../comparisonRequest";
import type { MarketComparison } from "../types/comparison";
import type { InstrumentIdentity } from "../types/instrument";
import { useComparisonBoards } from "../useComparisonBoards";
import { useComparisonQuotes } from "../useComparisonQuotes";
import { ComparisonBoardPicker } from "./ComparisonBoardPicker";
import { ComparisonChart } from "./ComparisonChart";
import { ComparisonMetricCard } from "./ComparisonMetricCard";
import { InstrumentSearch } from "./InstrumentSearch";


function formatDateRange(start: string | null, end: string | null): string {
  return start && end ? `${start} — ${end}` : "没有可比较的共同日期区间";
}

function toBoardInstrument(instrument: InstrumentIdentity): BoardInstrument {
  return {
    symbol: instrument.symbol,
    name: instrument.name,
    exchange: instrument.exchange,
    asset_type: instrument.asset_type,
    price_precision: instrument.price_precision,
  };
}

export function ComparisonPage() {
  const [instruments, setInstruments] = useState<BoardInstrument[]>([]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [comparison, setComparison] = useState<MarketComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreatingBoard, setIsCreatingBoard] = useState(false);
  const [boardName, setBoardName] = useState("");
  const requestRunnerRef = useRef<ReturnType<typeof createComparisonRequestRunner> | null>(null);
  const boardState = useComparisonBoards();
  const comparisonSymbols = comparison?.series.map((series) => series.instrument.symbol) ?? [];
  const quoteStates = useComparisonQuotes(comparisonSymbols);

  if (requestRunnerRef.current === null) {
    requestRunnerRef.current = createComparisonRequestRunner(fetchMarketComparison);
  }

  useEffect(() => () => requestRunnerRef.current?.invalidate(), []);

  const invalidateResult = () => {
    requestRunnerRef.current?.invalidate();
    setComparison(null);
    setIsLoading(false);
  };

  const addInstrument = (instrument: InstrumentIdentity) => {
    setError(null);
    setNotice(null);
    if (instruments.some((item) => item.symbol === instrument.symbol)) return;
    if (instruments.length >= COMPARISON_MAX_INSTRUMENTS) {
      setError(`一次最多比较 ${COMPARISON_MAX_INSTRUMENTS} 个标的`);
      return;
    }
    invalidateResult();
    setInstruments([...instruments, toBoardInstrument(instrument)]);
  };

  const removeInstrument = (symbol: string) => {
    invalidateResult();
    setInstruments((current) => current.filter((item) => item.symbol !== symbol));
    setError(null);
    setNotice(null);
  };

  const loadBoard = (board: BuiltInBoard | StoredBoardV1) => {
    try {
      const selection = prepareBoardSelection(board.instruments);
      invalidateResult();
      setInstruments(selection);
      setError(null);
      setNotice(`已装载“${board.name}”的 ${selection.length} 个标的`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "板块成员无法装载");
      setNotice(null);
    }
  };

  const saveBoard = () => {
    try {
      const saved = boardState.save(boardName, instruments);
      setBoardName("");
      setIsCreatingBoard(false);
      setError(null);
      setNotice(`已保存自定义板块“${saved.name}”`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存自定义板块失败");
    }
  };

  const deleteBoard = (id: string) => {
    try {
      boardState.remove(id);
      setNotice("自定义板块已删除");
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "删除自定义板块失败");
    }
  };

  const clearBoardStorage = () => {
    try {
      boardState.clear();
      setNotice("自定义板块存储已清除，可以重新保存");
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "清除自定义板块存储失败");
    }
  };

  const changeStart = (value: string) => {
    invalidateResult();
    setStart(value);
    setError(null);
  };

  const changeEnd = (value: string) => {
    invalidateResult();
    setEnd(value);
    setError(null);
  };

  const submit = () => {
    if (instruments.length < COMPARISON_MIN_INSTRUMENTS) {
      setError(`请先选择至少 ${COMPARISON_MIN_INSTRUMENTS} 个标的`);
      return;
    }
    if (start && end && start > end) {
      setError("开始日期不能晚于结束日期");
      return;
    }

    setIsLoading(true);
    setComparison(null);
    setError(null);
    setNotice(null);
    requestRunnerRef.current?.run(
      instruments.map((instrument) => instrument.symbol),
      { start: start || undefined, end: end || undefined },
      {
        success: setComparison,
        failure: (reason: unknown) => {
          setComparison(null);
          setError(reason instanceof Error ? reason.message : "读取走势对比失败");
        },
        settled: () => setIsLoading(false),
      },
    );
  };

  return (
    <main className="comparison-shell">
      <section className="comparison-hero">
        <div>
          <p className="eyebrow">MULTI-INSTRUMENT RESEARCH</p>
          <h1>多标的日 K 走势对比</h1>
          <p>在共同覆盖区间内对齐交易日，以首个有效收盘价为基准比较累计收益与最大回撤。</p>
        </div>
        <aside>
          <strong>研究边界</strong>
          <span>不填充缺失日 · 不连接券商 · 不构成交易建议</span>
        </aside>
      </section>

      <ComparisonBoardPicker
        builtInBoards={BUILT_IN_BOARDS}
        customBoards={boardState.customBoards}
        storageIssue={boardState.storageIssue}
        canSave={instruments.length >= COMPARISON_MIN_INSTRUMENTS}
        isCreating={isCreatingBoard}
        boardName={boardName}
        onBoardNameChange={setBoardName}
        onLoad={loadBoard}
        onStartCreating={() => {
          setIsCreatingBoard(true);
          setError(null);
          setNotice(null);
        }}
        onCancelCreating={() => {
          setIsCreatingBoard(false);
          setBoardName("");
        }}
        onSave={saveBoard}
        onDelete={deleteBoard}
        onClearStorage={clearBoardStorage}
      />

      <section className="comparison-selection" aria-label="已选择标的">
        <div className="comparison-controls__search">
          <label>添加标的（2–8 个）</label>
          <InstrumentSearch onSelect={addInstrument} variant="compact" actionLabel="添加" />
        </div>
        <div className="comparison-symbols">
          {instruments.length === 0 && (
            <span className="comparison-symbols__empty">尚未选择标的</span>
          )}
          {instruments.map((instrument) => (
            <button
              type="button"
              key={instrument.symbol}
              aria-label={`移除 ${instrument.name} ${instrument.symbol}`}
              onClick={() => removeInstrument(instrument.symbol)}
            >
              <span>
                <strong>{instrument.name}</strong>
                <small>{instrument.symbol}</small>
              </span>
              <i aria-hidden="true">×</i>
            </button>
          ))}
        </div>
      </section>

      <section className="comparison-controls" aria-label="走势对比条件">
        <label>
          开始日期
          <input type="date" value={start} onChange={(event) => changeStart(event.target.value)} />
        </label>
        <label>
          结束日期
          <input type="date" value={end} onChange={(event) => changeEnd(event.target.value)} />
        </label>
        <button
          type="button"
          onClick={submit}
          disabled={isLoading || instruments.length < COMPARISON_MIN_INSTRUMENTS}
        >
          {isLoading ? "计算中" : "开始对比"}
        </button>
      </section>

      {notice && <div className="comparison-message comparison-message--success">{notice}</div>}
      {error && <div className="comparison-message comparison-message--error">{error}</div>}
      {isLoading && <div className="comparison-message">正在读取并对齐历史日 K…</div>}

      {comparison && (
        <>
          <section className="comparison-summary">
            <div>
              <span>结果状态</span>
              <strong>{comparison.status === "COMPLETE" ? "完整" : comparison.status === "PARTIAL" ? "部分完成" : "失败"}</strong>
            </div>
            <div>
              <span>成功 / 失败</span>
              <strong>{comparison.succeeded} / {comparison.failed}</strong>
            </div>
            <div>
              <span>共同覆盖区间</span>
              <strong>{formatDateRange(comparison.common_from, comparison.common_to)}</strong>
            </div>
            <div>
              <span>统一日期点</span>
              <strong>{comparison.dates.length}</strong>
            </div>
          </section>

          <section className="comparison-message" aria-label="跨市场对齐口径">
            <strong>对齐口径：</strong>
            各标的本地交易日 · 常规时段收盘 · 原币种不换汇 · 缺失日期不填充
          </section>

          {comparison.warnings.map((warning) => (
            <div
              className="comparison-message comparison-message--warning"
              key={warning.code}
            >
              [{warning.code}] {warning.message}
            </div>
          ))}

          {comparison.series.length > 0 && (
            <section className="comparison-chart-panel">
              <div className="comparison-section-heading">
                <div>
                  <p className="eyebrow">NORMALIZED RETURN</p>
                  <h2>归一化收益曲线</h2>
                </div>
                <span>缺失交易日保留为空，不以前值填充</span>
              </div>
              <ComparisonChart comparison={comparison} />
            </section>
          )}

          <section className="comparison-metrics" aria-label="多标的比较指标">
            {comparison.series.map((series) => {
              const quoteState: ComparisonQuoteState = quoteStates[series.instrument.symbol] ?? {
                status: "LOADING",
                quote: null,
                error: null,
              };
              return (
                <ComparisonMetricCard
                  key={series.instrument.symbol}
                  series={series}
                  quoteState={quoteState}
                />
              );
            })}
          </section>

          {comparison.failures.length > 0 && (
            <section className="comparison-failures">
              <h2>未纳入比较的标的</h2>
              {comparison.failures.map((failure) => (
                <p key={`${failure.symbol}-${failure.code}`}>
                  <strong>{failure.symbol}</strong>
                  <span>[{failure.code}] {failure.message}</span>
                </p>
              ))}
            </section>
          )}
        </>
      )}
    </main>
  );
}
