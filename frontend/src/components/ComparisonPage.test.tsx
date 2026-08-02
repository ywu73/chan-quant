import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ComparisonPage } from "./ComparisonPage";


describe("ComparisonPage", () => {
  it("keeps the instrument search form outside another form", () => {
    const markup = renderToStaticMarkup(<ComparisonPage />);

    expect(markup).toContain('<section class="comparison-controls"');
    expect(markup.match(/<form\b/g)).toHaveLength(1);
    expect(markup).not.toContain('<form class="comparison-controls"');
  });

  it("places board loading before selection and comparison conditions", () => {
    const markup = renderToStaticMarkup(<ComparisonPage />);

    expect(markup).toContain('aria-label="板块速选"');
    expect(markup).toContain("宽基指数");
    expect(markup).toContain("保存当前组合");
    expect(markup).toContain("添加标的（2–8 个）");
    expect(markup.indexOf('aria-label="板块速选"')).toBeLessThan(
      markup.indexOf('aria-label="已选择标的"'),
    );
    expect(markup.indexOf('aria-label="已选择标的"')).toBeLessThan(
      markup.indexOf('aria-label="走势对比条件"'),
    );
  });

  it("shows every built-in preset with membership provenance and subset limits", () => {
    const markup = renderToStaticMarkup(<ComparisonPage />);

    expect(markup).toContain("中证白酒前 8 权重");
    expect(markup).toContain("中证创新药前 8 权重");
    expect(markup).toContain("半导体材料设备前 8 权重");
    expect(markup).toContain("来源 中证白酒指数（399997）");
    expect(markup).toContain("来源 中证创新药产业指数（931152）");
    expect(markup).toContain("来源 中证半导体材料设备主题指数（931743）");
    expect(markup.match(/成员日期 2026-07-31/g)).toHaveLength(3);
    expect(markup.match(/身份确认 2026-08-02/g)).toHaveLength(3);
    expect(markup.match(/不是完整指数成分/g)).toHaveLength(3);
    expect(markup).not.toContain("来源 sina-undocumented-suggest");
  });
});
