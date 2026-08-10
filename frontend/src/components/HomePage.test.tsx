import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { HomePage } from "./HomePage";


describe("HomePage", () => {
  it("exposes the methodology page from the hero, boundary card, and footer", () => {
    const markup = renderToStaticMarkup(
      <HomePage
        onNavigateComparison={vi.fn()}
        onNavigateMethodology={vi.fn()}
        onNavigateResearch={vi.fn()}
      />,
    );

    expect(markup.match(/href="\/methodology"/g)).toHaveLength(3);
    expect(markup).toContain("查看数据与方法");
    expect(markup).toContain("查看数据谱系、计算口径与失败语义");
    expect(markup).toContain('href="/search"');
  });


  it("renders an offline research snapshot without remote refresh controls", () => {
    const markup = renderToStaticMarkup(
      <HomePage
        remoteNetworkEnabled={false}
        forceRefreshEnabled={false}
        onNavigateComparison={vi.fn()}
        onNavigateMethodology={vi.fn()}
        onNavigateResearch={vi.fn()}
      />,
    );

    expect(markup).toContain("离线研究演示");
    expect(markup).toContain("远端指数快照已关闭");
    expect(markup).not.toContain("正在读取独立实时快照");
  });
});
