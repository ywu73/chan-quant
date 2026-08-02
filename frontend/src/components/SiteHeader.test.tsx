import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { SiteHeader } from "./SiteHeader";


describe("SiteHeader", () => {
  it("exposes the index performance page as a first-class navigation item", () => {
    const markup = renderToStaticMarkup(
      <SiteHeader
        activeSection="indices"
        onNavigateHome={vi.fn()}
        onNavigateIndices={vi.fn()}
        onNavigateComparison={vi.fn()}
        onNavigateResearch={vi.fn()}
        onSelect={vi.fn()}
      />,
    );

    expect(markup).toContain('href="/indices"');
    expect(markup).toContain("指数表现");
    expect(markup).toContain('aria-current="page"');
  });
});
