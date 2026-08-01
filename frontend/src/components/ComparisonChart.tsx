import { LineChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { init, use, type EChartsCoreOption } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef } from "react";

import type { MarketComparison } from "../types/comparison";


use([
  LineChart,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);


const SERIES_COLORS = [
  "#4169d8",
  "#d6604d",
  "#2e9b70",
  "#835cc7",
  "#c2832f",
  "#2f8fa8",
  "#b6518c",
  "#68788d",
];


function seriesLabel(name: string, symbol: string): string {
  return `${name} · ${symbol}`;
}


export function ComparisonChart({ comparison }: { comparison: MarketComparison }) {
  const elementRef = useRef<HTMLDivElement>(null);
  const option = useMemo<EChartsCoreOption>(() => ({
    animation: false,
    color: SERIES_COLORS,
    legend: {
      type: "scroll",
      top: 2,
      left: 0,
      right: 0,
      data: comparison.series.map((item) => seriesLabel(
        item.instrument.name,
        item.instrument.symbol,
      )),
      textStyle: { color: "#65748b" },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255,255,255,.97)",
      borderColor: "#d9e0ea",
      valueFormatter: (value: unknown) => (
        typeof value === "number" ? `${(value * 100).toFixed(2)}%` : "缺失"
      ),
      textStyle: { color: "#344054" },
    },
    grid: { left: 66, right: 24, top: 54, bottom: 62 },
    xAxis: {
      type: "category",
      data: comparison.dates.map((day) => day.slice(5)),
      boundaryGap: false,
      axisLine: { lineStyle: { color: "#d9e0ea" } },
      axisLabel: { color: "#91a0b5" },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "#edf1f6" } },
      axisLabel: {
        color: "#91a0b5",
        formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
      },
    },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      {
        type: "slider",
        bottom: 8,
        height: 22,
        borderColor: "#d8e1ee",
        fillerColor: "rgba(83,132,219,.14)",
      },
    ],
    series: comparison.series.map((item) => ({
      name: seriesLabel(item.instrument.name, item.instrument.symbol),
      type: "line",
      data: item.values,
      symbol: "none",
      connectNulls: false,
      lineStyle: { width: 2 },
      emphasis: { focus: "series" },
    })),
  }), [comparison]);

  useEffect(() => {
    if (!elementRef.current) return;
    const instance = init(elementRef.current, undefined, { renderer: "canvas" });
    instance.setOption(option);
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(elementRef.current);
    return () => {
      observer.disconnect();
      instance.dispose();
    };
  }, [option]);

  return (
    <div
      className="comparison-chart"
      ref={elementRef}
      role="img"
      aria-label="多标的归一化收益曲线"
    />
  );
}
