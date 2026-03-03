// src/atlas/frontend/src/Charts.jsx
// FIX: pintar velas SIEMPRE que cambie `candles` y normalizar `time` (segundos UNIX numéricos)

import React, { useEffect, useMemo, useRef } from "react";
import { createChart } from "lightweight-charts";

function toUnixSeconds(t) {
  if (t == null) return null;

  // si viene string numérica
  if (typeof t === "string") {
    const n = Number(t);
    if (!Number.isNaN(n)) t = n;
  }

  // si viene en ms (13 dígitos aprox)
  if (typeof t === "number") {
    if (t > 2_000_000_000_000) return Math.floor(t / 1000); // ms -> s
    if (t > 2_000_000_000) return Math.floor(t); // ya es s (2020+)
    // si viene "segundos chicos" igual lo dejamos
    return Math.floor(t);
  }

  // si viene fecha ISO
  if (typeof t === "string") {
    const d = new Date(t);
    if (!Number.isNaN(d.getTime())) return Math.floor(d.getTime() / 1000);
  }

  return null;
}

function normalizeCandles(candles) {
  const arr = Array.isArray(candles) ? candles : [];
  const out = [];

  for (const c of arr) {
    const time = toUnixSeconds(c.time ?? c.ts ?? c.timestamp);
    if (!time) continue;

    const o = Number(c.open);
    const h = Number(c.high);
    const l = Number(c.low);
    const cl = Number(c.close);

    if ([o, h, l, cl].some((x) => Number.isNaN(x))) continue;

    out.push({ time, open: o, high: h, low: l, close: cl });
  }

  // ordenar por tiempo y deduplicar por time
  out.sort((a, b) => a.time - b.time);
  const dedup = [];
  let last = null;
  for (const c of out) {
    if (last !== c.time) dedup.push(c);
    last = c.time;
  }
  return dedup;
}

export default function Charts({ candles = [], height = 420 }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  const data = useMemo(() => normalizeCandles(candles), [candles]);

  // crear chart 1 vez
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: "#0b0c0e" },
        textColor: "#c0c0c0",
      },
      grid: {
        vertLines: { color: "#1f2125" },
        horzLines: { color: "#1f2125" },
      },
      rightPriceScale: { borderColor: "#1f2125" },
      timeScale: { borderColor: "#1f2125", timeVisible: true, secondsVisible: true },
      crosshair: { mode: 0 },
    });

    const series = chart.addCandlestickSeries();

    chartRef.current = chart;
    seriesRef.current = series;

    const ro = new ResizeObserver(() => {
      if (!containerRef.current) return;
      chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    ro.observe(containerRef.current);

    // set width inicial
    chart.applyOptions({ width: containerRef.current.clientWidth });

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [height]);

  // setear data cada vez que cambia
  useEffect(() => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !chart) return;

    if (!data.length) {
      series.setData([]); // limpia si no hay velas
      return;
    }

    series.setData(data);
    chart.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} style={{ width: "100%", height }} />;
}