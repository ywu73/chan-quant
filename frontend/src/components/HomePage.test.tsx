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
});
