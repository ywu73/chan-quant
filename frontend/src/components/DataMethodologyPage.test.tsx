import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { DataMethodologyPage } from "./DataMethodologyPage";


describe("DataMethodologyPage", () => {
  it("renders data lineage, source boundaries, time semantics, and owned APIs", () => {
    const markup = renderToStaticMarkup(
      <DataMethodologyPage onNavigateHome={vi.fn()} />,
    );

    expect(markup).toContain("先说明数据能证明什么，再展示研究结论");
    expect(markup).toContain("上交所 / 深交所官方公开来源");
    expect(markup).toContain("新浪财经未文档化 Web 端点");
    expect(markup).toContain("可审计历史快照");
    expect(markup).toContain("合成演示数据");
    expect(markup).toContain("structure_at");
    expect(markup).toContain("confirmed_at");
    expect(markup).toContain("executable_at");
    expect(markup).toContain("不回退成演示数字");
    expect(markup).toContain("GET /api/v1/market-breadth");
    expect(markup).toContain('href="/"');
  });
});
