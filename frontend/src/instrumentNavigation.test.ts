import { describe, expect, it } from "vitest";

import { symbolFromSearch } from "./App";
import { normalizeDirectSymbol } from "./components/InstrumentSearch";


describe("instrument navigation", () => {
  it("accepts only canonical Shanghai and Shenzhen symbols for direct navigation", () => {
    expect(normalizeDirectSymbol(" 000001.sz ")).toBe("000001.SZ");
    expect(normalizeDirectSymbol("600519.SH")).toBe("600519.SH");
    expect(normalizeDirectSymbol("513100.SH")).toBe("513100.SH");
    expect(normalizeDirectSymbol("000001")).toBeNull();
    expect(normalizeDirectSymbol("DEMO.SZ")).toBeNull();
    expect(normalizeDirectSymbol("430047.BJ")).toBeNull();
  });

  it("keeps the root URL as an empty landing state", () => {
    expect(symbolFromSearch("")).toBeNull();
    expect(symbolFromSearch("?other=value")).toBeNull();
    expect(symbolFromSearch("?symbol=DEMO.SZ")).toBeNull();
  });

  it("normalizes a canonical URL symbol", () => {
    expect(symbolFromSearch("?symbol=000001.sz")).toBe("000001.SZ");
  });
});
