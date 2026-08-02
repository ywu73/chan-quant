import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { IndexPerformancePage } from "./IndexPerformancePage";


describe("IndexPerformancePage", () => {
  it("renders all verified broad indices with range controls and research boundaries", () => {
    const markup = renderToStaticMarkup(<IndexPerformancePage />);

    expect(markup).toContain("主要指数区间表现");
    expect(markup).toContain("近 3 个月");
    expect(markup).toContain("近 6 个月");
    expect(markup).toContain("近 1 年");
    expect(markup).toContain("今年以来");
    expect(markup).toContain("自定义区间");
    expect(markup.match(/class="index-performance-card /g)).toHaveLength(8);
    expect(markup).toContain("上证指数");
    expect(markup).toContain("深证成指");
    expect(markup).toContain("中证1000");
    expect(markup).toContain("盘中行情不参与累计收益与最大回撤");
    expect(markup).toContain("不构成交易建议");
  });
});
