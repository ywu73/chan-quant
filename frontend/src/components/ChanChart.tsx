import { BarChart, CandlestickChart, LineChart, ScatterChart } from "echarts/charts";
import {
  AxisPointerComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { init, use, type EChartsCoreOption } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef } from "react";

import type { DashboardSnapshot } from "../types/dashboard";

use([
  BarChart,
  CandlestickChart,
  LineChart,
  ScatterChart,
  AxisPointerComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

export function ChanChart({ chart }: { chart: DashboardSnapshot["chart"] }) {
  const elementRef = useRef<HTMLDivElement>(null);

  const option = useMemo<EChartsCoreOption>(() => {
    const dates = chart.bars.map((bar) => bar.date.slice(5));
    const candles = chart.bars.map((bar) => [bar.open, bar.close, bar.low, bar.high]);
    const buyLine = chart.bars.map((bar) => bar.buy_line);
    const sellLine = chart.bars.map((bar) => bar.sell_line);
    const ma57 = chart.bars.map((bar) => bar.ma57);
    const volume = chart.bars.map((bar) => bar.volume);
    const dateIndex = new Map(chart.bars.map((bar, index) => [bar.date, index]));

    const strokeSeries = chart.strokes.map((stroke, index) => ({
      name: `${stroke.direction === "UP" ? "上升笔" : "下降笔"}-${index + 1}`,
      type: "line" as const,
      data: stroke.points.map((point) => [dateIndex.get(point.date), point.price]),
      symbol: "none",
      connectNulls: true,
      lineStyle: {
        width: 2,
        color: stroke.direction === "UP" ? "#48b968" : "#ef665e",
        type: stroke.status === "TENTATIVE" ? "dashed" : "solid",
      },
      tooltip: { show: false },
      z: 5,
    }));

    const signalSeries = (["BUY", "SELL"] as const).map((side) => ({
      name: side === "BUY" ? "买点" : "卖点",
      type: "scatter" as const,
      data: chart.signals
        .filter((signal) => signal.side === side)
        .map((signal) => ({
          value: [dateIndex.get(signal.date), signal.price],
          signal,
        })),
      symbolSize: 38,
      itemStyle: { color: side === "BUY" ? "#285bd4" : "#af5525" },
      label: {
        show: true,
        color: "#fff",
        fontWeight: 700,
        formatter: side === "BUY" ? "买" : "卖",
      },
      z: 10,
    }));

    return {
      animation: false,
      legend: {
        top: 2,
        left: 0,
        data: ["买线", "卖线", "MA57", "底分型", "顶分型", "买点", "卖点"],
        textStyle: { color: "#718096" },
      },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
        backgroundColor: "rgba(255,255,255,.97)",
        borderColor: "#d9e0ea",
        textStyle: { color: "#344054" },
      },
      axisPointer: { link: [{ xAxisIndex: "all" }] },
      grid: [
        { left: 54, right: 20, top: 48, height: "64%" },
        { left: 54, right: 20, top: "76%", height: "13%" },
      ],
      xAxis: [
        {
          type: "category",
          data: dates,
          boundaryGap: true,
          axisLine: { lineStyle: { color: "#d9e0ea" } },
          axisLabel: { color: "#91a0b5" },
          splitLine: { show: false },
        },
        {
          type: "category",
          gridIndex: 1,
          data: dates,
          boundaryGap: true,
          axisLine: { lineStyle: { color: "#d9e0ea" } },
          axisLabel: { show: false },
        },
      ],
      yAxis: [
        {
          scale: true,
          splitLine: { lineStyle: { color: "#edf1f6" } },
          axisLabel: { color: "#91a0b5" },
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: { show: false },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1], start: 0, end: 100 },
        {
          type: "slider",
          xAxisIndex: [0, 1],
          bottom: 0,
          height: 22,
          borderColor: "#d8e1ee",
          fillerColor: "rgba(83,132,219,.14)",
        },
      ],
      series: [
        {
          name: "K线",
          type: "candlestick",
          data: candles,
          itemStyle: {
            color: "#e7554d",
            color0: "#52bf68",
            borderColor: "#e7554d",
            borderColor0: "#52bf68",
          },
        },
        { name: "买线", type: "line", data: buyLine, symbol: "none", smooth: true, lineStyle: { color: "#4a79ed", width: 2 } },
        { name: "卖线", type: "line", data: sellLine, symbol: "none", smooth: true, lineStyle: { color: "#ef665e", width: 2 } },
        { name: "MA57", type: "line", data: ma57, symbol: "none", smooth: true, lineStyle: { color: "#8b65f4", width: 2, type: "dashed" } },
        ...strokeSeries,
        {
          name: "底分型",
          type: "scatter",
          data: chart.fractals.filter((item) => item.kind === "BOTTOM").map((item) => [dateIndex.get(item.date), item.price]),
          symbolSize: 10,
          itemStyle: { color: "#52bf68", borderColor: "#fff", borderWidth: 2 },
          z: 8,
        },
        {
          name: "顶分型",
          type: "scatter",
          data: chart.fractals.filter((item) => item.kind === "TOP").map((item) => [dateIndex.get(item.date), item.price]),
          symbolSize: 10,
          itemStyle: { color: "#ef665e", borderColor: "#fff", borderWidth: 2 },
          z: 8,
        },
        ...signalSeries,
        {
          name: "成交量",
          type: "bar",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volume,
          itemStyle: { color: "#d0d8e4" },
        },
      ],
    };
  }, [chart]);

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

  return <div className="chan-chart" ref={elementRef} role="img" aria-label="缠论 K 线与策略图" />;
}
