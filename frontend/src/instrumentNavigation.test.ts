import { describe, expect, it } from "vitest";

import { appViewFromLocation, symbolFromSearch } from "./App";
import {
  directInstrumentFromSymbol,
  normalizeDirectSymbol,
} from "./components/InstrumentSearch";


describe("instrument navigation", () => {
  it("accepts only canonical Shanghai and Shenzhen symbols for direct navigation", () => {
    expect(normalizeDirectSymbol(" 000001.sz ")).toBe("000001.SZ");
    expect(normalizeDirectSymbol("600519.SH")).toBe("600519.SH");
    expect(normalizeDirectSymbol("513100.SH")).toBe("513100.SH");
    expect(normalizeDirectSymbol("000001")).toBeNull();
    expect(normalizeDirectSymbol("DEMO.SZ")).toBeNull();
    expect(normalizeDirectSymbol("430047.BJ")).toBeNull();
  });

  it("keeps direct canonical input as unresolved code and exchange only", () => {
    expect(directInstrumentFromSymbol(" 000001.sh ")).toEqual({
      symbol: "000001.SH",
      exchange: "SH",
    });
  });

  it("keeps the root URL as an empty landing state", () => {
    expect(symbolFromSearch("")).toBeNull();
    expect(symbolFromSearch("?other=value")).toBeNull();
    expect(symbolFromSearch("?symbol=DEMO.SZ")).toBeNull();
  });

  it("normalizes a canonical URL symbol", () => {
    expect(symbolFromSearch("?symbol=000001.sz")).toBe("000001.SZ");
  });

  it("uses the root as the market overview and keeps search on its manual path", () => {
    expect(appViewFromLocation("/", "")).toEqual({ name: "home" });
    expect(appViewFromLocation("/search", "")).toEqual({ name: "search" });
    expect(appViewFromLocation("/search/", "")).toEqual({ name: "search" });
    expect(appViewFromLocation("/compare", "")).toEqual({ name: "comparison" });
    expect(appViewFromLocation("/compare/", "")).toEqual({ name: "comparison" });
  });

  it("opens a canonical dashboard symbol regardless of the entry path", () => {
    expect(appViewFromLocation("/", "?symbol=600519.SH")).toEqual({
      name: "dashboard",
      symbol: "600519.SH",
    });
    expect(appViewFromLocation("/search", "?symbol=000001.sz")).toEqual({
      name: "dashboard",
      symbol: "000001.SZ",
    });
  });
});
