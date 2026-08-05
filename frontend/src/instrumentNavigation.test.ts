import { describe, expect, it } from "vitest";

import { appViewFromLocation, symbolFromSearch } from "./App";
import {
  directInstrumentFromSymbol,
  normalizeDirectSymbol,
} from "./components/InstrumentSearch";


describe("instrument navigation", () => {
  it("accepts the explicit canonical forms for each modeled market", () => {
    expect(normalizeDirectSymbol(" 000001.sz ")).toBe("000001.SZ");
    expect(normalizeDirectSymbol("600519.SH")).toBe("600519.SH");
    expect(normalizeDirectSymbol("513100.SH")).toBe("513100.SH");
    expect(normalizeDirectSymbol("00700.hk")).toBe("00700.HK");
    expect(normalizeDirectSymbol("aapl.us")).toBe("AAPL.US");
    expect(normalizeDirectSymbol("brk.b.us")).toBe("BRK.B.US");
    expect(normalizeDirectSymbol("spx.gi")).toBe("SPX.GI");
    expect(normalizeDirectSymbol("000001")).toBeNull();
    expect(normalizeDirectSymbol("DEMO.SZ")).toBeNull();
    expect(normalizeDirectSymbol("430047.BJ")).toBeNull();
  });

  it("keeps direct canonical input as unresolved code and market only", () => {
    expect(directInstrumentFromSymbol(" 000001.sh ")).toEqual({
      symbol: "000001.SH",
      market: "CN",
    });
    expect(directInstrumentFromSymbol("aapl.us")).toEqual({
      symbol: "AAPL.US",
      market: "US",
    });
  });

  it("keeps the root URL as an empty landing state", () => {
    expect(symbolFromSearch("")).toBeNull();
    expect(symbolFromSearch("?other=value")).toBeNull();
    expect(symbolFromSearch("?symbol=DEMO.SZ")).toBeNull();
  });

  it("normalizes a canonical URL symbol", () => {
    expect(symbolFromSearch("?symbol=000001.sz")).toBe("000001.SZ");
    expect(symbolFromSearch("?symbol=spx.gi")).toBe("SPX.GI");
  });

  it("uses the root as the market overview and keeps search on its manual path", () => {
    expect(appViewFromLocation("/", "")).toEqual({ name: "home" });
    expect(appViewFromLocation("/indices", "")).toEqual({ name: "indices" });
    expect(appViewFromLocation("/indices/", "")).toEqual({ name: "indices" });
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
