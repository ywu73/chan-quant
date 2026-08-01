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
});
