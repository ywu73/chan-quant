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
});
