import type { MarketBreadthSnapshot } from "../types/marketBreadth";


const STATUS_LABELS = {
  COMPLETE: "口径完整",
  PARTIAL: "部分覆盖",
  FAILED: "数据质量未通过",
} as const;


function formatRatio(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}


export function MarketBreadthPanel({
  snapshot,
  isLoading,
  error,
  onRefresh,
}: {
  snapshot: MarketBreadthSnapshot | null;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}) {
  const canShowDistribution = snapshot?.status === "COMPLETE" || snapshot?.status === "PARTIAL";
  const maxCount = snapshot ? Math.max(1, ...snapshot.bins.map((item) => item.count)) : 1;

  return (
    <section className="home-section home-breadth" aria-labelledby="market-breadth-title">
      <div className="home-section__heading home-breadth__heading">
        <div>
          <p className="home-section__eyebrow">MARKET BREADTH · AUDITABLE EOD</p>
          <h2 id="market-breadth-title">沪深 A 股市场温度</h2>
        </div>
        <div className="home-section__actions">
          <span className="home-breadth__mode">日终审计快照</span>
          <button type="button" onClick={onRefresh} disabled={isLoading}>
            {isLoading ? "读取中" : "刷新"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="home-breadth__state home-breadth__state--error">
          <strong>审计包未通过读取</strong>
          <span>{error}</span>
          <small>不会回退到匿名行情、演示数字或上一次未标记的旧值。</small>
        </div>
      ) : !snapshot ? (
        <div className="home-breadth__state">
          <strong>{isLoading ? "正在校验市场温度审计包…" : "尚无可展示的市场温度"}</strong>
          <span>需要在后端配置 Git 外的 manifest.json、universe.csv 与 quotes.csv。</span>
        </div>
      ) : (
        <>
          <div className="home-breadth__audit">
            <span className={`home-breadth__status home-breadth__status--${snapshot.status.toLowerCase()}`}>
              {STATUS_LABELS[snapshot.status]}
            </span>
            <span>交易日 {snapshot.session_date}</span>
            <span>universe {snapshot.universe_as_of}</span>
            <span>{snapshot.source}</span>
          </div>

          <div className="home-breadth__totals" aria-label="市场涨跌统计">
            <strong className="home-breadth__advance">涨 {snapshot.advancers}</strong>
            <strong className="home-breadth__decline">跌 {snapshot.decliners}</strong>
            <strong className="home-breadth__unchanged">平 {snapshot.unchanged}</strong>
            <span>不可用 {snapshot.unavailable}</span>
            <span>覆盖 {formatRatio(snapshot.coverage_ratio)}</span>
            <span>分母 {snapshot.universe_total}</span>
          </div>

          {canShowDistribution ? (
            <div
              className="home-breadth__chart"
              data-testid="market-breadth-chart"
              aria-label="非零涨跌幅分布"
            >
              {snapshot.bins.map((item) => (
                <div className={`home-breadth__bin home-breadth__bin--${item.side.toLowerCase()}`} key={item.id}>
                  <div className="home-breadth__bar-space">
                    <span>{item.count}</span>
                    <i
                      aria-hidden="true"
                      style={{ height: item.count === 0 ? "2px" : `${Math.max(6, item.count / maxCount * 100)}%` }}
                    />
                  </div>
                  <small>{item.label}</small>
                </div>
              ))}
            </div>
          ) : (
            <div className="home-breadth__state home-breadth__state--error">
              <strong>数据质量未通过</strong>
              {snapshot.issues.map((issue) => <span key={issue.code}>{issue.message}</span>)}
              <small>覆盖不足时不展示可能误导的涨跌分布。</small>
            </div>
          )}

          {snapshot.status === "PARTIAL" && (
            <p className="home-breadth__warning">
              可解释比例 {formatRatio(snapshot.resolution_ratio)}；存在未知缺行，图表仅代表已覆盖证券。
            </p>
          )}
          <p className="home-section__note home-breadth__note">
            后端使用当日昨收与收盘价复算；零涨跌单列，停牌和无合法参考价不计为平盘。
          </p>
        </>
      )}
    </section>
  );
}
