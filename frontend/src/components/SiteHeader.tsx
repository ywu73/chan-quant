import type { MouseEvent } from "react";

import { InstrumentSearch } from "./InstrumentSearch";


type SiteSection = "market" | "indices" | "comparison" | "research" | "methodology";


interface SiteHeaderProps {
  activeSection: SiteSection | null;
  onNavigateHome: () => void;
  onNavigateIndices: () => void;
  onNavigateComparison: () => void;
  onNavigateResearch: () => void;
  onNavigateMethodology: () => void;
  onSelect: (symbol: string) => void;
}


function handleInternalNavigation(
  event: MouseEvent<HTMLAnchorElement>,
  navigate: () => void,
) {
  if (
    event.defaultPrevented
    || event.button !== 0
    || event.metaKey
    || event.ctrlKey
    || event.shiftKey
    || event.altKey
  ) {
    return;
  }
  event.preventDefault();
  navigate();
}


export function SiteHeader({
  activeSection,
  onNavigateHome,
  onNavigateIndices,
  onNavigateComparison,
  onNavigateResearch,
  onNavigateMethodology,
  onSelect,
}: SiteHeaderProps) {
  return (
    <header className="site-header">
      <a
        className="site-brand"
        href="/"
        aria-label="返回市场概况首页"
        onClick={(event) => handleInternalNavigation(event, onNavigateHome)}
      >
        <span className="site-brand__mark" aria-hidden="true">CQ</span>
        <span className="site-brand__copy">
          <span>CHAN QUANT</span>
          <strong>结构与趋势量化研究台</strong>
        </span>
      </a>

      <nav className="site-nav" aria-label="主导航">
        <a
          className={`site-nav__item${activeSection === "market" ? " site-nav__item--active" : ""}`}
          href="/"
          aria-current={activeSection === "market" ? "page" : undefined}
          onClick={(event) => handleInternalNavigation(event, onNavigateHome)}
        >
          市场概况
        </a>
        <a
          className={`site-nav__item${activeSection === "indices" ? " site-nav__item--active" : ""}`}
          href="/indices"
          aria-current={activeSection === "indices" ? "page" : undefined}
          onClick={(event) => handleInternalNavigation(event, onNavigateIndices)}
        >
          指数表现
        </a>
        <a
          className={`site-nav__item${activeSection === "comparison" ? " site-nav__item--active" : ""}`}
          href="/compare"
          aria-current={activeSection === "comparison" ? "page" : undefined}
          onClick={(event) => handleInternalNavigation(event, onNavigateComparison)}
        >
          走势对比
        </a>
        <a
          className={`site-nav__item${activeSection === "research" ? " site-nav__item--active" : ""}`}
          href="/search"
          aria-current={activeSection === "research" ? "page" : undefined}
          onClick={(event) => handleInternalNavigation(event, onNavigateResearch)}
        >
          研究工作台
        </a>
        <a
          className={`site-nav__item${activeSection === "methodology" ? " site-nav__item--active" : ""}`}
          href="/methodology"
          aria-current={activeSection === "methodology" ? "page" : undefined}
          onClick={(event) => handleInternalNavigation(event, onNavigateMethodology)}
        >
          数据与方法
        </a>
      </nav>

      <InstrumentSearch
        variant="compact"
        onSelect={(instrument) => onSelect(instrument.symbol)}
      />
    </header>
  );
}
